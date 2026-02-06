"""
脚本验证器：为 AI 生成的临时脚本提供"执行前质量门槛"。

目标：
- 在执行前捕获语法错误/常见逻辑错误（lint）/输出格式不符合约定
- 可选执行一次"低风险预跑（dry-run）"来提前发现 NameError 等运行时错误
- 将验证报告反馈给反思环路，提高自动修复成功率

说明：
- 这是"最务实"的闭环：不会强制生成 pytest 测试（那会拖慢用户体验）
- dry-run 默认会阻断危险操作（删除文件、子进程等）；若脚本确实需要这些操作，会返回可继续执行的提示

策略（v2）：
- ruff 分两步：1) `ruff check --fix` 自动修复 2) 重新检查只看致命错误
- 致命规则（阻断执行）：F821（未定义变量）、E999（语法错误）
- 其他规则（仅记录警告，不阻断）：E/F/B 其余项
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

# 这些 ruff 规则代表真正的逻辑 bug，必须阻断执行
# 注意：E999 在 ruff ≥0.15 中已移除（语法错误由 AST/py_compile 捕获），只保留 F821
FATAL_RULES = {"F821"}


@dataclass
class ValidationReport:
    """脚本验证报告。"""

    ok: bool
    kind: ValidationKind
    message: str
    details: str = ""
    fixed_code: str = ""  # 如果 ruff --fix 修复了代码，返回修复后版本


class ScriptValidator:
    """
    AI 脚本验证器。

    典型用法：
    - 写入临时脚本
    - ruff --fix 自动修复 → 只对致命错误阻断
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
        fixed_code = code

        # 1) Lint: 先 --fix 自动修复，再检查是否残留致命错误
        if lint:
            ok, msg, details, patched = self._ruff_fix_then_check(code)
            if patched:
                fixed_code = patched
            if not ok:
                return ValidationReport(
                    ok=False, kind="lint", message=msg,
                    details=details, fixed_code=fixed_code,
                )

        # 2) Contract
        if require_json_output:
            if "json.dumps" not in fixed_code or "print(" not in fixed_code:
                return ValidationReport(
                    ok=False,
                    kind="contract",
                    message="输出契约不满足：脚本未包含 print(json.dumps(...))，可能导致前端无法解析结果",
                    details='建议脚本最后输出：print(json.dumps({"success": True/False, "message": "...", "data": {...}}, ensure_ascii=False))',
                    fixed_code=fixed_code,
                )

        # 3) Dry-run（可选）
        if dry_run:
            ok, msg, details, fatal = self._dry_run(fixed_code, timeout_sec=dry_run_timeout_sec)
            if not ok and fatal:
                return ValidationReport(
                    ok=False, kind="dry_run", message=msg,
                    details=details, fixed_code=fixed_code,
                )

        return ValidationReport(
            ok=True, kind="unknown", message="验证通过",
            fixed_code=fixed_code,
        )

    def _write_tmp(self, code: str) -> Path:
        ts = int(time.time() * 1000)
        path = self.tmp_dir / f"validate_{ts}.py"
        path.write_text(code, encoding="utf-8")
        return path

    # ------------------------------------------------------------------
    # 核心改造：先 fix 再 check
    # ------------------------------------------------------------------
    def _ruff_fix_then_check(self, code: str) -> Tuple[bool, str, str, str]:
        """
        两步 ruff 策略：
        1. `ruff check --fix` 自动修复可修复项（E501、B905、F401 等）
        2. 重新读取修复后代码，只检查 FATAL_RULES 是否残留

        Returns:
            (ok, message, details, fixed_code_or_empty)
            fixed_code_or_empty: 如果代码被修改则返回修复后文本，否则空字符串
        """
        try:
            tmp = self._write_tmp(code)

            # ---- Step 1: ruff check --fix （就地修复） ----
            fix_cmd = [
                sys.executable, "-m", "ruff", "check",
                str(tmp),
                "--select", "E,F,B",
                "--fix",      # 就地修复
                "--quiet",
            ]
            subprocess.run(fix_cmd, capture_output=True, text=True, timeout=10)

            # 读回修复后代码
            fixed_code = tmp.read_text(encoding="utf-8")

            # ---- Step 2: 再次检查，只看致命规则 ----
            fatal_select = ",".join(sorted(FATAL_RULES))
            check_cmd = [
                sys.executable, "-m", "ruff", "check",
                str(tmp),
                "--select", fatal_select,
                "--quiet",
            ]
            result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                # 没有致命错误
                if fixed_code != code:
                    logger.info("ruff --fix 自动修复了部分问题，已采用修复后代码")
                return True, "ruff 通过", "", fixed_code if fixed_code != code else ""

            # 仍存在致命错误
            output = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
            return False, "ruff 检查发现致命错误（未定义变量/语法错误）", output[:2000], fixed_code

        except FileNotFoundError:
            logger.debug("ruff 未安装，跳过检查")
            return True, "ruff 跳过（未安装）", "", ""
        except Exception as e:
            logger.debug("ruff 检查跳过/失败: " + str(e))
            return True, "ruff 跳过", "", ""

    def _dry_run(self, code: str, timeout_sec: int) -> Tuple[bool, str, str, bool]:
        """
        执行一次短超时预跑。

        返回：
        - ok: 是否通过
        - message/details
        - fatal: 是否应阻断真实执行

        规则：
        - 如果触发了"被阻断的危险操作"，不视为 fatal（允许继续真实执行）
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
                return True, "dry-run 通过", stdout[-500:], False

            combined = (stderr or stdout or "").strip()
            if "DESKJARVIS_BLOCKED_OPERATION" in combined:
                return False, "dry-run 检测到被阻断的危险操作（将继续真实执行）", combined[:1500], False

            # 其他错误：fatal
            return False, "dry-run 预跑失败（运行时错误，建议重写脚本）", combined[:2000], True
        except subprocess.TimeoutExpired:
            return False, "dry-run 超时（不阻断真实执行）", "timeout", False
        except Exception as e:
            return False, "dry-run 预跑异常（不阻断真实执行）", str(e), False

    def _build_guard_prelude(self) -> str:
        """
        生成 dry-run 防护前置代码：阻断明显危险操作。
        """
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
