"""
DeskJarvis Agent主入口

命令行版本：用于原型验证和测试

遵循 docs/ARCHITECTURE.md 中的架构设计
"""

import sys
import json
import logging
from typing import Dict, Any, List
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.tools.config import Config
from agent.tools.logger import setup_logger
from agent.tools.exceptions import DeskJarvisError
from agent.planner.planner_factory import create_planner
from agent.executor.browser import BrowserExecutor
from agent.executor.file_manager import FileManager
from agent.executor.system_tools import SystemTools

logger = logging.getLogger(__name__)


class DeskJarvisAgent:
    """
    DeskJarvis Agent主类
    
    职责：
    - 协调Planner和Executor
    - 执行完整任务流程
    - 处理错误和重试
    """
    
    def __init__(self, config: Config):
        """
        初始化Agent
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.planner = create_planner(config)
        self.browser_executor = BrowserExecutor(config)
        self.file_manager = FileManager(config)
        self.system_tools = SystemTools(config)
        logger.info(f"DeskJarvis Agent已初始化，使用{config.provider}规划器")
    
    def execute(self, user_instruction: str, progress_callback=None, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行用户指令
        
        Args:
            user_instruction: 用户自然语言指令
            progress_callback: 进度回调函数，接收进度事件字典
        
        Returns:
            执行结果，包含success、message、steps等
        """
        def emit_progress(event_type: str, data: Dict[str, Any]):
            """发送进度事件"""
            event = {
                "type": event_type,
                "timestamp": __import__("time").time(),
                "data": data
            }
            if progress_callback:
                progress_callback(event)
            else:
                # 如果没有回调，输出到stdout（JSON Lines格式）
                print(json.dumps(event, ensure_ascii=False), flush=True)
        
        try:
            logger.info(f"收到用户指令: {user_instruction}")
            emit_progress("task_started", {"instruction": user_instruction})
            
            # 1. 规划任务（传递上下文）
            logger.info("步骤1: 规划任务...")
            emit_progress("planning_started", {})
            steps = self.planner.plan(user_instruction, context=context)
            logger.info(f"规划完成，生成{len(steps)}个步骤")
            emit_progress("planning_completed", {
                "step_count": len(steps),
                "steps": steps
            })
            
            # 2. 检查是否需要浏览器（只有当任务包含浏览器相关步骤时才启动）
            browser_needed = any(
                step.get("type", "").startswith("browser_") or step.get("type") == "download_file"
                for step in steps
            )
            
            if browser_needed:
                logger.info("步骤2: 启动浏览器（任务需要浏览器操作）...")
                emit_progress("browser_starting", {})
                self.browser_executor.start()
                emit_progress("browser_started", {})
            else:
                logger.info("步骤2: 跳过浏览器启动（任务不需要浏览器操作）")
            
            try:
                # 3. 执行步骤
                logger.info("步骤3: 执行步骤...")
                results = []
                
                for i, step in enumerate(steps, 1):
                    step_type = step.get("type", "")
                    step_action = step.get("action", "")
                    step_params = step.get("params", {})
                    
                    logger.info(f"执行步骤 {i}/{len(steps)}: {step_type} - {step_action}")
                    logger.info(f"📋 步骤 {i} 详细信息: type={step_type}, params keys={list(step_params.keys())}")
                    
                    # 如果是 download_file，输出详细信息
                    if step_type == "download_file":
                        logger.info(f"✅ 步骤 {i} 是 download_file 工具，text={step_params.get('text')}, save_path={step_params.get('save_path')}")
                    
                    # 如果是 execute_python_script，检查是否应该被转换
                    if step_type == "execute_python_script":
                        script_preview = step_params.get('script', '')[:200] if step_params.get('script') else ''
                        logger.warning(f"⚠️ 步骤 {i} 是 execute_python_script，脚本预览: {script_preview}...")
                        if 'download' in script_preview.lower() or '下载' in step_action:
                            logger.error(f"❌ 步骤 {i} 包含下载操作但仍然是脚本，自动转换可能没有生效！")
                    
                    emit_progress("step_started", {
                        "step_index": i - 1,
                        "total_steps": len(steps),
                        "step": step
                    })
                    
                    # 根据步骤类型选择执行器
                    if step_type.startswith("browser_"):
                        result = self.browser_executor.execute_step(step)
                    elif step_type == "download_file":
                        logger.info(f"🔽 使用 browser_executor 执行 download_file 步骤")
                        result = self.browser_executor.execute_step(step)
                        logger.info(f"📥 download_file 执行结果: success={result.get('success')}, message={result.get('message')}, data={result.get('data')}")
                    elif step_type.startswith("file_"):
                        result = self.file_manager.execute_step(step)
                    elif step_type in ["screenshot_desktop", "open_folder", "open_file", "open_app", "close_app", "execute_python_script"]:
                        result = self.system_tools.execute_step(step)
                    else:
                        result = {
                            "success": False,
                            "message": f"未知的步骤类型: {step_type}",
                            "data": None
                        }
                    
                    results.append({
                        "step": step,
                        "result": result
                    })
                    
                    # 发送步骤完成事件
                    emit_progress("step_completed", {
                        "step_index": i - 1,
                        "total_steps": len(steps),
                        "step": step,
                        "result": result
                    })
                    
                    # 如果步骤失败，记录但继续执行
                    if not result.get("success"):
                        logger.warning(f"步骤 {i} 执行失败: {result.get('message')}")
                        emit_progress("step_failed", {
                            "step_index": i - 1,
                            "total_steps": len(steps),
                            "step": step,
                            "error": result.get("message", "未知错误")
                        })
                
                # 4. 汇总结果
                success_count = sum(1 for r in results if r["result"].get("success"))
                all_success = success_count == len(results)
                
                final_result = {
                    "success": all_success,
                    "message": f"任务完成: {success_count}/{len(results)}个步骤成功",
                    "steps": results,
                    "user_instruction": user_instruction
                }
                
                emit_progress("task_completed", {
                    "success": all_success,
                    "success_count": success_count,
                    "total_count": len(results),
                    "result": final_result
                })
                
                return final_result
                
            finally:
                # 5. 停止浏览器（如果已启动）
                if browser_needed:
                    logger.info("步骤4: 停止浏览器...")
                    emit_progress("browser_stopping", {})
                    self.browser_executor.stop()
                    emit_progress("browser_stopped", {})
                else:
                    logger.info("步骤4: 跳过浏览器停止（浏览器未启动）")
                
        except Exception as e:
            logger.error(f"执行任务失败: {e}", exc_info=True)
            error_result = {
                "success": False,
                "message": f"任务执行失败: {e}",
                "steps": [],
                "user_instruction": user_instruction
            }
            emit_progress("task_failed", {
                "error": str(e),
                "result": error_result
            })
            return error_result


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="DeskJarvis Agent - AI桌面助手")
    parser.add_argument(
        "instruction",
        nargs="?",
        help="用户指令（自然语言）"
    )
    parser.add_argument(
        "--config",
        help="配置文件路径（可选）"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="仅输出JSON结果（用于Tauri调用）"
    )
    parser.add_argument(
        "--context",
        help="上下文信息（JSON字符串，包含之前创建的文件等）"
    )
    
    args = parser.parse_args()
    
    # 配置日志（JSON模式下只输出ERROR级别到stderr）
    if args.json:
        # JSON模式：日志只输出到stderr，stdout只输出JSON
        logging.basicConfig(
            level=logging.ERROR,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            stream=sys.stderr
        )
    else:
        setup_logger(log_level=args.log_level)
    
    try:
        # 加载配置
        config = Config(config_path=args.config)
        
        # 验证配置
        if not config.validate():
            error_msg = "配置无效，请检查配置文件"
            if args.json:
                # JSON模式：返回错误JSON
                error_result = {
                    "success": False,
                    "message": error_msg,
                    "steps": [],
                    "user_instruction": args.instruction or ""
                }
                print(json.dumps(error_result, ensure_ascii=False))
                sys.exit(1)
            else:
                logger.error(error_msg)
                logger.info(f"配置文件位置: {config.config_path}")
                logger.info("请设置api_key字段")
                sys.exit(1)
        
        # 解析上下文信息
        context = None
        if args.context:
            try:
                context = json.loads(args.context)
            except json.JSONDecodeError as e:
                logger.warning(f"解析上下文信息失败: {e}")
                context = None
        
        # 创建Agent
        agent = DeskJarvisAgent(config)
        
        # 获取用户指令
        if args.instruction:
            instruction = args.instruction
        else:
            if args.json:
                # JSON模式下必须有指令参数
                error_result = {
                    "success": False,
                    "message": "JSON模式下必须提供instruction参数",
                    "steps": [],
                    "user_instruction": ""
                }
                print(json.dumps(error_result, ensure_ascii=False))
                sys.exit(1)
            # 交互式输入
            print("DeskJarvis Agent - 输入指令（输入'exit'退出）")
            instruction = input("> ").strip()
            if instruction.lower() == "exit":
                return
        
        # 执行任务（传递上下文）
        result = agent.execute(instruction, context=context)
        
        # 输出结果
        if args.json:
            # JSON模式：只输出JSON到stdout
            print(json.dumps(result, ensure_ascii=False))
        else:
            # 交互模式：输出详细信息
            print("\n" + "="*50)
            print("执行结果:")
            print("="*50)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            if result["success"]:
                print("\n✅ 任务执行成功！")
            else:
                print("\n❌ 任务执行失败")
                sys.exit(1)
            
    except KeyboardInterrupt:
        if args.json:
            error_result = {
                "success": False,
                "message": "用户中断",
                "steps": [],
                "user_instruction": args.instruction or ""
            }
            print(json.dumps(error_result, ensure_ascii=False))
        else:
            logger.info("用户中断")
        sys.exit(0)
    except Exception as e:
        if args.json:
            # JSON模式：捕获异常并返回JSON错误
            error_result = {
                "success": False,
                "message": f"程序错误: {str(e)}",
                "steps": [],
                "user_instruction": args.instruction or ""
            }
            print(json.dumps(error_result, ensure_ascii=False))
            # 详细错误信息输出到stderr
            import traceback
            traceback.print_exc(file=sys.stderr)
        else:
            logger.error(f"程序错误: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
