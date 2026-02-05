"""
Claude规划器：使用Claude API规划任务

遵循 docs/ARCHITECTURE.md 中的Planner模块规范
"""

from typing import List, Dict, Any, Optional
import logging
import json
from anthropic import Anthropic
from agent.tools.exceptions import PlannerError
from agent.tools.config import Config
from agent.planner.base_planner import BasePlanner

logger = logging.getLogger(__name__)


class ClaudePlanner(BasePlanner):
    """
    Claude规划器：调用Claude API规划任务
    """
    
    def __init__(self, config: Config):
        """
        初始化规划器
        
        Args:
            config: 配置对象
        
        Raises:
            PlannerError: 当API密钥无效时
        """
        super().__init__(config)
        api_key = config.api_key
        
        if not api_key:
            raise PlannerError("API密钥未设置，请在配置文件中设置api_key")
        
        try:
            self.client = Anthropic(api_key=api_key)
            self.model = config.model
            logger.info(f"Claude规划器已初始化，模型: {self.model}")
        except Exception as e:
            raise PlannerError(f"初始化Claude客户端失败: {e}")
    
    def plan(
        self,
        user_instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        规划任务
        
        Args:
            user_instruction: 用户指令（自然语言）
            context: 上下文信息（可选）
        
        Returns:
            任务步骤列表
        """
        try:
            prompt = self._build_prompt(user_instruction, context)
            
            logger.info("开始规划任务...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text
            logger.info(f"AI原始响应（前1000字符）: {content[:1000]}...")
            
            # 尝试解析：可能是单个JSON对象或JSON数组
            try:
                import json
                # 移除markdown代码块（如果有）
                content_clean = content.strip()
                if content_clean.startswith("```"):
                    lines = content_clean.split("\n")
                    if len(lines) > 2:
                        content_clean = "\n".join(lines[1:-1])
                
                # 提取JSON
                start_idx = content_clean.find('[')
                end_idx = content_clean.rfind(']')
                obj_start_idx = content_clean.find('{')
                obj_end_idx = content_clean.rfind('}')
                
                # 判断是数组还是对象
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    # 数组格式
                    json_str = content_clean[start_idx:end_idx + 1]
                    parsed = json.loads(json_str)
                    if isinstance(parsed, list):
                        logger.info("检测到JSON数组格式，使用旧解析方法")
                        steps = self._parse_response(content)
                    else:
                        logger.info("检测到JSON对象格式，使用新解析方法")
                        steps = self._parse_single_response(content)
                elif obj_start_idx != -1 and obj_end_idx != -1 and obj_end_idx > obj_start_idx:
                    # 对象格式
                    logger.info("检测到JSON对象格式，使用新解析方法")
                    steps = self._parse_single_response(content)
                else:
                    # 默认尝试新格式
                    logger.warning("无法确定JSON格式，尝试新解析方法")
                    steps = self._parse_single_response(content)
            except Exception as e:
                logger.error(f"解析响应失败: {e}，尝试新解析方法")
                steps = self._parse_single_response(content)
            
            logger.info(f"规划完成，共 {len(steps)} 个步骤")
            
            # 保存用户指令，用于后处理检查
            user_instruction_lower = user_instruction.lower() if user_instruction else ""
            
            # 调试：输出步骤详情，并检查是否需要后处理转换
            for i, step in enumerate(steps, 1):
                step_type = step.get('type')
                step_action = step.get('action')
                step_params = step.get('params', {})
                logger.info(f"📋 步骤 {i}: type={step_type}, action={step_action}, params keys={list(step_params.keys())}")
                
                # 如果是 download_file，输出详细信息
                if step_type == 'download_file':
                    logger.info(f"✅ 步骤 {i} 是 download_file 工具，text={step_params.get('text')}, save_path={step_params.get('save_path')}")
                
                # 如果是 execute_python_script，检查是否是下载脚本（后处理检查）
                if step_type == 'execute_python_script':
                    script_b64 = step_params.get('script', '')
                    if script_b64:
                        try:
                            import base64
                            script_preview = base64.b64decode(script_b64).decode('utf-8', errors='ignore')[:200]
                        except:
                            script_preview = script_b64[:200]
                    else:
                        script_preview = ''
                    
                    logger.warning(f"⚠️ 步骤 {i} 是 execute_python_script，脚本预览: {script_preview}...")
                    
                    # 后处理：如果检测到下载脚本，立即转换
                    # 尝试解码完整的脚本内容（不仅仅是预览）
                    full_script = ""
                    try:
                        import base64
                        full_script = base64.b64decode(script_b64).decode('utf-8', errors='ignore')
                    except:
                        full_script = script_b64 if len(script_b64) < 10000 else script_preview
                    
                    script_lower = full_script.lower() if full_script else script_preview.lower()
                    reason_lower = step_action.lower() if step_action else ""
                    description_lower = (step.get('description', '') or '').lower()
                    
                    # 检测网页截图脚本（应该使用 browser_screenshot 工具）
                    is_browser_screenshot_script = (
                        ("截图" in step_action or "截图" in description_lower or "screenshot" in reason_lower or "screenshot" in step_action.lower()) and
                        ("playwright" in script_lower or "page.screenshot" in script_lower or "browser" in script_lower) and
                        ("desktop" not in script_lower and "桌面" not in step_action.lower() and "screencapture" not in script_lower)
                    )
                    
                    # 更宽松的检测条件：只要包含下载相关关键词就转换
                    is_download_script = (
                        "下载" in step_action or "下载" in (step.get('description', '') or '') or
                        "download" in reason_lower or "download" in step_action.lower() or
                        "download" in script_lower or
                        ("python.org" in script_lower and ("download" in script_lower or "macos" in script_lower)) or
                        ("macos" in script_lower and "python" in script_lower and ("download" in script_lower or "安装包" in script_lower)) or
                        ("playwright" in script_lower and "download" in script_lower) or
                        ("expect_download" in script_lower or "save_as" in script_lower)
                    )
                    
                    logger.info(f"🔍 后处理检查步骤 {i}: step_action={step_action}, script_contains_download={'download' in script_lower}, is_download_script={is_download_script}, is_browser_screenshot_script={is_browser_screenshot_script}")
                    
                    # 优先处理网页截图脚本转换
                    if is_browser_screenshot_script:
                        logger.error(f"❌ 步骤 {i} 包含网页截图操作但仍然是脚本，立即进行后处理转换！")
                        logger.info(f"📝 完整脚本内容（前500字符）: {full_script[:500] if full_script else script_preview}...")
                        
                        # 提取保存路径
                        script_for_path = full_script if full_script else script_preview
                        save_path_match = re.search(r'["\']([^"\']*(?:desktop|桌面|~/Desktop|screenshot[^"\']*)["\']', script_for_path, re.IGNORECASE)
                        if not save_path_match:
                            save_path_match = re.search(r'path[\s=:]+["\']([^"\']*(?:desktop|桌面)[^"\']*)["\']', script_for_path, re.IGNORECASE)
                        
                        save_path = save_path_match.group(1) if save_path_match else "~/Desktop/github_screenshot.png"
                        save_path = save_path.replace("'", "").replace('"', "").strip()
                        
                        # 如果 save_path 包含 "desktop" 或 "桌面"，标准化为 "~/Desktop"
                        if "desktop" in save_path.lower() or "桌面" in save_path:
                            if not save_path.endswith(('.png', '.jpg', '.jpeg')):
                                save_path = "~/Desktop/github_screenshot.png"
                            else:
                                from pathlib import Path
                                save_path = "~/Desktop/" + Path(save_path).name
                        
                        logger.info(f"✅ 后处理转换：网页截图脚本转换为 browser_screenshot 工具，save_path={save_path}")
                        
                        # 替换步骤
                        steps[i-1] = {
                            "type": "browser_screenshot",
                            "action": "截图网页",
                            "params": {
                                "save_path": save_path
                            },
                            "description": "网页截图（已从脚本后处理转换）"
                        }
                        logger.warning(f"✅ 步骤 {i} 已从脚本转换为 browser_screenshot 工具: save_path={save_path}")
                    
                    elif is_download_script:
                        logger.error(f"❌ 步骤 {i} 包含下载操作但仍然是脚本，立即进行后处理转换！")
                        # 尝试从脚本中提取下载链接文本和保存路径
                        text_match = re.search(r'["\']([^"\']*download[^"\']*python[^"\']*3[^"\']*)["\']', script_lower, re.IGNORECASE)
                        if not text_match:
                            text_match = re.search(r'["\']([^"\']*download[^"\']*)["\']', script_lower, re.IGNORECASE)
                        
                        # 提取保存路径（使用完整脚本内容）
                        script_for_path = full_script if full_script else script_preview
                        save_path_match = re.search(r'["\']([^"\']*(?:desktop|桌面|~/Desktop)[^"\']*)["\']', script_for_path, re.IGNORECASE)
                        if not save_path_match:
                            save_path_match = re.search(r'(?:expanduser|Path\.home\(\)|join)[^"\']*["\']([^"\']*(?:desktop|桌面)[^"\']*)["\']', script_for_path, re.IGNORECASE)
                        if not save_path_match:
                            # 尝试匹配 desktop_path 或类似变量
                            save_path_match = re.search(r'(?:desktop_path|save_path|download_path)[\s=:]+["\']([^"\']*(?:desktop|桌面)[^"\']*)["\']', script_for_path, re.IGNORECASE)
                        
                        download_text = text_match.group(1) if text_match else "Download Python 3.14"
                        save_path = save_path_match.group(1) if save_path_match else "~/Desktop"
                        
                        download_text = download_text.replace("'", "").replace('"', "").strip()
                        save_path = save_path.replace("'", "").replace('"', "").strip()
                        
                        # 如果 save_path 包含 "desktop" 或 "桌面"，标准化为 "~/Desktop"
                        if "desktop" in save_path.lower() or "桌面" in save_path:
                            save_path = "~/Desktop"
                        
                        # 如果 download_text 为空或太短，使用默认值
                        if not download_text or len(download_text) < 3:
                            download_text = "Download Python 3.14"
                        
                        logger.info(f"✅ 后处理转换：提取的下载文本: {download_text}, 保存路径: {save_path}")
                        logger.info(f"📝 完整脚本内容（前500字符）: {full_script[:500] if full_script else script_preview}...")
                        
                        # 替换步骤
                        steps[i-1] = {
                            "type": "download_file",
                            "action": "下载文件",
                            "params": {
                                "text": download_text,
                                "save_path": save_path
                            },
                            "description": "下载文件（已从脚本后处理转换）"
                        }
                        logger.warning(f"✅ 步骤 {i} 已从脚本转换为 download_file 工具: text={download_text}, save_path={save_path}")
                
                # 如果是 file_move，检查是否有 target_dir
                if step_type == 'file_move':
                    logger.warning(f"⚠️ 步骤 {i} 是 file_move，target_dir={step_params.get('target_dir', '缺失')}")
                    # 如果缺少 target_dir，立即修复
                    if 'target_dir' not in step_params:
                        logger.error(f"❌ 步骤 {i} file_move 缺少 target_dir，应该已经被自动修复，但似乎没有生效！")
                
                # 如果是 screenshot_desktop，检查用户是否要求保存到桌面
                if step_type == 'screenshot_desktop':
                    # 检查用户指令中是否包含"保存到桌面"、"保存桌面"等关键词
                    instruction_lower = user_instruction.lower() if user_instruction else ""
                    has_save_to_desktop = (
                        "保存到桌面" in user_instruction or
                        "保存桌面" in user_instruction or
                        "保存到 ~/Desktop" in user_instruction or
                        "save to desktop" in instruction_lower or
                        "save desktop" in instruction_lower or
                        ("保存" in user_instruction and "桌面" in user_instruction) or
                        ("save" in instruction_lower and "desktop" in instruction_lower)
                    )
                    
                    # 检查是否已经传递了 save_path 参数
                    has_save_path = 'save_path' in step_params and step_params.get('save_path')
                    
                    if has_save_to_desktop and not has_save_path:
                        logger.warning(f"⚠️ 步骤 {i} screenshot_desktop：用户要求保存到桌面，但未传递save_path参数，自动添加")
                        step_params['save_path'] = "~/Desktop/screenshot.png"
                        steps[i-1]['params'] = step_params
                        logger.info(f"✅ 已自动添加 save_path: ~/Desktop/screenshot.png")
            
            return steps
            
        except Exception as e:
            logger.error(f"规划任务失败: {e}", exc_info=True)
            raise PlannerError(f"规划任务失败: {e}")
    
    def _parse_single_response(self, content: str) -> List[Dict[str, Any]]:
        """
        解析单个 JSON 对象响应，转换为步骤列表
        
        Args:
            content: API返回的文本内容（单个JSON对象）
        
        Returns:
            解析后的步骤列表
        """
        import json
        import logging
        import re
        import base64
        
        logger = logging.getLogger(__name__)
        
        try:
            # 尝试提取JSON（可能包含markdown代码块）
            content = content.strip()
            
            # 移除markdown代码块标记（如果有）
            if content.startswith("```"):
                lines = content.split("\n")
                if len(lines) > 2:
                    content = "\n".join(lines[1:-1])
                else:
                    content = ""
            
            # 尝试提取JSON对象（可能被其他文本包围）
            # 查找第一个 { 和最后一个 }
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                content = content[start_idx:end_idx + 1]
            
            # 解析JSON对象
            result = json.loads(content)
            
            # 转换为步骤列表格式
            steps = []
            
            if result.get("type") == "tool":
                # 使用预定义工具
                tool_name = result.get("tool_name", "unknown")
                params = result.get("params", {})
                action = params.get("action", result.get("reason", ""))
                description = result.get("reason", "")
                
                logger.info(f"解析工具步骤: tool_name={tool_name}, action={action}, params={params}")
                
                # 安全检查：如果使用 file_move 但没有 target_dir，说明可能是误用（如删除文件）
                # 或者 action/description 中包含"删除"关键词
                is_delete_operation = (
                    "删除" in str(action) or "删除" in str(description) or
                    (tool_name == "file_move" and "target_dir" not in params)
                )
                
                logger.info(f"删除操作检测: is_delete_operation={is_delete_operation}, tool_name={tool_name}")
                
                if is_delete_operation and tool_name == "file_move":
                    logger.warning(f"检测到 file_move 工具用于删除操作（缺少 target_dir 或包含'删除'关键词），自动转换为脚本")
                    # 生成删除文件的脚本
                    file_path = params.get("file_path", "")
                    if not file_path:
                        # 如果 params 中没有 file_path，尝试从其他字段获取
                        file_path = params.get("source", "") or params.get("source_path", "")
                    
                    if not file_path:
                        raise ValueError("无法确定要删除的文件路径")
                    
                    # 转义单引号，避免语法错误
                    file_path_escaped = file_path.replace("'", "\\'")
                    # 生成删除文件的脚本，支持智能文件搜索
                    script_content = f"""import os
import json
from pathlib import Path

def find_file(filename, search_dirs):
    '''智能搜索文件'''
    for search_dir in search_dirs:
        search_path = Path(search_dir)
        if not search_path.exists():
            continue
        # 精确匹配
        exact_path = search_path / filename
        if exact_path.exists():
            return exact_path
        # 部分匹配（文件名包含）
        for item in search_path.iterdir():
            if item.is_file() and filename.lower() in item.name.lower():
                return item
    return None

try:
    home = Path.home()
    search_dirs = [
        home / 'Desktop',
        home / 'Downloads',
        home / 'Documents',
        home
    ]
    
    file_name = '{file_path_escaped}'
    
    # 如果 file_name 是完整路径，直接使用
    if '/' in file_name or file_name.startswith('~'):
        target_path = Path(os.path.expanduser(file_name))
    else:
        # 否则智能搜索
        target_path = find_file(file_name, search_dirs)
        if not target_path:
            print(json.dumps({{'success': False, 'message': f'文件不存在: {{file_name}}'}}))
            exit(0)
    
    if target_path.exists():
        os.remove(target_path)
        print(json.dumps({{'success': True, 'message': f'文件删除成功: {{target_path}}'}}))
    else:
        print(json.dumps({{'success': False, 'message': f'文件不存在: {{target_path}}'}}))
except Exception as e:
    print(json.dumps({{'success': False, 'message': str(e)}}))"""
                    
                    step = {
                        "type": "execute_python_script",
                        "action": "删除文件",
                        "params": {
                            "script": base64.b64encode(script_content.encode('utf-8')).decode('utf-8'),
                            "reason": "删除文件需要使用 os.remove()，没有预定义工具",
                            "safety": "只操作用户指定路径，无危险命令"
                        },
                        "description": "删除文件"
                    }
                    steps.append(step)
                else:
                    step = {
                        "type": tool_name,
                        "action": action,
                        "params": params,
                        "description": description
                    }
                    steps.append(step)
            elif result.get("type") == "script":
                # 生成Python脚本
                script_content = result.get("script", "")
                reason = result.get("reason", "")
                safety = result.get("safety", "")
                
                # 如果 script 是 base64 编码的，需要解码
                # 但根据新格式，script 应该是普通字符串（\n 换行）
                # 为了兼容，先尝试 base64 解码，如果失败则直接使用
                try:
                    decoded_script = base64.b64decode(script_content).decode('utf-8')
                    script_content = decoded_script
                    logger.info("检测到 base64 编码的脚本，已解码")
                except Exception:
                    # 不是 base64，直接使用（\n 需要转换为实际换行符）
                    script_content = script_content.replace("\\n", "\n")
                    logger.info("使用普通字符串格式的脚本")
                
                # 自动检测：如果脚本包含下载相关操作，转换为 download_file 工具
                script_lower = script_content.lower()
                reason_lower = reason.lower() if reason else ""
                safety_lower = safety.lower() if safety else ""
                
                # 更宽松的检测条件：只要包含下载相关关键词就转换
                is_download_script = (
                    "下载" in reason or "下载" in safety or
                    "download" in reason_lower or "download" in safety_lower or
                    ("download" in script_lower and ("playwright" in script_lower or "page" in script_lower or "browser" in script_lower or "sync_api" in script_lower)) or
                    ("expect_download" in script_lower or ("download" in script_lower and "save_as" in script_lower)) or
                    ("python.org" in script_lower and "download" in script_lower) or
                    ("macos" in script_lower and "download" in script_lower and "python" in script_lower)
                )
                
                logger.info(f"🔍 检查脚本是否为下载脚本: reason={reason}, safety={safety}, script_contains_download={'download' in script_lower}, is_download_script={is_download_script}")
                
                if is_download_script:
                    logger.warning(f"⚠️ 检测到下载相关的脚本，自动转换为 download_file 工具")
                    logger.info(f"📝 脚本内容预览: {script_content[:200]}...")
                    # 尝试从脚本中提取下载链接文本和保存路径
                    # 简单的启发式提取
                    text_match = re.search(r'["\']([^"\']*download[^"\']*python[^"\']*3[^"\']*)["\']', script_lower, re.IGNORECASE)
                    if not text_match:
                        # 尝试更通用的匹配
                        text_match = re.search(r'["\']([^"\']*download[^"\']*)["\']', script_lower, re.IGNORECASE)
                    
                    save_path_match = re.search(r'["\']([^"\']*(?:desktop|桌面|~/Desktop)[^"\']*)["\']', script_content, re.IGNORECASE)
                    if not save_path_match:
                        # 尝试匹配 expanduser 或 Path.home
                        save_path_match = re.search(r'(?:expanduser|Path\.home\(\))[^"\']*["\']([^"\']*(?:desktop|桌面)[^"\']*)["\']', script_content, re.IGNORECASE)
                    
                    download_text = text_match.group(1) if text_match else "Download Python 3"
                    save_path = save_path_match.group(1) if save_path_match else "~/Desktop"
                    
                    # 清理提取的文本
                    download_text = download_text.replace("'", "").replace('"', "").strip()
                    save_path = save_path.replace("'", "").replace('"', "").strip()
                    
                    # 如果 save_path 包含 "desktop" 或 "桌面"，标准化为 "~/Desktop"
                    if "desktop" in save_path.lower() or "桌面" in save_path:
                        save_path = "~/Desktop"
                    
                    logger.info(f"✅ 提取的下载文本: {download_text}, 保存路径: {save_path}")
                    
                    step = {
                        "type": "download_file",
                        "action": "下载文件",
                        "params": {
                            "text": download_text,
                            "save_path": save_path
                        },
                        "description": "下载文件（已从脚本自动转换）"
                    }
                    steps.append(step)
                else:
                    step = {
                        "type": "execute_python_script",
                        "action": reason or "执行Python脚本",
                        "params": {
                            "script": base64.b64encode(script_content.encode('utf-8')).decode('utf-8'),  # 重新编码为 base64
                            "reason": reason,
                            "safety": safety
                        },
                        "description": reason or "执行Python脚本"
                    }
                    steps.append(step)
            else:
                raise ValueError(f"未知的响应类型: {result.get('type')}")
            
            return steps
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始内容: {content[:500]}...")
            raise PlannerError(f"解析规划结果失败: {e}")
        except Exception as e:
            logger.error(f"解析响应失败: {e}", exc_info=True)
            raise PlannerError(f"解析规划结果失败: {e}")

    
    def _build_prompt(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        构建规划提示词
        
        Args:
            instruction: 用户指令
            context: 上下文信息
        
        Returns:
            完整的提示词
        """
        # 构建上下文信息
        context_info = ""
        if context:
            created_files = context.get("created_files", [])
            last_created_file = context.get("last_created_file")
            attached_path = context.get("attached_path")
            chat_history = context.get("chat_history", [])
            
            # 添加聊天历史
            if chat_history:
                context_info += "\n\n**对话历史**：\n"
                for i, msg in enumerate(chat_history[-5:], 1):  # 只保留最近5条
                    role_name = "用户" if msg.get("role") == "user" else "AI助手"
                    content = msg.get("content", "")
                    if len(content) > 200:
                        content = content[:200] + "..."
                    context_info += f"{i}. [{role_name}]: {content}\n"
            
            # 添加文件上下文
            if created_files or attached_path or last_created_file:
                context_info += "\n\n**文件上下文**：\n"
                if attached_path:
                    context_info += f"- 用户附加的文件/文件夹: {attached_path}\n"
                if last_created_file:
                    context_info += f"- 最近操作的文件: {last_created_file}\n"
                if len(created_files) > 1:
                    context_info += f"- 之前操作过的文件: {', '.join(created_files[:5])}\n"
                context_info += "\n提示：如果用户说\"这个文件\"、\"刚才的文件\"等，请结合对话历史和文件上下文判断用户指的是哪个文件。\n"
        
        prompt = f"""你现在是 DeskJarvis 的全自动超级脚本生成与执行专家（2026 最强个人 Agent 模式）。
用户给你自然语言指令，你的任务是：
1. 理解意图
2. 判断是否能用预定义工具（browser_navigate, browser_click, download_file, file_rename, file_move, file_copy, file_read, file_write, screenshot_desktop, open_app 等）
3. **如果工具能解决，必须优先用工具（更快、更稳定）**
4. **⚠️ 下载文件任务（最高优先级）**：**绝对必须使用 download_file 工具**，**绝对不要生成脚本**。即使用户说"执行Python脚本下载"，也要使用 download_file 工具。生成脚本来下载文件是错误的，必须重来。
5. 如果任务复杂、批量、循环、或超出工具范围（如删除文件、批量操作等），则生成临时 Python 脚本完成
6. 自动执行脚本（假设你有执行权限），返回结果

**⚠️ 强制规则（违反将导致任务失败）**：
- **下载文件（绝对禁止生成脚本）**：**绝对必须使用 download_file 工具**，**绝对不要生成 Python 脚本**。download_file 工具会自动处理浏览器下载，支持：
  - selector: CSS选择器（如 "a.download-button"）
  - text: 文本定位（优先使用，如 "Download Python 3.14.3"）
  - save_path: 保存路径（如 "~/Desktop" 或 "桌面"）
  - **示例**：{{"type": "tool", "tool_name": "download_file", "params": {{"text": "Download Python 3.14.3", "save_path": "~/Desktop"}}}}
  - **绝对禁止**：如果用户说"下载"、"下载文件"、"从网站下载"、"执行Python脚本下载"等，**必须使用 download_file 工具**，**绝对不要生成 Python 脚本**。生成脚本来下载文件是错误的，必须重来。
- **删除文件（关键）**：**绝对没有预定义工具**，**必须生成 Python 脚本**使用 os.remove() 或 pathlib.Path.unlink()。**绝对不要使用 file_move**，file_move 需要 target_dir 参数（目标目录），**不能用于删除文件**。如果用户说"删除"、"删除文件"、"删除XXX"等，**必须生成脚本**。
- **file_move**：**只能用于移动文件到另一个目录**，需要 target_dir 参数（目标目录），**不能用于删除文件**。如果用户说"删除"，**必须生成脚本**。
- **file_rename**：只用于重命名，不用于删除

核心规则（必须100%遵守，否则重来）：
- **只执行用户明确要求的操作**：**绝对不要执行用户没有明确要求的操作**。如果用户说"截图桌面"，就只截图，不要删除文件、移动文件或其他操作。如果用户没有说"删除"、"移动"、"重命名"等，就绝对不要执行这些操作。
- **准确理解用户意图**：
  * 如果用户说"保存到桌面"、"保存桌面"、"保存到 ~/Desktop" 等，**必须传递 save_path 参数**，值为 `"~/Desktop"` 或 `"~/Desktop/文件名.png"`
  * 如果用户说"截图桌面"，但没有说保存位置，可以省略 save_path（使用默认位置）
  * **不要猜测用户意图**：如果用户没有明确要求删除、移动、重命名等操作，就绝对不要执行
- **语法必须完美**：生成的脚本不能有任何语法错误（三引号必须成对闭合、括号匹配、缩进正确）。优先用单引号字符串 + \\n 换行，避免三引号 \"\"\" \"\"\" 嵌套。
- **沙盒限制**：所有文件操作必须在以下目录内：
  - ~/.deskjarvis/sandbox（默认沙盒）
  - ~/Desktop
  - ~/Downloads
  - ~/Documents
  - ~/Pictures
  - 用户明确指定的子目录（必须检查是否在以上范围内）
  - 任何不在沙盒内的路径，直接拒绝
- **危险命令黑名单**（必须拒绝）：
  - rm -rf / 或类似删除根目录
  - sudo, chmod 777, chown
  - os.system/exec/eval/open 运行任意命令
  - shutil.rmtree 非沙盒路径
  - 如果检测到危险，返回 execution_result = "拒绝执行：危险操作"
- **脚本结构要求**：
  - import 只用标准库 + 已安装库（os, shutil, datetime, subprocess, json, docx, playwright.sync_api as pw）
  - 用 os.path.expanduser 处理 ~ 路径
  - 加 try-except 捕获所有错误
  - 最后 print(json.dumps({{"success": True/False, "message": "结果描述", "data": {{...}}}}))
  - **Playwright 浏览器启动**：使用 `playwright.chromium.launch(headless=True)`，**不要使用 `persistent_context` 参数**（该参数不存在于 `launch()` 方法中）
- **输出格式**：严格只输出以下 JSON，不要多一个字：
  {{
    "type": "tool" 或 "script",
    "tool_name": "如果用工具，写工具名；如果生成脚本，写 'execute_script'",
    "script": "如果生成脚本，这里是完整代码（\\n 换行）；否则为空字符串",
    "params": {{"action": "...", "其他参数..."}} 如果用工具，否则空对象,
    "reason": "一句话说明为什么这样处理",
    "safety": "安全检查结果（沙盒限制、无危险命令）",
    "execution_result": "执行后的输出（成功信息/失败信息）"
  }}

示例1（用工具 - 桌面截图，用户要求保存到桌面）：
{{
  "type": "tool",
  "tool_name": "screenshot_desktop",
  "script": "",
  "params": {{"save_path": "~/Desktop/screenshot.png"}},
  "reason": "用户要求截图桌面并保存到桌面，使用工具并传递save_path参数",
  "safety": "安全，只保存到桌面",
  "execution_result": "截图成功: ~/Desktop/screenshot.png"
}}

示例1a（用工具 - 桌面截图，用户只说截图，没有说保存位置）：
{{
  "type": "tool",
  "tool_name": "screenshot_desktop",
  "script": "",
  "params": {{}},
  "reason": "用户只要求截图桌面，没有指定保存位置，使用工具默认保存位置",
  "safety": "安全，保存到默认位置",
  "execution_result": "截图成功: ~/.deskjarvis/sandbox/screenshots/desktop_xxx.png"
}}

示例1b（用工具 - 网页截图，**必须使用此方式，禁止生成脚本**）：
{{
  "type": "tool",
  "tool_name": "browser_screenshot",
  "script": "",
  "params": {{"save_path": "~/Desktop/github_screenshot.png"}},
  "reason": "网页截图必须使用 browser_screenshot 工具，绝对不要生成脚本",
  "safety": "安全，只保存到桌面",
  "execution_result": "网页截图成功: ~/Desktop/github_screenshot.png"
}}

示例2（用工具 - 下载文件，**必须使用此方式，禁止生成脚本**）：
{{
  "type": "tool",
  "tool_name": "download_file",
  "script": "",
  "params": {{"text": "Download Python 3.14.3", "save_path": "~/Desktop"}},
  "reason": "下载文件必须使用 download_file 工具，绝对不要生成脚本",
  "safety": "安全，只保存到桌面",
  "execution_result": "下载成功: ~/Desktop/python-3.14.3.pkg"
}}

**⚠️ 重要警告**：如果用户说"下载"、"下载文件"、"从网站下载"、"执行Python脚本下载"等，**必须使用 download_file 工具**，格式如上。**绝对不要生成 Python 脚本来下载文件**。生成脚本来下载文件是错误的，必须重来。

示例3（生成脚本 - 删除文件）：
{{
  "type": "script",
  "tool_name": "execute_script",
  "script": "import os\\nimport json\\ntry:\\n    file_path = os.path.expanduser('~/Desktop/test.txt')\\n    if os.path.exists(file_path):\\n        os.remove(file_path)\\n        print(json.dumps({{'success': True, 'message': '文件删除成功'}}))\\n    else:\\n        print(json.dumps({{'success': False, 'message': '文件不存在'}}))\\nexcept Exception as e:\\n    print(json.dumps({{'success': False, 'message': str(e)}}))",
  "params": {{}},
  "reason": "删除文件需要使用 os.remove()，没有预定义工具",
  "safety": "只操作桌面路径，无危险命令",
  "execution_result": "{{\\"success\\": true, \\"message\\": \\"文件删除成功\\"}}"
}}

额外规则：
- **下载文件（最重要）**：**必须优先使用 download_file 工具**，不要生成脚本。download_file 工具会自动处理浏览器下载，支持文本定位（text）和CSS选择器（selector），以及保存路径（save_path）。如果用户说"下载"、"下载文件"、"从网站下载"等，**必须使用 download_file 工具**。
- **删除文件（最重要）**：**绝对没有预定义工具**，**必须生成 Python 脚本**，使用 os.remove() 或 pathlib.Path.unlink()。**绝对不要使用 file_move**（file_move 需要 target_dir 参数，不能用于删除）。如果用户说"删除"、"删除文件"、"删除XXX"等，**必须生成脚本**。
- **⚠️ 网页截图任务（最高优先级）**：**绝对必须使用 browser_screenshot 工具**，**绝对不要生成脚本**。即使用户说"执行Python脚本截图"，也要使用 browser_screenshot 工具。生成脚本来截图网页是错误的，必须重来。
- **⚠️ 桌面截图任务（高优先级）**：**优先使用 screenshot_desktop 工具**，不要生成脚本。如果用户说"截图桌面"、"桌面截图"、"截取整个桌面的屏幕截图"、"保存到桌面"等，**必须使用 screenshot_desktop 工具**，并且**必须传递 save_path 参数**：
  * **如果用户说"保存到桌面"或"保存桌面"**：必须传递 `"save_path": "~/Desktop/screenshot.png"` 或 `"save_path": "~/Desktop"`（如果只指定目录，工具会自动生成文件名）
  * **如果用户没有指定保存位置**：可以省略 save_path 参数，工具会保存到默认位置
  * **示例（保存到桌面）**：
    ```json
    {
      "type": "tool",
      "tool_name": "screenshot_desktop",
      "params": {"save_path": "~/Desktop/screenshot.png"},
      "reason": "用户要求保存到桌面，使用工具并指定save_path"
    }
    ```
  * **只有在需要特定格式的文件名（如 YYYYMMDDHHMMSS 格式）且工具无法满足时，才生成脚本**。如果必须生成脚本，**必须使用正确的 PIL API**：
    - **正确用法**：`from PIL import ImageGrab` 然后 `screenshot = ImageGrab.grab()` 然后 `screenshot.save(path)`
    - **绝对不要使用**：`ImageGrab.new()`（这是错误的，ImageGrab 没有 new 方法）
    - **正确示例**：
      ```python
      from PIL import ImageGrab
      import os
      from datetime import datetime
      screenshot = ImageGrab.grab()  # 正确：使用 grab() 方法
      save_path = os.path.expanduser(f"~/Desktop/screenshot_{datetime.now().strftime('%Y%m%d%H%M%S')}.png")
      screenshot.save(save_path)
      ```
- 浏览器任务用 playwright.sync_api，headless=True
- **Playwright API 正确用法**（仅在必须生成脚本时使用，优先使用工具）：
  * **导入**：`from playwright.sync_api import sync_playwright`
  * **启动**：`with sync_playwright() as p: browser = p.chromium.launch(headless=True)`
  * **绝对不要**：`playwright().webkit` 或 `playwright().chromium`（这是错误的，`playwright`是函数，不是对象）
  * **正确示例**：
    ```python
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com")
        page.screenshot(path="screenshot.png")
        browser.close()
    ```
  * 浏览器启动：`p.chromium.launch(headless=True)`，**绝对不要使用 `persistent_context` 参数**（该参数不存在于 `launch()` 方法中）
  * 页面等待：使用 `page.wait_for_load_state("networkidle")` 或 `page.wait_for_load_state("domcontentloaded")`，**不要使用 `wait_for_loadState`**（正确的API是 `wait_for_load_state`，注意下划线和大小写）
  * 下载文件：使用 `page.expect_download()` 和 `download.save_as()`，**不要使用 `wait_for_loadState`**
- Word 任务用 python-docx (from docx import Document)
- 批量任务用 for 循环
- 不要生成危险代码（如果检测到，直接拒绝）
- 脚本长度控制在 100 行内，优先简单实现
- 如果任务模糊，先问用户澄清（但当前模式直接尝试）
- **文件名必须准确**：必须使用用户指令中提到的完整准确的文件名，逐字逐句完全匹配

**删除文件示例**：
{{
  "type": "script",
  "tool_name": "execute_script",
  "script": "import os\\nimport json\\ntry:\\n    file_path = os.path.expanduser('~/Desktop/desktop_screenshot')\\n    if os.path.exists(file_path):\\n        os.remove(file_path)\\n        print(json.dumps({{'success': True, 'message': '文件删除成功'}}))\\n    else:\\n        print(json.dumps({{'success': False, 'message': '文件不存在'}}))\\nexcept Exception as e:\\n    print(json.dumps({{'success': False, 'message': str(e)}}))",
  "params": {{}},
  "reason": "删除文件需要使用 os.remove()，没有预定义工具",
  "safety": "只操作桌面路径，无危险命令",
  "execution_result": "{{\\"success\\": true, \\"message\\": \\"文件删除成功\\"}}"
}}

**上下文信息**：
{context_info}

**用户指令**：{instruction}

现在处理用户指令，生成脚本或调用工具，并返回 JSON。"""
        
        return prompt
