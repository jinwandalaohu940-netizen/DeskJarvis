"""
浏览器执行器：使用Playwright控制浏览器

遵循 docs/ARCHITECTURE.md 中的Executor模块规范
"""

from typing import Dict, Any, Optional
import logging
import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from agent.tools.exceptions import BrowserError
from agent.tools.config import Config

logger = logging.getLogger(__name__)


class BrowserExecutor:
    """
    浏览器执行器：使用Playwright执行浏览器操作
    
    职责：
    - 控制独立headless浏览器实例
    - 执行导航、点击、填写等操作
    - 下载文件
    - 截图（用于调试）
    """
    
    def __init__(self, config: Config):
        """
        初始化浏览器执行器
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.download_path = config.sandbox_path / "downloads"
        self.download_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"浏览器执行器已初始化，下载目录: {self.download_path}")
    
    def start(self) -> None:
        """
        启动浏览器实例
        
        Raises:
            BrowserError: 当启动失败时
        """
        try:
            logger.info("正在启动浏览器...")
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            self.context = self.browser.new_context(
                accept_downloads=True,
                viewport={"width": 1920, "height": 1080}
            )
            self.page = self.context.new_page()
            logger.info("✅ 浏览器已启动")
        except Exception as e:
            error_msg = f"启动浏览器失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def stop(self) -> None:
        """停止浏览器实例"""
        try:
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("浏览器已停止")
        except Exception as e:
            logger.warning(f"停止浏览器时出错: {e}")
    
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行单个任务步骤
        
        Args:
            step: 任务步骤，包含type、action、params等
        
        Returns:
            执行结果，包含success、message、data等
        
        Raises:
            BrowserError: 当执行失败时
        """
        if not self.page:
            raise BrowserError("浏览器未启动，请先调用start()")
        
        step_type = step.get("type")
        action = step.get("action", "")
        params = step.get("params", {})
        
        logger.info(f"执行步骤: {step_type} - {action}")
        
        try:
            if step_type == "browser_navigate":
                return self._navigate(params)
            elif step_type == "browser_click":
                return self._click(params)
            elif step_type == "browser_fill":
                return self._fill(params)
            elif step_type == "browser_wait":
                return self._wait(params)
            elif step_type == "browser_screenshot":
                return self._screenshot(params)
            elif step_type == "download_file":
                return self._download_file(params)
            else:
                raise BrowserError(f"未知的步骤类型: {step_type}")
                
        except Exception as e:
            logger.error(f"执行步骤失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"执行失败: {e}",
                "data": None
            }
    
    def _navigate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        导航到URL（只能用于HTTP/HTTPS URL，不能用于本地文件路径）
        
        Args:
            params: 参数字典，包含url
        
        Returns:
            执行结果字典
        
        Raises:
            BrowserError: 当导航失败时
        """
        url = params.get("url")
        if not url:
            raise BrowserError("导航参数缺少url")
        
        # 检查是否是本地文件路径
        if url.startswith("file://") or url.startswith("/"):
            raise BrowserError(
                f"browser_navigate 不能用于本地文件路径: {url}。"
                f"请使用 open_folder 工具打开本地文件夹。"
            )
        
        try:
            logger.info(f"导航到: {url}")
            self.page.goto(url, wait_until="networkidle", timeout=60000)
            logger.info(f"✅ 已导航到: {url}")
            
            return {
                "success": True,
                "message": f"已导航到: {url}",
                "data": {"url": url}
            }
        except Exception as e:
            error_msg = f"导航失败: {url} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _click(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        点击元素（增强版：支持文本定位 + 等待可见 + 滚动 + 多元素处理）
        
        Args:
            params: 参数字典
                - selector: CSS选择器（可选）
                - text: 文本内容（可选，优先使用）
                - timeout: 超时时间（毫秒，默认60000）
        
        Returns:
            执行结果字典
        
        Raises:
            BrowserError: 当点击失败时
        """
        selector = params.get("selector")
        text = params.get("text")  # 新增：文本定位参数
        timeout = params.get("timeout", 60000)
        
        if not selector and not text:
            raise BrowserError("点击参数缺少selector或text")
        
        try:
            # 步骤1: 根据参数类型选择定位方式
            if text:
                # 使用文本定位（优先）
                locator = self.page.get_by_text(text, exact=False)
                logger.info(f"使用文本定位: {text}")
            elif selector.startswith("text="):
                # 支持 text= 格式
                text_content = selector[5:].strip()
                locator = self.page.get_by_text(text_content, exact=False)
                logger.info(f"使用text=格式定位: {text_content}")
            elif ":contains(" in selector or "contains" in selector.lower():
                # 检测到 contains 语法，提取文本内容
                import re
                match = re.search(r":contains\(['\"](.*?)['\"]\)", selector)
                if match:
                    text_content = match.group(1)
                    base_selector = re.sub(r":contains\(['\"].*?['\"]\)", "", selector)
                    base_locator = self.page.locator(base_selector)
                    locator = base_locator.filter(has_text=text_content)
                else:
                    locator = self.page.locator(selector)
            else:
                # 使用CSS选择器
                logger.info(f"使用CSS选择器定位: {selector}")
                locator = self.page.locator(selector)
            
            # 步骤2: 等待元素出现并可见（关键修复）
            logger.info(f"等待元素可见...")
            
            # 检查有多少个匹配元素
            # 使用 all() 方法获取所有匹配的元素，然后获取长度（更可靠）
            try:
                all_elements = locator.all()
                count = len(all_elements)
            except Exception as e:
                # 如果 all() 失败，尝试使用 count 属性
                try:
                    count_value = locator.count
                    # 检查是否是方法（callable）还是属性值
                    if callable(count_value):
                        count = count_value()
                    else:
                        count = count_value
                    # 确保是整数
                    count = int(count) if isinstance(count, (int, float)) else 1
                except Exception:
                    logger.warning(f"无法确定匹配元素数量，假设至少有1个: {e}")
                    count = 1
            
            logger.info(f"找到 {count} 个匹配元素")
            
            if count == 0:
                # 元素不存在，先截图调试
                screenshot_path = self.download_path / f"click_error_{int(time.time())}.png"
                self.page.screenshot(path=str(screenshot_path))
                raise BrowserError(f"未找到元素，已截图: {screenshot_path}")
            
            # 确保 count 是整数
            count = int(count)
            
            # 步骤3: 选择第一个可见的元素（关键修复）
            # 如果多个匹配，优先选择可见的第一个
            visible_locator = None
            for i in range(min(count, 10)):  # 最多检查前10个
                try:
                    candidate = locator.nth(i)
                    # 检查是否可见（使用 Playwright 的可见性检查）
                    if candidate.is_visible(timeout=1000):
                        visible_locator = candidate
                        logger.info(f"选择第 {i+1} 个可见元素")
                        break
                except Exception:
                    continue
            
            if not visible_locator:
                # 如果都不可见，尝试滚动到第一个并等待
                logger.warning(f"所有匹配元素都不可见，尝试滚动到第一个元素")
                first_locator = locator.first
                # 滚动到元素（关键修复）
                first_locator.scroll_into_view_if_needed(timeout=timeout)
                # 再次等待可见
                first_locator.wait_for(state="visible", timeout=timeout)
                visible_locator = first_locator
            
            # 步骤4: 确保元素在视口内（滚动）
            visible_locator.scroll_into_view_if_needed(timeout=5000)
            
            # 步骤5: 等待元素稳定（可点击状态）
            visible_locator.wait_for(state="attached", timeout=5000)
            
            # 步骤6: 执行点击
            logger.info(f"执行点击...")
            visible_locator.click(timeout=timeout)
            
            logger.info(f"✅ 已成功点击元素")
            
            return {
                "success": True,
                "message": f"已点击元素",
                "data": {"selector": selector, "text": text, "matched_count": count}
            }
            
        except Exception as e:
            # 失败时自动截图（关键调试功能）
            screenshot_path = self.download_path / f"click_error_{int(time.time())}.png"
            try:
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.error(f"点击失败，已截图: {screenshot_path}")
            except Exception:
                pass
            
            error_msg = f"点击元素失败: {selector or text} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _fill(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """填写表单字段"""
        selector = params.get("selector")
        value = params.get("value")
        
        if not selector or value is None:
            raise BrowserError("填写参数缺少selector或value")
        
        try:
            logger.info(f"填写字段: {selector} = {value}")
            self.page.fill(selector, str(value))
            logger.info(f"✅ 已填写字段")
            
            return {
                "success": True,
                "message": f"已填写字段: {selector}",
                "data": {"selector": selector, "value": value}
            }
        except Exception as e:
            error_msg = f"填写字段失败: {selector} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _wait(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """等待指定时间或条件"""
        timeout = params.get("timeout", 5000)
        
        try:
            logger.info(f"等待 {timeout} 毫秒...")
            self.page.wait_for_timeout(timeout)
            logger.info(f"✅ 等待完成")
            
            return {
                "success": True,
                "message": f"等待完成",
                "data": {"timeout": timeout}
            }
        except Exception as e:
            error_msg = f"等待失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _screenshot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        浏览器页面截图
        
        Args:
            params: 包含save_path（保存路径，可选）
                    - 可以是相对路径（相对于用户主目录）
                    - 可以是绝对路径（必须在用户主目录下）
                    - 支持 ~ 符号（如 ~/Desktop/github.png）
                    - 如果不指定，默认保存到沙盒下载目录
        """
        save_path_str = params.get("save_path")
        home = Path.home()
        
        if save_path_str:
            # 处理 ~ 符号
            if save_path_str.startswith("~/"):
                save_path_str = str(home / save_path_str[2:])
            elif save_path_str.startswith("~"):
                save_path_str = str(home / save_path_str[1:])
            
            save_path = Path(save_path_str)
            
            # 如果是相对路径，相对于用户主目录
            if not save_path.is_absolute():
                save_path = home / save_path
            
            save_path = save_path.resolve()
            
            # 安全：确保路径在用户主目录下
            try:
                save_path.relative_to(home)
            except ValueError:
                logger.warning(f"路径不在用户主目录下，使用默认路径: {save_path}")
                save_path = self.download_path / f"screenshot_{int(time.time())}.png"
        else:
            save_path = self.download_path / f"screenshot_{int(time.time())}.png"
        
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"浏览器页面截图保存到: {save_path}")
            self.page.screenshot(path=str(save_path), full_page=True)
            logger.info(f"✅ 浏览器页面截图已保存")
            
            return {
                "success": True,
                "message": f"浏览器页面截图已保存: {save_path}",
                "data": {"path": str(save_path)}
            }
        except Exception as e:
            error_msg = f"浏览器页面截图失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _download_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        下载文件（通过点击下载链接，使用增强的点击逻辑）
        
        修复要点：
        1. 使用增强的点击逻辑（等待可见 + 滚动）
        2. 监听下载事件（page.expect_download）
        3. 保存到指定路径（支持 ~、相对路径、绝对路径）
        4. 自动创建目录
        5. 文件存在验证
        6. 截图调试
        7. 超时延长（默认60秒）
        
        Args:
            params: 参数字典
                - selector: CSS选择器或文本定位（必需）
                - save_path: 保存路径（支持 ~、相对路径、绝对路径）
                - timeout: 超时时间（毫秒，默认60000）
        
        Returns:
            执行结果字典
        
        Raises:
            BrowserError: 当下载失败时
        """
        selector = params.get("selector")
        text = params.get("text")  # 文本定位参数（优先使用）
        save_path = params.get("save_path")
        timeout = params.get("timeout", 60000)  # 默认60秒超时
        
        # selector 和 text 至少需要一个
        if not selector and not text:
            raise BrowserError("下载参数缺少selector或text，至少需要提供一个")
        
        try:
            # 步骤1: 解析保存路径（在点击前解析，以便提前创建目录）
            if save_path:
                # 处理中文"桌面"和英文"Desktop"
                save_path_normalized = save_path.strip()
                if save_path_normalized == "桌面" or save_path_normalized.lower() == "desktop":
                    file_path = Path.home() / "Desktop"
                    logger.info(f"检测到'桌面'或'Desktop'，解析为: {file_path}")
                elif save_path_normalized.startswith("~/"):
                    file_path = Path.home() / save_path_normalized[2:]
                elif save_path_normalized.startswith("~"):
                    file_path = Path.home() / save_path_normalized[1:]
                else:
                    file_path = Path(save_path_normalized)
                
                # 如果是相对路径，相对于用户主目录
                if not file_path.is_absolute():
                    file_path = Path.home() / file_path
                
                file_path = file_path.resolve()
                
                # 确保目录存在（如果路径是目录）
                if file_path.exists() and file_path.is_dir():
                    # 路径是目录，稍后会添加文件名
                    logger.info(f"目标保存目录: {file_path}")
                else:
                    # 路径可能是文件路径，确保父目录存在
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    logger.info(f"目标保存路径: {file_path}")
            else:
                # 如果没有指定路径，使用默认下载目录
                file_path = None
                logger.info("未指定保存路径，将使用默认下载目录")
            
            # 步骤2: 定位并点击下载链接
            logger.info(f"准备下载文件，点击链接: {selector or text}")
            
            # 定位元素（支持文本定位和CSS选择器）
            if text:
                # 使用文本定位（优先）
                locator = self.page.get_by_text(text, exact=False)
                logger.info(f"使用文本定位: {text}")
            elif selector and selector.startswith("text="):
                # 支持 text= 格式
                text_content = selector[5:].strip()
                locator = self.page.get_by_text(text_content, exact=False)
                logger.info(f"使用text=格式定位: {text_content}")
            elif selector:
                # 使用CSS选择器
                locator = self.page.locator(selector)
                logger.info(f"使用CSS选择器定位: {selector}")
            else:
                # 理论上不会到这里（前面已经检查过）
                raise BrowserError("下载参数缺少selector或text")
            
            # 检查有多少个匹配元素
            # 使用 all() 方法获取所有匹配的元素，然后获取长度（更可靠）
            try:
                all_elements = locator.all()
                count = len(all_elements)
            except Exception as e:
                # 如果 all() 失败，尝试使用 count 属性
                try:
                    count_value = locator.count
                    # 检查是否是方法（callable）还是属性值
                    if callable(count_value):
                        count = count_value()
                    else:
                        count = count_value
                    # 确保是整数
                    count = int(count) if isinstance(count, (int, float)) else 1
                except Exception:
                    logger.warning(f"无法确定匹配元素数量，假设至少有1个: {e}")
                    count = 1
            
            logger.info(f"找到 {count} 个匹配元素")
            
            if count == 0:
                screenshot_path = self.download_path / f"download_error_{int(time.time())}.png"
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise BrowserError(f"未找到下载链接: {selector or text}，已截图: {screenshot_path}")
            
            # 确保 count 是整数
            count = int(count)
            
            # 选择第一个可见的元素
            visible_locator = None
            for i in range(min(count, 10)):
                try:
                    candidate = locator.nth(i)
                    if candidate.is_visible(timeout=1000):
                        visible_locator = candidate
                        logger.info(f"选择第 {i+1} 个可见的下载链接")
                        break
                except Exception:
                    continue
            
            if not visible_locator:
                # 如果都不可见，尝试滚动到第一个并等待
                logger.warning(f"所有匹配元素都不可见，尝试滚动到第一个元素")
                visible_locator = locator.first
                visible_locator.scroll_into_view_if_needed(timeout=timeout)
                visible_locator.wait_for(state="visible", timeout=timeout)
            
            # 确保元素在视口内（滚动）
            visible_locator.scroll_into_view_if_needed(timeout=5000)
            
            # 等待元素稳定（可点击状态）
            visible_locator.wait_for(state="attached", timeout=5000)
            
            # 步骤3: 监听下载事件并点击
            logger.info(f"监听下载事件并点击: {selector or text}")
            with self.page.expect_download(timeout=timeout) as download_info:
                visible_locator.click(timeout=timeout)
            
            # 步骤4: 获取下载对象
            download = download_info.value
            # 在 Playwright 同步 API 中，suggested_filename 是属性，不是方法
            # 但为了兼容性，先检查是否是方法
            if hasattr(download, 'suggested_filename'):
                suggested_filename_attr = getattr(download, 'suggested_filename')
                if callable(suggested_filename_attr):
                    suggested_filename = suggested_filename_attr()
                else:
                    suggested_filename = suggested_filename_attr
            else:
                # 如果没有 suggested_filename，使用默认名称
                suggested_filename = "download"
            logger.info(f"检测到下载: {suggested_filename}")
            
            # 步骤5: 确定最终保存路径
            if file_path:
                # 检查路径是否是目录
                is_directory = False
                if file_path.exists():
                    is_directory = file_path.is_dir()
                else:
                    # 如果路径不存在，检查是否有扩展名来判断
                    # 如果没有扩展名，可能是目录
                    if not file_path.suffix:
                        is_directory = True
                
                if is_directory:
                    # 路径是目录，添加下载的文件名
                    file_path = file_path / suggested_filename
                    logger.info(f"路径是目录，添加文件名: {file_path}")
                elif not file_path.suffix and suggested_filename:
                    # 如果路径没有扩展名，使用下载文件的扩展名
                    suggested = Path(suggested_filename)
                    file_path = file_path.with_suffix(suggested.suffix)
                    logger.info(f"路径缺少扩展名，添加扩展名: {file_path}")
                else:
                    # 路径已经是完整文件路径
                    logger.info(f"使用指定的完整文件路径: {file_path}")
            else:
                # 使用默认下载目录
                file_path = self.download_path / suggested_filename
                logger.info(f"使用默认下载目录: {file_path}")
            
            # 确保目录存在（再次检查，防止路径解析后目录不存在）
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 步骤6: 保存文件
            logger.info(f"正在保存文件到: {file_path}")
            download.save_as(str(file_path))
            
            # 步骤7: 验证文件是否存在
            if not file_path.exists():
                screenshot_path = self.download_path / f"download_error_{int(time.time())}.png"
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise BrowserError(f"文件保存失败，文件不存在: {file_path}，已截图: {screenshot_path}")
            
            file_size = file_path.stat().st_size
            logger.info(f"✅ 文件已下载: {file_path} (大小: {file_size} 字节)")
            
            return {
                "success": True,
                "message": f"文件已下载: {file_path}",
                "data": {
                    "path": str(file_path),
                    "size": file_size,
                    "filename": file_path.name
                }
            }
            
        except Exception as e:
            # 失败时自动截图（关键调试功能）
            screenshot_path = self.download_path / f"download_error_{int(time.time())}.png"
            try:
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.error(f"下载失败，已截图: {screenshot_path}")
            except Exception:
                pass
            
            selector_str = selector or text or "未提供selector或text"
            error_msg = f"下载文件失败: {selector_str} - {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise BrowserError(error_msg)
    
    def _handle_download(self, download) -> None:
        """处理下载事件"""
        # 在 Playwright 同步 API 中，suggested_filename 是属性，不是方法
        try:
            suggested_filename = download.suggested_filename if not callable(download.suggested_filename) else download.suggested_filename()
        except AttributeError:
            suggested_filename = "未知文件名"
        logger.info(f"检测到下载: {suggested_filename}")
