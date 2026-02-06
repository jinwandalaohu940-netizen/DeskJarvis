"""
脚本验证器：为 AI 生成的临时脚本提供“执行前质量门槛”。

目标：
- 在执行前捕获语法错误/常见逻辑错误（lint）/输出格式不符合约定
- 可选执行一次“低风险预跑（dry-run）”来提前发现 NameError 等运行时错误
- 将验证报告反馈给反思环路，提高自动修复成功率

说明：
- 这是“最务实”的闭环：不会强制生成 pytest 测试（那会拖慢用户体验）
- dry-run 默认会阻断危险操作（删除文件、子进程等）；若脚本确实需要这些操作，会返回可继续执行的提示
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Tuple

logger = logging.getLogger(__name__)

ValidationKind = Literal["syntax", "lint", "contract", "dry_run", "unknown"]


@dataclass
class ValidationReport:
    """脚本验证报告。"""

    ok: bool
    kind: ValidationKind
    message: str
    details: str = ""


class ScriptValidator:
    """
    AI 脚本验证器。

    典型用法：
    - 写入临时脚本
    - ruff 快检（可选）
    - 输出契约检查（可选：要求 JSON）
    - dry-run 预跑（可选，短超时）
    """

    def __init__(self, sandbox_path: Path):
        """
        Args:
            sandbox_path: DeskJarvis 沙盒目录
        """
        self.sandbox_path = sandbox_path
        self.tmp_dir = sandbox_path / "scripts"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    def validate(
        self,
        code: str,
        *,
        lint: bool = True,
        require_json_output: bool = False,
        dry_run: bool = True,
        dry_run_timeout_sec: int = 2,
    ) -> ValidationReport:
        """
        执行验证。

        Args:
            code: Python 源码
            lint: 是否运行 ruff 快检（安装了才会执行）
            require_json_output: 是否要求脚本输出可解析的 JSON（stdout）
            dry_run: 是否进行一次低风险预跑（短超时）
            dry_run_timeout_sec: dry-run 超时秒

        Returns:
            ValidationReport
        """
        # 1) Lint
        if lint:
            ok, msg, details = self._ruff_check(code)
            if not ok:
                return ValidationReport(ok=False, kind="lint", message=msg, details=details)

        # 2) Contract（静态约束：如果要求 JSON，则至少包含 json.dumps + print；这不是强校验，只是挡住明显遗漏）
        if require_json_output:
            if "json.dumps" not in code or "print(" not in code:
                return ValidationReport(
                    ok=False,
                    kind="contract",
                    message="输出契约不满足：脚本未包含 print(json.dumps(...))，可能导致前端无法解析结果",
                    details="建议脚本最后输出：print(json.dumps({\"success\": True/False, \"message\": \"...\", \"data\": {...}}, ensure_ascii=False))",
                )

        # 3) Dry-run（可选）
        if dry_run:
            ok, msg, details, fatal = self._dry_run(code, timeout_sec=dry_run_timeout_sec)
            if not ok and fatal:
                return ValidationReport(ok=False, kind="dry_run", message=msg, details=details)

        return ValidationReport(ok=True, kind="unknown", message="验证通过")

    def _write_tmp(self, code: str) -> Path:
        ts = int(time.time() * 1000)
        path = self.tmp_dir / f"validate_{ts}.py"
        path.write_text(code, encoding="utf-8")
        return path

    def _ruff_check(self, code: str) -> Tuple[bool, str, str]:
        """
        运行 ruff 快检（若未安装则跳过）。
        """
        try:
            # ruff 作为工具依赖，不强制存在
            # 仅检查最常见错误：F(未定义等) + E(语法/格式基础) + B(常见bug)
            tmp = self._write_tmp(code)
            cmd = [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(tmp),
                "--select",
                "E,F,B",
                "--ignore",
                "E501",
                "--quiet",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return True, "ruff 通过", ""
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            output = output.strip()
            return False, "ruff 检查未通过（脚本存在明显问题）", output[:2000]
        except Exception as e:
            # ruff 不可用或运行失败 → 不阻断执行
            logger.debug(f"ruff 检查跳过/失败: {e}")
            return True, "ruff 跳过", ""

    def _dry_run(self, code: str, timeout_sec: int) -> Tuple[bool, str, str, bool]:
        """
        执行一次短超时预跑。

        返回：
        - ok: 是否通过
        - message/details
        - fatal: 是否应阻断真实执行

        规则：
        - 如果触发了“被阻断的危险操作”，不视为 fatal（允许继续真实执行）
        - NameError/ImportError/TypeError 等明显运行时错误视为 fatal
        """
        guard = self._build_guard_prelude()
        wrapped = guard + "\n\n" + code
        tmp = self._write_tmp(wrapped)

        env = {
            **os.environ,
            "PYTHONIOENCODING": "utf-8",
            "DESKJARVIS_DRY_RUN": "1",
        }

        try:
            result = subprocess.run(
                [sys.executable, str(tmp)],
                capture_output=True,
                text=True,
                timeout=max(1, int(timeout_sec)),
                cwd=str(self.sandbox_path),
                env=env,
            )
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            if result.returncode == 0:
                # 预跑 OK（不要求输出 JSON）
                return True, "dry-run 通过", stdout[-500:], False

            combined = (stderr or stdout or "").strip()
            if "DESKJARVIS_BLOCKED_OPERATION" in combined:
                return False, "dry-run 检测到被阻断的危险操作（将继续真实执行）", combined[:1500], False

            # 其他错误：fatal
            return False, "dry-run 预跑失败（运行时错误，建议重写脚本）", combined[:2000], True
        except subprocess.TimeoutExpired:
            # 超时不一定是错误（长任务），不阻断
            return False, "dry-run 超时（不阻断真实执行）", "timeout", False
        except Exception as e:
            return False, "dry-run 预跑异常（不阻断真实执行）", str(e), False

    def _build_guard_prelude(self) -> str:
        """
        生成 dry-run 防护前置代码：阻断明显危险操作。
        """
        # 使用字符串字面量拼接，避免 f-string
        return (
            "# === DeskJarvis dry-run guard ===\n"
            "import os as _dj_os\n"
            "import shutil as _dj_shutil\n"
            "import subprocess as _dj_subprocess\n"
            "from pathlib import Path as _dj_Path\n"
            "\n"
            "def _dj_block(*args, **kwargs):\n"
            "    raise RuntimeError('DESKJARVIS_BLOCKED_OPERATION: blocked in dry-run')\n"
            "\n"
            "# 阻断删除/移动等高风险操作\n"
            "_dj_os.remove = _dj_block\n"
            "_dj_os.unlink = _dj_block\n"
            "_dj_shutil.rmtree = _dj_block\n"
            "_dj_shutil.move = _dj_block\n"
            "_dj_shutil.copytree = _dj_block\n"
            "_dj_subprocess.run = _dj_block\n"
            "_dj_subprocess.Popen = _dj_block\n"
            "\n"
            "# Path 级别删除也阻断\n"
            "_dj_Path.unlink = _dj_block\n"
            "_dj_Path.rmdir = _dj_block\n"
        )

