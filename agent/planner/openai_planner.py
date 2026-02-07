"""
OpenAI规划器：使用OpenAI API（ChatGPT）规划任务

遵循 docs/ARCHITECTURE.md 中的Planner模块规范
"""

from typing import List, Dict, Any, Optional
import logging
from openai import OpenAI
from agent.tools.exceptions import PlannerError
from agent.tools.config import Config
from agent.planner.base_planner import BasePlanner

logger = logging.getLogger(__name__)


class OpenAIPlanner(BasePlanner):
    """
    OpenAI规划器：调用OpenAI API规划任务
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
            self.client = OpenAI(api_key=api_key)
            self.model = config.model
            logger.info(f"OpenAI规划器已初始化，模型: {self.model}")
        except Exception as e:
            raise PlannerError(f"初始化OpenAI客户端失败: {e}")
    
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

            def call_llm(messages):
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,
                    max_tokens=4000,
                )

            messages = [
                {
                    "role": "system",
                    "content": "你是一个AI任务规划助手。请理解用户的自然语言指令，生成可执行的任务步骤。只返回JSON数组，不要添加其他文字。",
                },
                {"role": "user", "content": prompt},
            ]

            response = call_llm(messages)
            content = response.choices[0].message.content or ""
            logger.debug(f"AI响应: {content[:500]}...")

            try:
                steps = self._parse_response(content)
            except Exception as e:
                logger.warning(f"解析规划结果失败，将重试一次修复输出格式: {e}")
                retry_messages = [
                    {
                        "role": "system",
                        "content": "你是一个严格的JSON生成器。你只允许输出一个JSON数组（[]），不得包含任何其他字符。",
                    },
                    {
                        "role": "user",
                        "content": (
                            "上一次输出不是合法JSON，解析失败。\n"
                            "错误信息:\n"
                            + str(e)
                            + "\n\n"
                            "上一次原始输出（可能被截断）:\n"
                            + content[:1500]
                            + "\n\n"
                            "请重新输出合法JSON数组。规则：\n"
                            "- 只输出 JSON 数组（以 [ 开头，以 ] 结尾）\n"
                            "- 所有字符串必须使用双引号，且字符串内换行必须写成 \\n\n"
                            "- 不要输出 markdown 代码块\n"
                        ),
                    },
                ]
                response2 = call_llm(retry_messages)
                content2 = response2.choices[0].message.content or ""
                logger.debug(f"AI重试响应: {content2[:500]}...")
                steps = self._parse_response(content2)

            logger.info(f"规划完成，共 {len(steps)} 个步骤")
            
            # 保存用户指令，用于后处理检查
            user_instruction_lower = user_instruction.lower() if user_instruction else ""
            
            # 后处理：检查并修复 screenshot_desktop 缺少 save_path 的情况
            for i, step in enumerate(steps, 1):
                step_type = step.get('type')
                step_params = step.get('params', {})
                
                # 如果是 screenshot_desktop，检查用户是否要求保存到桌面
                if step_type == 'screenshot_desktop':
                    # 检查用户指令中是否包含"保存到桌面"、"保存桌面"等关键词
                    has_save_to_desktop = (
                        "保存到桌面" in user_instruction or
                        "保存桌面" in user_instruction or
                        "保存到 ~/Desktop" in user_instruction or
                        "save to desktop" in user_instruction_lower or
                        "save desktop" in user_instruction_lower or
                        ("保存" in user_instruction and "桌面" in user_instruction) or
                        ("save" in user_instruction_lower and "desktop" in user_instruction_lower)
                    )
                    
                    # 检查是否已经传递了 save_path 参数
                    has_save_path = 'save_path' in step_params and step_params.get('save_path')
                    
                    if has_save_to_desktop and not has_save_path:
                        logger.warning(f"⚠️ 步骤 {i} screenshot_desktop：用户要求保存到桌面，但未传递save_path参数，自动添加")
                        step_params['save_path'] = "~/Desktop/screenshot.png"
                        steps[i-1]['params'] = step_params
                        logger.info("✅ 已自动添加 save_path: ~/Desktop/screenshot.png")
            
            return steps
            
        except Exception as e:
            logger.error(f"规划任务失败: {e}", exc_info=True)
            raise PlannerError(f"规划任务失败: {e}")

    
    def _build_prompt(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """构建规划提示词"""
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
        
        prompt = f"""你是一个AI任务规划助手。请理解用户的自然语言指令，生成可执行的任务步骤。

