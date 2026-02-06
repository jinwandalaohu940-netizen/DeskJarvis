"""
DeskJarvis 常驻 Python 服务进程

核心设计：
- 通过 stdin/stdout JSON 行协议与 Tauri 通信
- Agent 初始化一次，后续所有任务复用同一实例
- MemoryManager 懒加载，不阻塞启动
- sentence-transformers 异步后台加载

协议格式（stdin → Python）：
  {"cmd":"execute","id":"task_123","instruction":"翻译 hello","context":null}
  {"cmd":"ping","id":"health_1"}
  {"cmd":"shutdown","id":"bye_1"}

协议格式（Python → stdout）：
  {"type":"ready","timestamp":1234567890.0}
  {"type":"progress","id":"task_123","timestamp":...,"data":{...}}
  {"type":"result","id":"task_123","timestamp":...,"data":{...}}
  {"type":"pong","id":"health_1","timestamp":1234567890.0}
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


def send_event(event: Dict[str, Any]) -> None:
    """发送 JSON 事件到 stdout（一行一个，Tauri 逐行读取）"""
    try:
        line = json.dumps(event, ensure_ascii=False)
        sys.stdout.write(line + "\n")
        sys.stdout.flush()
    except Exception:
        pass  # stdout 管道关闭时静默忽略


def main() -> None:
    """常驻服务主循环"""
    # ========== 日志只输出到 stderr，stdout 留给通信协议 ==========
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    logger.info("DeskJarvis Python 服务启动中...")
    startup_start = time.time()

    # ========== 初始化配置 ==========
    try:
        from agent.tools.config import Config
        config = Config()
        if not config.validate():
            send_event({"type": "error", "message": "配置无效，请检查 ~/.deskjarvis/config.json"})
            sys.exit(1)
    except Exception as e:
        send_event({"type": "error", "message": "配置初始化失败: " + str(e)})
        sys.exit(1)

    # ========== 初始化 Agent（MemoryManager 懒加载，不阻塞） ==========
    try:
        from agent.main import DeskJarvisAgent
        agent = DeskJarvisAgent(config)
    except Exception as e:
        send_event({"type": "error", "message": "Agent 初始化失败: " + str(e)})
        sys.exit(1)

    startup_elapsed = time.time() - startup_start
    logger.info("DeskJarvis Python 服务已就绪，启动耗时 %.1fs" % startup_elapsed)

    # ========== 发送就绪信号 ==========
    send_event({
        "type": "ready",
        "timestamp": time.time(),
        "startup_time": round(startup_elapsed, 2),
    })

    # ========== 主循环：从 stdin 读取命令，执行并返回结果 ==========
    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue

            # 解析命令
            try:
                cmd = json.loads(line)
            except json.JSONDecodeError as e:
                send_event({
                    "type": "error",
                    "message": "JSON 解析失败: " + str(e),
                })
                continue

            cmd_type = cmd.get("cmd", "")
            request_id = cmd.get("id", "")

            # ---------- ping ----------
            if cmd_type == "ping":
                send_event({
                    "type": "pong",
                    "id": request_id,
                    "timestamp": time.time(),
                })

            # ---------- shutdown ----------
            elif cmd_type == "shutdown":
                logger.info("收到关闭命令，正在退出...")
                send_event({
                    "type": "shutdown_ack",
                    "id": request_id,
                    "timestamp": time.time(),
                })
                break

            # ---------- execute ----------
            elif cmd_type == "execute":
                instruction = cmd.get("instruction", "")
                context = cmd.get("context")

                if not instruction:
                    send_event({
                        "type": "result",
                        "id": request_id,
                        "timestamp": time.time(),
                        "data": {
                            "success": False,
                            "message": "指令为空",
                            "steps": [],
                            "user_instruction": "",
                        },
                    })
                    continue

                # 创建进度回调，将事件写到 stdout 并带上 request_id
                def make_progress_callback(rid: str):
                    def callback(event: Dict[str, Any]):
                        event["id"] = rid
                        send_event(event)
                    return callback

                progress_cb = make_progress_callback(request_id)

                try:
                    result = agent.execute(
                        instruction,
                        progress_callback=progress_cb,
                        context=context,
                    )
                    send_event({
                        "type": "result",
                        "id": request_id,
                        "timestamp": time.time(),
                        "data": result,
                    })
                except Exception as e:
                    logger.error("执行任务异常: " + str(e), exc_info=True)
                    send_event({
                        "type": "result",
                        "id": request_id,
                        "timestamp": time.time(),
                        "data": {
                            "success": False,
                            "message": "执行异常: " + str(e),
                            "steps": [],
                            "user_instruction": instruction,
                        },
                    })

            # ---------- unknown ----------
            else:
                send_event({
                    "type": "error",
                    "id": request_id,
                    "message": "未知命令: " + cmd_type,
                })

    except KeyboardInterrupt:
        logger.info("收到中断信号")
    except Exception as e:
        logger.error("服务主循环异常: " + str(e), exc_info=True)

    # ========== 清理 ==========
    try:
        if agent._memory is not None:
            agent._memory.shutdown()
    except Exception:
        pass

    logger.info("DeskJarvis Python 服务已关闭")


if __name__ == "__main__":
    main()