**核心原则**：
- 理解用户的真实意图，而不是匹配关键词
- 思考如何完成任务，而不是选择工具
- 简单任务用工具，复杂任务用脚本
- 以结果为导向，只要能达到目标，用什么方法都可以

**你的能力**：
1. **文件操作**：读取、写入、创建、删除、重命名、移动、复制文件
2. **浏览器操作**：导航网页、点击、填写表单、下载文件、截图网页
3. **系统操作**：桌面截图、打开/关闭应用、打开文件/文件夹
4. **脚本执行**：生成并执行Python脚本完成复杂任务
5. **邮件发送**：发送带附件的邮件，支持多文件自动压缩
6. **验证码识别**：自动识别并填写简单的图片验证码

**可用工具**（简单任务优先使用）：
- file_read: 读取文件内容（支持.txt, .docx等）
- file_write: 写入文件内容（支持覆盖/追加模式）
- file_create: 创建新文件
- file_rename: 重命名文件
- file_move: 移动文件（可移动到回收站）。target_dir 参数支持完整路径（如 "~/Desktop/文件夹名"）或文件夹名（如 "8888"），系统会自动智能搜索文件夹。
- file_copy: 复制文件
- file_batch_rename: 批量重命名文件夹内的文件
- file_batch_copy: 批量复制文件夹内的文件
- file_batch_organize: 批量整理文件（按关键词、类型、时间分类）
- browser_navigate: 导航到网页URL
- browser_click: 点击页面元素
- browser_fill: 填写表单
- browser_wait: 等待页面加载
- browser_screenshot: 截图网页
- download_file: 下载文件（通过点击下载链接）
- screenshot_desktop: 截图整个桌面
- open_file: 用默认应用打开文件（只在用户明确说"打开文件"时使用）
- open_folder: 在文件管理器中打开文件夹（只在用户明确说"打开文件夹"时使用）
- open_app: 打开应用程序，params: {{"app_name": "应用名称"}}
- close_app: 关闭应用程序，params: {{"app_name": "应用名称"}}
- execute_python_script: 执行Python脚本（用于复杂任务或工具无法满足的需求）
- send_email: 发送邮件，params: {{"recipient": "收件人", "subject": "主题", "body": "正文", "attachments": ["文件路径列表"]}}
- compress_files: 压缩文件，params: {{"files": ["文件路径列表"], "output": "输出zip路径", "type": "zip"}}
- request_qr_login: 请求二维码登录，params: {{"site_name": "网站名称", "qr_selector": "可选选择器"}}
- request_captcha: 请求验证码识别，params: {{"captcha_image_selector": "图片选择器", "captcha_input_selector": "输入框选择器", "site_name": "网站名"}}
- request_login: 请求登录，params: {{"site_name": "名称", "username_selector": "可选", "password_selector": "可选"}}

**Python脚本执行**（复杂任务或工具无法满足时使用）：
- script: Python代码，**必须使用 base64 编码**（避免JSON转义问题）
- reason: 为什么使用脚本而不是工具
- safety: 安全检查说明
- **脚本要求**：
  * 安全：文件操作限制在用户主目录或沙盒目录（~/Desktop, ~/Downloads, ~/.deskjarvis/sandbox）
  * 禁止危险命令：rm -rf /, sudo, chmod 777 等
  * 必须使用 try-except 包裹可能失败的操作
  * 输出格式：`print(json.dumps({{"success": True/False, "message": "...", "data": {{...}}}}))`
  * Python布尔值：使用 `True`/`False`（首字母大写），不是 `true`/`false`
  * 浏览器操作：使用 `playwright.sync_api` 模块
  * 文件操作：使用 `os`, `shutil`, `pathlib` 模块
  * **Word文档处理**：使用 `python-docx` 库，导入方式：`from docx import Document`（**不要使用** `import docxplr` 或其他库名）
  * **文件路径**：脚本中应该**直接使用文件路径**（硬编码），不要从环境变量读取。使用 `os.path.expanduser()` 或 `pathlib.Path.home()` 处理 `~` 符号。例如：`file_path = os.path.expanduser("~/Desktop/file.docx")`
  * **重要**：文件路径**不要进行 URL 编码**（不要使用 `urllib.parse.quote()` 或类似函数），直接使用原始的中文文件名。例如：`"~/Desktop/强制执行申请书.docx"` 而不是 `"~/Desktop/%E5%BC%BA%E5%88%B6%E6%89%A7%E8%A1%8C%E7%94%B3%E8%AF%B7%E4%B9%A6.docx"`
  * **文件名必须准确**：必须使用用户指令中提到的**完整准确的文件名**，不要随意更改、替换或编码文件名。
    - **重要**：文件名必须**逐字逐句完全匹配**用户指令中的文件名，包括中文字符、英文、数字、扩展名等。
    - **示例1**：如果用户说"强制执行申请书.docx"，脚本中必须使用 `"强制执行申请书.docx"`，**绝对不要**改成 `"大取同学名称.docx"`、`"求正放接探底作品.docx"` 或其他任何名称。
    - **示例2**：如果用户说"总结.txt"，必须使用 `"总结.txt"`，**绝对不要**改成 `"连排.txt"`、`"输克.txt"` 或其他任何名称。
    - **检查方法**：生成脚本后，检查脚本中的文件名是否与用户指令中的文件名完全一致，如果不一致，必须修正。
  * **Python语法安全**：
    - **禁止**在 f-string 中使用复杂嵌套引号。例如 `f"Status: {{json.dumps(...)}}"` 极易出错。请分开写：`status_json = json.dumps(...); print(f"Status: {{status_json}}")`
    - **字符串转义**：如果字符串包含反斜杠（Windows路径），必须使用 raw string (r"...") 或双反斜杠。
    - **JSON输出**：message 字段尽量使用简单的中文或英文，避免特殊字符（如换行符、未转义的引号）。
    - **错误处理**：`try-except` 必须捕获所有异常，并且打印的错误信息不能包含可能破坏 JSON 结构的字符。使用 `repr(e)` 而不是 `str(e)` 可以更安全地打印异常。
  * **文件名准确性**：必须使用用户指令中提到的**准确文件名**，不要随意更改文件名。

**路径格式**：
- 支持相对路径（如 "Desktop/file.txt"）
- 支持绝对路径（如 "~/Desktop/file.txt"）
- 支持文件名（系统会自动搜索）
- 支持 ~ 符号（如 "~/Desktop"）

**优先使用上下文**：
- 如果用户说 "这个文件"、"这个文件夹"、"整理它"、"帮我处理" 等指代词，但指令中没有明确文件名，**必须优先使用 {context_info} 中的 [用户附加的文件/文件夹] (attached_path)**。
- 如果 attached_path 为空，尝试使用 [最近操作的文件] (last_created_file)。
- **切记**：不要凭空捏造文件名，如果找不到任何上下文文件，请在 message 中询问用户。

**重要规则**：
- **桌面截图任务**：
  * 如果用户要求"截图并保存为..."、"截图并重命名..."、"截图后处理..."：**必须在 screenshot_desktop 步骤中指定一个确定的 save_path**（例如 "~/Desktop/temp_screenshot.png"），以便后续步骤（如 python_script）能准确找到该文件。
  * 如果用户说"保存到桌面"或"保存桌面"：传递 `"save_path": "~/Desktop/screenshot.png"`（必须包含文件名和 .png 后缀，不要只传目录）
  * 如果用户只说"截图桌面"但没有说保存位置：可以省略 save_path（使用默认位置）
- **准确理解用户意图**：如果用户说"保存到桌面"，必须传递 save_path 参数

**工作流模式**：
- **下载需要登录的网站**：
  1. browser_navigate
  2. request_login 或 request_qr_login
  3. browser_wait (等待登录同步，建议2000-3000ms)
  4. download_file
- **发送邮件附件**：
  1. (如果多个文件) compress_files (注意输出路径必须在 /tmp/ 下)
  2. send_email

**上下文理解**：
{context_info}

**用户指令**：{instruction}

请生成JSON数组格式的执行步骤，每个步骤包含：
- type: 步骤类型（字符串）
- action: 操作描述（字符串）
- params: 参数对象
- description: 步骤说明（字符串）

**重要**：
- 只输出JSON数组，不要添加其他文字
- 如果使用 execute_python_script，script字段必须使用 base64 编码
- JSON格式必须严格正确，可以被Python的json.loads()解析

示例：
[
  {{
    "type": "file_read",
    "action": "读取文件",
    "params": {{"file_path": "~/Desktop/test.txt"}},
    "description": "读取桌面上的test.txt文件"
  }},
  {{
    "type": "execute_python_script",
    "action": "处理文件内容",
    "params": {{
      "script": "aW1wb3J0IGpzb24KcHJpbnQoanNvbi5kdW1wcyh7InN1Y2Nlc3MiOiBUcnVlLCAibWVzc2FnZSI6ICJjb21wbGV0ZSJ9KSk=",
      "reason": "需要处理文件内容并生成总结",
      "safety": "文件操作限制在用户主目录，使用try-except包裹"
    }},
    "description": "执行Python脚本处理文件内容"
  }}
]"""
        
        return prompt
