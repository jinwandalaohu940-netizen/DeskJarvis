"""
系统工具：系统级操作（截图、系统命令等）

遵循 docs/ARCHITECTURE.md 中的Executor模块规范
"""

from typing import Dict, Any, List, Optional
import logging
import sys
import subprocess
import time
from pathlib import Path
from agent.tools.exceptions import BrowserError
from agent.tools.config import Config

logger = logging.getLogger(__name__)


class SystemTools:
    """
    系统工具：执行系统级操作
    
    职责：
    - 桌面截图
    - 系统命令执行（未来扩展）
    """
    
    def __init__(self, config: Config):
        """
        初始化系统工具
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.sandbox_path = Path(config.sandbox_path).resolve()
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"系统工具已初始化，沙盒目录: {self.sandbox_path}")
    
    def _find_folder(self, folder_name: str, search_dirs: List[Path] = None) -> Optional[Path]:
        """
        智能搜索文件夹：在指定目录中搜索文件夹名
        
        支持：
        - 精确匹配（如 "8888"）
        - 部分匹配（如 "88" 可以匹配 "8888"）
        
        Args:
            folder_name: 文件夹名（如 "8888"）
            search_dirs: 搜索目录列表，默认为用户主目录下的常用目录
        
        Returns:
            找到的文件夹路径，如果未找到返回None
        """
        if search_dirs is None:
            home = Path.home()
            search_dirs = [
                home / "Desktop",
                home / "Downloads",
                home / "Documents",
                home,  # 也在主目录下搜索
                self.sandbox_path,
            ]
        
        # 规范化文件夹名（去除前后空格）
        folder_name = folder_name.strip()
        
        # 1. 先尝试直接匹配文件夹名（精确匹配）
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            candidate = search_dir / folder_name
            if candidate.exists() and candidate.is_dir():
                logger.info(f"精确匹配找到文件夹: {candidate}")
                return candidate
        
        # 2. 部分匹配：文件夹名包含在文件夹名的开头
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                for item in search_dir.iterdir():
                    if item.is_dir():
                        item_name = item.name
                        # 如果用户输入的文件夹名包含在文件夹名的开头，或者文件夹名包含用户输入
                        if folder_name in item_name or item_name.startswith(folder_name):
                            logger.info(f"部分匹配找到文件夹: {item} (匹配: {folder_name})")
                            return item
            except (PermissionError, OSError):
                continue
        
        # 3. 递归搜索（限制深度为2）
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
            try:
                # 先尝试精确匹配
                for item in search_dir.rglob(folder_name):
                    if item.is_dir():
                        logger.info(f"递归搜索找到文件夹: {item}")
                        return item
                
                # 再尝试部分匹配（递归）
                for item in search_dir.rglob("*"):
                    if item.is_dir():
                        item_name = item.name
                        if folder_name in item_name or item_name.startswith(folder_name):
                            logger.info(f"递归部分匹配找到文件夹: {item} (匹配: {folder_name})")
                            return item
            except (PermissionError, OSError):
                continue
        
        logger.warning(f"未找到文件夹: {folder_name}")
        return None
    
    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行系统操作步骤
        
        Args:
            step: 任务步骤，包含type、action、params等
        
        Returns:
            执行结果
        """
        step_type = step.get("type")
        action = step.get("action", "")
        params = step.get("params", {})
        
        logger.info(f"执行系统操作: {step_type} - {action}")
        
        try:
            if step_type == "screenshot_desktop":
                return self._screenshot_desktop(params)
            elif step_type == "open_folder":
                return self._open_folder(params)
            elif step_type == "open_file":
                return self._open_file(params)
            elif step_type == "open_app":
                return self._open_app(params)
            elif step_type == "close_app":
                return self._close_app(params)
            elif step_type == "execute_python_script":
                return self._execute_python_script(params)
            else:
                raise BrowserError(f"未知的系统操作类型: {step_type}")
                
        except Exception as e:
            logger.error(f"执行系统操作失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"操作失败: {e}",
                "data": None
            }
    
    def _screenshot_desktop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        桌面截图
        
        Args:
            params: 包含save_path（保存路径，可选）
                    - 可以是相对路径（相对于用户主目录）
                    - 可以是绝对路径（必须在用户主目录下）
                    - 支持 ~ 符号（如 ~/Desktop/screenshot.png）
        
        Returns:
            截图结果，包含保存路径
        """
        save_path_str = params.get("save_path")
        home = Path.home()
        
        # 如果没有指定路径，使用默认路径（沙盒目录下）
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
            
            # 安全：确保路径在用户主目录下（禁止操作系统关键路径）
            try:
                save_path.relative_to(home)
            except ValueError:
                # 不在用户主目录下，使用默认路径
                screenshots_dir = self.sandbox_path / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                import time
                save_path = screenshots_dir / f"desktop_{int(time.time())}.png"
                logger.warning(f"路径不在用户主目录下，使用默认路径: {save_path}")
        else:
            # 默认保存到沙盒目录的screenshots子目录
            screenshots_dir = self.sandbox_path / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            import time
            save_path = screenshots_dir / f"desktop_{int(time.time())}.png"
        
        # 确保目录存在
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存原始路径，用于查找实际保存的文件
        original_save_path = save_path
        
        # 根据操作系统选择截图方法
        platform = sys.platform
        
        try:
            if platform == "darwin":  # macOS
                # 使用 screencapture 命令
                # -x: 不播放快门声音
                # -T 0: 立即截图（无延迟）
                result = subprocess.run(
                    ["screencapture", "-x", str(save_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"截图失败: {result.stderr}")
                
                # macOS 的 screencapture 如果文件已存在，会自动添加序号（如 screenshot_1.png）
                # 需要检查实际保存的文件路径
                if not save_path.exists():
                    # 尝试查找带序号的文件
                    parent_dir = save_path.parent
                    stem = save_path.stem
                    suffix = save_path.suffix
                    counter = 1
                    found_path = None
                    # 最多尝试查找 100 个序号（防止无限循环）
                    while counter <= 100:
                        candidate_path = parent_dir / f"{stem}_{counter}{suffix}"
                        if candidate_path.exists():
                            found_path = candidate_path
                            logger.info(f"找到实际保存的截图文件（带序号）: {found_path}")
                            break
                        counter += 1
                    
                    if found_path:
                        save_path = found_path
                    else:
                        # 如果找不到带序号的文件，尝试查找任何匹配的文件
                        # 这可能是 screencapture 使用了其他命名规则
                        logger.warning(f"未找到预期的截图文件: {original_save_path}，尝试查找匹配的文件...")
                        # 列出目录中所有以相同 stem 开头的文件
                        matching_files = list(parent_dir.glob(f"{stem}*{suffix}"))
                        if matching_files:
                            # 按修改时间排序，取最新的
                            matching_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                            save_path = matching_files[0]
                            logger.info(f"找到匹配的截图文件: {save_path}")
                
            elif platform == "win32":  # Windows
                try:
                    # 尝试使用 mss 库（如果已安装）
                    import mss
                    with mss.mss() as sct:
                        # 截图整个屏幕
                        monitor = sct.monitors[1]  # 主显示器
                        sct_img = sct.grab(monitor)
                        mss.tools.to_png(sct_img.rgb, sct_img.size, output=str(save_path))
                except ImportError:
                    # 如果没有 mss，使用 pyautogui
                    try:
                        import pyautogui
                        screenshot = pyautogui.screenshot()
                        screenshot.save(str(save_path))
                    except ImportError:
                        raise BrowserError(
                            "Windows截图需要安装 mss 或 pyautogui 库。"
                            "运行: pip install mss 或 pip install pyautogui"
                        )
            
            elif platform.startswith("linux"):  # Linux
                try:
                    # 尝试使用 gnome-screenshot（GNOME）
                    result = subprocess.run(
                        ["gnome-screenshot", "-f", str(save_path)],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode != 0:
                        # 尝试使用 import（需要 X11）
                        try:
                            from PIL import ImageGrab
                            screenshot = ImageGrab.grab()
                            screenshot.save(str(save_path))
                        except ImportError:
                            raise BrowserError(
                                "Linux截图需要安装 gnome-screenshot 或 PIL。"
                                "运行: sudo apt-get install gnome-screenshot 或 pip install Pillow"
                            )
                except FileNotFoundError:
                    # 尝试使用 import
                    try:
                        from PIL import ImageGrab
                        screenshot = ImageGrab.grab()
                        screenshot.save(str(save_path))
                    except ImportError:
                        raise BrowserError(
                            "Linux截图需要安装 gnome-screenshot 或 PIL。"
                            "运行: sudo apt-get install gnome-screenshot 或 pip install Pillow"
                        )
            else:
                raise BrowserError(f"不支持的操作系统: {platform}")
            
            # 验证文件已创建
            if not save_path.exists():
                raise BrowserError(f"截图文件未创建: {save_path}")
            
            logger.info(f"✅ 桌面截图已保存: {save_path}")
            
            return {
                "success": True,
                "message": f"桌面截图已保存: {save_path}",
                "data": {"path": str(save_path)}
            }
            
        except subprocess.TimeoutExpired:
            raise BrowserError("截图超时（超过10秒）")
        except Exception as e:
            logger.error(f"截图失败: {e}", exc_info=True)
            raise BrowserError(f"截图失败: {e}")
    
    def _open_folder(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        在文件管理器中打开文件夹（支持智能搜索）
        
        Args:
            params: 包含folder_path（文件夹路径，必需）
                    - 可以是相对路径（相对于用户主目录）
                    - 可以是绝对路径（必须在用户主目录下）
                    - 支持 ~ 符号（如 ~/Desktop）
                    - 支持特殊路径（如 ~/Downloads, ~/Desktop, ~/Documents）
                    - 支持文件夹名（如 "8888"），会自动搜索
        
        Returns:
            打开结果
        """
        folder_path_str = params.get("folder_path")
        if not folder_path_str:
            raise BrowserError("缺少folder_path参数")
        
        home = Path.home()
        
        # 处理 ~ 符号
        if folder_path_str.startswith("~/"):
            folder_path_str = str(home / folder_path_str[2:])
        elif folder_path_str.startswith("~"):
            folder_path_str = str(home / folder_path_str[1:])
        
        folder_path = Path(folder_path_str)
        
        # 如果只是文件夹名（不包含路径分隔符），尝试智能搜索
        if "/" not in folder_path_str and "\\" not in folder_path_str and not folder_path_str.startswith("~"):
            logger.info(f"检测到文件夹名格式，开始智能搜索: {folder_path_str}")
            found_folder = self._find_folder(folder_path_str)
            if found_folder:
                folder_path = found_folder
                logger.info(f"找到文件夹: {folder_path}")
            else:
                raise BrowserError(
                    f"未找到文件夹: {folder_path_str}。"
                    f"请提供完整路径，如 '~/Desktop/{folder_path_str}' 或 '/Users/username/Desktop/{folder_path_str}'"
                )
        # 如果是相对路径，相对于用户主目录
        elif not folder_path.is_absolute():
            folder_path = home / folder_path
        
        folder_path = folder_path.resolve()
        
        # 安全：确保路径在用户主目录下
        try:
            folder_path.relative_to(home)
        except ValueError:
            raise BrowserError(
                f"文件夹路径不在允许的范围内: {folder_path}。"
                f"只允许打开用户主目录下的文件夹。"
            )
        
        # 检查文件夹是否存在
        if not folder_path.exists():
            raise BrowserError(f"文件夹不存在: {folder_path}")
        
        if not folder_path.is_dir():
            raise BrowserError(f"路径不是文件夹: {folder_path}")
        
        # 根据操作系统选择打开方法
        platform = sys.platform
        
        try:
            if platform == "darwin":  # macOS
                # 使用 open 命令打开文件夹
                result = subprocess.run(
                    ["open", str(folder_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件夹失败: {result.stderr}")
                
            elif platform == "win32":  # Windows
                # 使用 explorer 命令打开文件夹
                result = subprocess.run(
                    ["explorer", str(folder_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件夹失败: {result.stderr}")
                
            elif platform.startswith("linux"):  # Linux
                # 尝试使用 xdg-open（大多数 Linux 发行版）
                result = subprocess.run(
                    ["xdg-open", str(folder_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件夹失败: {result.stderr}")
            else:
                raise BrowserError(f"不支持的操作系统: {platform}")
            
            logger.info(f"✅ 已打开文件夹: {folder_path}")
            
            return {
                "success": True,
                "message": f"已打开文件夹: {folder_path}",
                "data": {"path": str(folder_path)}
            }
            
        except subprocess.TimeoutExpired:
            raise BrowserError("打开文件夹超时（超过10秒）")
        except Exception as e:
            logger.error(f"打开文件夹失败: {e}", exc_info=True)
            raise BrowserError(f"打开文件夹失败: {e}")
    
    def _open_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        使用默认应用程序打开文件（支持智能搜索）
        
        Args:
            params: 包含file_path（文件路径，必需）
                    - 可以是相对路径（相对于用户主目录）
                    - 可以是绝对路径（必须在用户主目录下）
                    - 支持 ~ 符号（如 ~/Desktop/file.pdf）
                    - 支持文件名（如 "强制执行申请书.pdf"），会自动搜索
        
        Returns:
            打开结果
        """
        file_path_str = params.get("file_path")
        if not file_path_str:
            raise BrowserError("缺少file_path参数")
        
        home = Path.home()
        
        # 处理 ~ 符号
        if file_path_str.startswith("~/"):
            file_path_str = str(home / file_path_str[2:])
        elif file_path_str.startswith("~"):
            file_path_str = str(home / file_path_str[1:])
        
        file_path = Path(file_path_str)
        
        # 如果只是文件名（不包含路径分隔符），尝试智能搜索
        if "/" not in file_path_str and "\\" not in file_path_str and not file_path_str.startswith("~"):
            logger.info(f"检测到文件名格式，开始智能搜索: {file_path_str}")
            # 使用 FileManager 的搜索方法
            from agent.executor.file_manager import FileManager
            file_manager = FileManager(self.config)
            found_file = file_manager._find_file(file_path_str)
            if found_file:
                file_path = found_file
                logger.info(f"找到文件: {file_path}")
            else:
                raise BrowserError(
                    f"未找到文件: {file_path_str}。"
                    f"请提供完整路径，如 '~/Desktop/{file_path_str}' 或 '/Users/username/Desktop/{file_path_str}'"
                )
        # 如果是相对路径，相对于用户主目录
        elif not file_path.is_absolute():
            file_path = home / file_path
        
        file_path = file_path.resolve()
        
        # 安全：确保路径在用户主目录下
        try:
            file_path.relative_to(home)
        except ValueError:
            raise BrowserError(
                f"文件路径不在允许的范围内: {file_path}。"
                f"只允许打开用户主目录下的文件。"
            )
        
        # 检查文件是否存在
        if not file_path.exists():
            raise BrowserError(f"文件不存在: {file_path}")
        
        if not file_path.is_file():
            raise BrowserError(f"路径不是文件: {file_path}")
        
        # 根据操作系统选择打开方法
        platform = sys.platform
        
        try:
            if platform == "darwin":  # macOS
                # 使用 open 命令打开文件（会自动使用默认应用程序）
                result = subprocess.run(
                    ["open", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件失败: {result.stderr}")
                
            elif platform == "win32":  # Windows
                # 使用 start 命令打开文件
                result = subprocess.run(
                    ["start", "", str(file_path)],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件失败: {result.stderr}")
                
            elif platform.startswith("linux"):  # Linux
                # 使用 xdg-open 打开文件
                result = subprocess.run(
                    ["xdg-open", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开文件失败: {result.stderr}")
            else:
                raise BrowserError(f"不支持的操作系统: {platform}")
            
            logger.info(f"✅ 已打开文件: {file_path}")
            
            return {
                "success": True,
                "message": f"已打开文件: {file_path}",
                "data": {"path": str(file_path)}
            }
            
        except subprocess.TimeoutExpired:
            raise BrowserError("打开文件超时（超过10秒）")
        except Exception as e:
            logger.error(f"打开文件失败: {e}", exc_info=True)
            raise BrowserError(f"打开文件失败: {e}")
    
    def _open_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        打开应用程序（支持后台运行）
        
        Args:
            params: 包含app_name（应用程序名称，必需）
                    - 可以是应用程序的完整名称（如 "汽水音乐"、"Spotify"）
                    - 可以是应用程序的bundle identifier（如 "com.spotify.client"）
                    - background: 是否在后台运行（可选，布尔值），如果为 true，应用程序会在后台运行，不显示窗口；如果为 false 或未指定，正常打开窗口
                    - **注意**：某些应用程序（如企业微信）可能需要窗口来操作，后台运行可能无法正常使用
        
        Returns:
            打开结果
        """
        app_name = params.get("app_name")
        background = params.get("background", False)
        if not app_name:
            raise BrowserError("缺少app_name参数")
        
        platform = sys.platform
        
        try:
            if platform == "darwin":  # macOS
                # 尝试多种方式打开应用程序
                app_variants = [
                    app_name,  # 原始名称
                    app_name + ".app",  # 带 .app 后缀
                ]
                
                # 尝试常见的应用程序名称映射
                app_mapping = {
                    "汽水音乐": ["汽水音乐", "汽水音乐.app"],
                    "spotify": ["Spotify", "Spotify.app"],
                    "chrome": ["Google Chrome", "Google Chrome.app"],
                    "safari": ["Safari", "Safari.app"],
                    "firefox": ["Firefox", "Firefox.app"],
                    "vscode": ["Visual Studio Code", "Visual Studio Code.app"],
                    "code": ["Visual Studio Code", "Visual Studio Code.app"],
                }
                
                if app_name.lower() in app_mapping:
                    app_variants.extend(app_mapping[app_name.lower()])
                
                # 尝试在 /Applications 目录下查找应用程序
                applications_dir = Path("/Applications")
                if applications_dir.exists():
                    for variant in app_variants:
                        app_path = applications_dir / variant
                        if app_path.exists() and app_path.is_dir():
                            logger.info(f"找到应用程序: {app_path}")
                            app_variants.insert(0, str(app_path))
                            break
                
                # 尝试打开应用程序
                opened = False
                last_error = None
                
                for variant in app_variants:
                    logger.info(f"尝试打开应用程序: {variant}（后台模式: {background}）")
                    # 如果需要在后台运行，使用 -g 选项（不激活应用程序窗口，在后台运行）
                    if background:
                        result = subprocess.run(
                            ["open", "-g", "-a", variant],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                    else:
                        result = subprocess.run(
                            ["open", "-a", variant],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                    
                    if result.returncode == 0:
                        # 验证应用程序是否真的打开了（检查进程）
                        import time
                        time.sleep(0.5)  # 等待应用程序启动
                        
                        # 检查进程是否在运行
                        check_result = subprocess.run(
                            ["pgrep", "-f", variant.replace(".app", "")],
                            capture_output=True,
                            text=True
                        )
                        
                        if check_result.returncode == 0 or variant in ["汽水音乐", "汽水音乐.app"]:
                            # 对于某些应用程序，pgrep 可能找不到，但如果 open 命令成功，通常表示已打开
                            opened = True
                            mode_str = "后台" if background else "前台"
                            logger.info(f"✅ 成功打开应用程序（{mode_str}模式）: {variant}")
                            break
                        else:
                            logger.warning(f"应用程序可能未成功启动: {variant}")
                            last_error = f"应用程序 {variant} 启动后未找到运行进程"
                    else:
                        last_error = result.stderr or f"打开 {variant} 失败"
                        logger.warning(f"尝试打开 {variant} 失败: {last_error}")
                
                if not opened:
                    raise BrowserError(
                        f"无法打开应用程序 '{app_name}'。"
                        f"已尝试: {', '.join(app_variants[:3])}。"
                        f"最后错误: {last_error}。"
                        f"请确认应用程序已安装且名称正确。"
                    )
                
            elif platform == "win32":  # Windows
                # Windows 使用 start 命令
                result = subprocess.run(
                    ["start", app_name],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开应用程序失败: {result.stderr}")
                
            elif platform.startswith("linux"):  # Linux
                # Linux 使用应用程序名称直接启动
                result = subprocess.run(
                    [app_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"打开应用程序失败: {result.stderr}")
            else:
                raise BrowserError(f"不支持的操作系统: {platform}")
            
            logger.info(f"✅ 已打开应用程序: {app_name}")
            
            return {
                "success": True,
                "message": f"已打开应用程序: {app_name}",
                "data": {"app_name": app_name}
            }
            
        except subprocess.TimeoutExpired:
            raise BrowserError("打开应用程序超时（超过10秒）")
        except Exception as e:
            logger.error(f"打开应用程序失败: {e}", exc_info=True)
            raise BrowserError(f"打开应用程序失败: {e}")
    
    def _close_app(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        关闭应用程序
        
        Args:
            params: 包含app_name（应用程序名称，必需）
                    - 可以是应用程序的完整名称（如 "汽水音乐"、"Spotify"）
                    - 可以是应用程序的bundle identifier（如 "com.spotify.client"）
        
        Returns:
            关闭结果
        """
        app_name = params.get("app_name")
        if not app_name:
            raise BrowserError("缺少app_name参数")
        
        platform = sys.platform
        
        try:
            if platform == "darwin":  # macOS
                # 尝试多种方式关闭应用程序
                app_variants = [
                    app_name,  # 原始名称
                    app_name.replace(".app", ""),  # 去除 .app 后缀
                ]
                
                # 尝试常见的应用程序名称映射
                app_mapping = {
                    "汽水音乐": ["汽水音乐", "汽水音乐.app"],
                    "spotify": ["Spotify"],
                    "chrome": ["Google Chrome"],
                    "safari": ["Safari"],
                    "firefox": ["Firefox"],
                    "vscode": ["Visual Studio Code"],
                    "code": ["Visual Studio Code"],
                }
                
                if app_name.lower() in app_mapping:
                    app_variants.extend(app_mapping[app_name.lower()])
                
                # 方法1：使用 osascript 优雅关闭（推荐）
                closed = False
                last_error = None
                
                for variant in app_variants:
                    try:
                        logger.info(f"尝试使用 osascript 关闭应用程序: {variant}")
                        result = subprocess.run(
                            ["osascript", "-e", f'tell application "{variant}" to quit'],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        
                        if result.returncode == 0:
                            # 等待应用程序关闭
                            import time
                            time.sleep(0.5)
                            
                            # 验证应用程序是否真的关闭了
                            check_result = subprocess.run(
                                ["pgrep", "-f", variant.replace(".app", "")],
                                capture_output=True,
                                text=True
                            )
                            
                            if check_result.returncode != 0:
                                # 进程不存在，说明已关闭
                                closed = True
                                logger.info(f"✅ 成功关闭应用程序: {variant}")
                                break
                            else:
                                logger.warning(f"应用程序可能未完全关闭: {variant}")
                    except Exception as e:
                        logger.warning(f"osascript 关闭失败: {variant}, 错误: {e}")
                        last_error = str(e)
                
                # 方法2：如果 osascript 失败，使用 killall 强制关闭
                if not closed:
                    logger.info("osascript 关闭失败，尝试使用 killall 强制关闭")
                    for variant in app_variants:
                        process_name = variant.replace(".app", "")
                        try:
                            result = subprocess.run(
                                ["killall", process_name],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            
                            if result.returncode == 0:
                                closed = True
                                logger.info(f"✅ 成功强制关闭应用程序: {process_name}")
                                break
                            elif "No matching processes" not in result.stderr:
                                last_error = result.stderr
                        except Exception as e:
                            logger.warning(f"killall 关闭失败: {process_name}, 错误: {e}")
                            last_error = str(e)
                
                if not closed:
                    raise BrowserError(
                        f"无法关闭应用程序 '{app_name}'。"
                        f"已尝试: {', '.join(app_variants[:3])}。"
                        f"最后错误: {last_error or '应用程序可能未运行'}。"
                    )
                
            elif platform == "win32":  # Windows
                # Windows 使用 taskkill 命令
                result = subprocess.run(
                    ["taskkill", "/IM", app_name, "/F"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0 and "not found" not in result.stderr.lower():
                    raise BrowserError(f"关闭应用程序失败: {result.stderr}")
                
            elif platform.startswith("linux"):  # Linux
                # Linux 使用 killall 命令
                result = subprocess.run(
                    ["killall", app_name],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode != 0:
                    raise BrowserError(f"关闭应用程序失败: {result.stderr}")
            else:
                raise BrowserError(f"不支持的操作系统: {platform}")
            
            logger.info(f"✅ 已关闭应用程序: {app_name}")
            
            return {
                "success": True,
                "message": f"已关闭应用程序: {app_name}",
                "data": {"app_name": app_name}
            }
            
        except subprocess.TimeoutExpired:
            raise BrowserError("关闭应用程序超时（超过10秒）")
        except Exception as e:
            logger.error(f"关闭应用程序失败: {e}", exc_info=True)
            raise BrowserError(f"关闭应用程序失败: {e}")
    
    def _execute_python_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Python脚本
        
        Args:
            params: 包含script（Python脚本代码，必需）、reason（原因，可选）、safety（安全检查说明，可选）
        
        Returns:
            执行结果，包含success、message、data等
        """
        script = params.get("script")
        if not script:
            raise BrowserError("缺少script参数")
        
        if not isinstance(script, str) or not script.strip():
            raise BrowserError("script参数必须是非空字符串")
        
        reason = params.get("reason", "未提供原因")
        safety = params.get("safety", "未提供安全检查说明")
        
        logger.info(f"执行Python脚本，原因: {reason}")
        logger.debug(f"安全检查说明: {safety}")
        logger.debug(f"脚本内容（前500字符）:\n{script[:500]}")
        
        try:
            # 创建临时脚本文件
            import tempfile
            import os
            
            # 在沙盒目录中创建临时脚本文件
            temp_script_dir = self.sandbox_path / "scripts"
            temp_script_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建临时脚本文件
            import time
            temp_script_path = temp_script_dir / f"script_{int(time.time())}.py"
            
            # 处理脚本内容：可能是 base64 编码，也可能是普通字符串
            import base64
            script_content = None
            
            # 首先尝试 base64 解码
            try:
                # 修复可能的 padding 问题
                # 移除所有空白字符（包括换行符、空格等），因为 base64 字符串不应该包含这些
                script_clean = ''.join(script.split())
                script_to_decode = script_clean.strip()
                
                # 修复 padding：如果长度不能被 4 整除，可能是字符串被截断了
                original_len = len(script_to_decode)
                missing_padding = original_len % 4
                
                if missing_padding:
                    # 先尝试添加 padding
                    script_to_decode_padded = script_to_decode + '=' * (4 - missing_padding)
                    logger.debug(f"修复 base64 padding，添加了 {4 - missing_padding} 个 =")
                else:
                    script_to_decode_padded = script_to_decode
                
                # 先尝试严格模式
                decoded_bytes = None
                try:
                    decoded_bytes = base64.b64decode(script_to_decode_padded, validate=True)
                    logger.debug("base64 严格模式解码成功")
                except Exception as strict_error:
                    # 严格模式失败，尝试宽松模式
                    logger.warning(f"base64 严格验证失败（{strict_error}），尝试宽松模式")
                    try:
                        decoded_bytes = base64.b64decode(script_to_decode_padded, validate=False)
                        logger.debug("base64 宽松模式解码成功")
                    except Exception as loose_error:
                        # 如果添加 padding 后仍然失败，尝试移除最后几个字符（可能是截断的）
                        if missing_padding:
                            logger.warning(f"添加 padding 后仍然失败，尝试移除最后 {missing_padding} 个字符（可能是截断的）")
                            try:
                                script_truncated = script_to_decode[:-missing_padding]
                                missing_truncated = len(script_truncated) % 4
                                if missing_truncated:
                                    script_truncated += '=' * (4 - missing_truncated)
                                decoded_bytes = base64.b64decode(script_truncated, validate=False)
                                logger.info("✅ 通过移除截断字符成功解码 base64")
                            except Exception as truncate_error:
                                # 所有尝试都失败，抛出异常让外层处理
                                raise ValueError(f"base64 解码失败（严格模式: {strict_error}, 宽松模式: {loose_error}, 截断修复: {truncate_error}）")
                        else:
                            raise ValueError(f"base64 解码失败（严格模式: {strict_error}, 宽松模式: {loose_error}）")
                
                # 尝试 UTF-8 解码
                try:
                    script_content = decoded_bytes.decode("utf-8")
                    logger.info("✅ 检测到 base64 编码的脚本，已成功解码")
                except UnicodeDecodeError as utf8_error:
                    # UTF-8 解码失败，尝试错误替换模式
                    script_content = decoded_bytes.decode("utf-8", errors="replace")
                    logger.warning(f"base64 解码成功，但 UTF-8 解码有错误（{utf8_error}），使用错误替换模式")
                
                # 立即清理控制字符（U+0000 到 U+001F，除了已允许的换行、制表符、回车）
                import string
                allowed_control_chars = {'\n', '\r', '\t'}  # 允许的控制字符
                cleaned_chars = []
                removed_count = 0
                for char in script_content:
                    char_code = ord(char)
                    # 保留可打印字符、空格、以及允许的控制字符
                    if char in string.printable or char in allowed_control_chars:
                        cleaned_chars.append(char)
                    elif char_code < 32:  # 控制字符（U+0000 到 U+001F）
                        # 完全移除控制字符（U+0019 等），不替换为空格
                        removed_count += 1
                        logger.debug(f"移除控制字符: U+{char_code:04X}")
                    else:
                        # 其他字符（如中文、emoji等）保留
                        cleaned_chars.append(char)
                
                if removed_count > 0:
                    logger.warning(f"已移除 {removed_count} 个控制字符（U+0000 到 U+001F）")
                    script_content = ''.join(cleaned_chars)
            except Exception as decode_error:
                # base64 解码失败，说明是普通字符串
                logger.info(f"不是 base64 编码（{decode_error}），使用普通字符串格式")
                script_content = script.replace("\\n", "\n")  # 将 \\n 转换为实际的换行符
                
                # 也清理普通字符串中的控制字符
                import string
                allowed_control_chars = {'\n', '\r', '\t'}
                cleaned_chars = []
                removed_count = 0
                for char in script_content:
                    char_code = ord(char)
                    if char in string.printable or char in allowed_control_chars:
                        cleaned_chars.append(char)
                    elif char_code < 32:
                        removed_count += 1
                    else:
                        cleaned_chars.append(char)
                
                if removed_count > 0:
                    logger.warning(f"已移除 {removed_count} 个控制字符")
                    script_content = ''.join(cleaned_chars)
            
            # 确保 script_content 不为空
            if not script_content:
                logger.error("脚本内容为空，使用原始内容")
                script_content = script
            
            # 验证解码后的内容看起来像 Python 代码
            if script_content and not script_content.strip().startswith(('import ', 'from ', 'def ', 'class ', 'try:', 'if ', 'print(', '#')):
                # 如果解码后的内容不像 Python 代码，可能是解码失败，尝试作为普通字符串处理
                logger.warning("解码后的内容不像 Python 代码，尝试作为普通字符串处理")
                script_content = script.replace("\\n", "\n")
            
            # 自动修复脚本中的常见问题
            if script_content:
                import urllib.parse
                import re
                
                # 1. 修复 f-string 语法错误（f'""" 应该是 f"""）
                # 查找 f'""" 或 f'""" 等错误的 f-string 语法
                # 匹配 f'""" 或 f'""" 等模式
                fstring_fix_pattern = r"f['\"]\"\"\""
                def fix_fstring_quote(match):
                    logger.warning("检测到错误的 f-string 语法（单引号+三引号混用），已修复为 f\"\"\"")
                    return 'f"""'
                
                # 也修复 f'""" 的情况（单引号开头，三引号结尾）
                fstring_fix_pattern2 = r"f'\"\"\""
                fixed_content = re.sub(fstring_fix_pattern2, 'f"""', script_content)
                if fixed_content != script_content:
                    script_content = fixed_content
                    logger.info("已修复 f-string 语法错误（f'\"\"\" -> f\"\"\"）")
                
                fixed_content = re.sub(fstring_fix_pattern, fix_fstring_quote, script_content)
                if fixed_content != script_content:
                    script_content = fixed_content
                    logger.info("已修复 f-string 语法错误")
                
                # 2. 修复未闭合的 f-string（检测 f"""... 但未闭合的情况）
                # 查找 f""" 开头但未正确闭合的字符串
                unterminated_fstring_pattern = r"(f\"\"\"[^\"]{200,}?)([^\"])"
                def fix_unterminated_fstring(match):
                    content = match.group(1)  # f"""... 部分
                    next_char = match.group(2)  # 下一个字符
                    
                    # 如果下一个字符不是引号，说明 f-string 未闭合
                    if next_char not in ['"', '\n', ' ']:
                        # 截断到合理长度并添加闭合引号
                        truncated = content[:500] if len(content) > 500 else content
                        # 尝试找到合理的结束点
                        for i in range(len(truncated) - 1, len(truncated) - 100, -1):
                            if i > 0 and truncated[i-1] in '。，！？\n':
                                truncated = truncated[:i]
                                break
                        fixed_fstring = truncated + '"""'
                        logger.warning(f"检测到未闭合的 f-string，已自动修复（截断到 {len(fixed_fstring)} 字符）")
                        return fixed_fstring + next_char
                    return match.group(0)
                
                fixed_content = re.sub(unterminated_fstring_pattern, fix_unterminated_fstring, script_content, flags=re.DOTALL)
                if fixed_content != script_content:
                    script_content = fixed_content
                    logger.info("已尝试修复未闭合的 f-string")
                
                # 3. 修复未闭合的 message 字符串（检测超长的字符串，可能是字符串未闭合）
                # 查找 print(json.dumps({"success": False, "message": "超长文本" 的模式
                # 如果 message 字段的值超过200字符且没有闭合引号，截断并添加闭合引号
                message_pattern = r'("message"\s*:\s*")([^"]{0,200})([^"]{200,}?)([",}])'
                def fix_unterminated_message(match):
                    prefix = match.group(1)  # "message": "
                    normal_part = match.group(2)  # 前面的正常部分（最多200字符）
                    long_part = match.group(3)  # 超长部分
                    next_char = match.group(4)  # 下一个字符（" 或 , 或 }）
                    
                    # 如果下一个字符不是引号，说明字符串未闭合
                    if next_char != '"':
                        # 截断超长部分到合理长度（100字符）
                        truncated = long_part[:100] if len(long_part) > 100 else long_part
                        # 尝试找到合理的结束点
                        for i in range(len(truncated), 0, -1):
                            if truncated[i-1] in '。，！？':
                                truncated = truncated[:i]
                                break
                        fixed_message = normal_part + truncated + '"'
                        logger.warning(f"检测到未闭合的 message 字符串（长度 {len(normal_part) + len(long_part)}），已自动修复（截断到 {len(fixed_message)-1} 字符）")
                        return prefix + fixed_message + next_char
                    return match.group(0)  # 如果已经有闭合引号，保持原样
                
                # 尝试修复未闭合的 message 字符串
                fixed_content = re.sub(message_pattern, fix_unterminated_message, script_content)
                if fixed_content != script_content:
                    script_content = fixed_content
                    logger.info("已尝试修复未闭合的 message 字符串")
                
                # 2. 修复 URL 编码的文件路径（如果存在）
                url_encoded_pattern = r'(["\'])([^"\']*%[0-9A-Fa-f]{2}[^"\']*)(["\'])'
                def fix_url_encoded_path(match):
                    quote_char = match.group(1)
                    path = match.group(2)
                    # 尝试解码 URL 编码的路径
                    try:
                        decoded_path = urllib.parse.unquote(path)
                        if decoded_path != path:
                            logger.info(f"检测到 URL 编码的文件路径，已自动修复: {path} -> {decoded_path}")
                            return f'{quote_char}{decoded_path}{quote_char}'
                    except Exception:
                        pass
                    return match.group(0)  # 如果解码失败，保持原样
                
                # 替换所有 URL 编码的文件路径
                fixed_content = re.sub(url_encoded_pattern, fix_url_encoded_path, script_content)
                if fixed_content != script_content:
                    script_content = fixed_content
                    logger.info("已自动修复脚本中的 URL 编码文件路径")
                
                # 3. 验证并修复基本的字符串闭合问题（简单但有效的方法）
                # 统计引号数量，如果不匹配，尝试修复
                single_quotes = script_content.count("'") - script_content.count("\\'")
                double_quotes = script_content.count('"') - script_content.count('\\"')
                
                # 如果双引号数量是奇数，可能缺少闭合引号
                if double_quotes % 2 == 1:
                    # 尝试在最后一个 print(json.dumps(...)) 语句后添加闭合引号
                    # 查找最后一个未闭合的字符串
                    last_print_match = list(re.finditer(r'print\s*\(\s*json\.dumps\s*\([^)]*\)', script_content))
                    if last_print_match:
                        last_match = last_print_match[-1]
                        # 检查匹配后的内容是否有未闭合的引号
                        after_match = script_content[last_match.end():]
                        if after_match.strip().startswith(')'):
                            # 如果后面直接是右括号，说明字符串已经闭合
                            pass
                        else:
                            # 尝试在合理的位置添加闭合引号
                            # 查找下一个结构字符（逗号、右括号、右大括号）
                            next_struct = re.search(r'[,)}\]]', after_match)
                            if next_struct:
                                insert_pos = last_match.end() + next_struct.start()
                                script_content = script_content[:insert_pos] + '"' + script_content[insert_pos:]
                                logger.warning("检测到未闭合的字符串，已自动添加闭合引号")
            
            with open(temp_script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            logger.info(f"临时脚本已创建: {temp_script_path}")
            
            # 执行脚本
            result = subprocess.run(
                [sys.executable, str(temp_script_path)],
                capture_output=True,
                text=True,
                timeout=300,  # 5分钟超时
                cwd=str(self.sandbox_path)  # 在沙盒目录中执行
            )
            
            # 解析输出（期望是JSON格式）
            stdout = result.stdout.strip()
            stderr = result.stderr.strip()
            
            if result.returncode != 0:
                logger.error(f"脚本执行失败，返回码: {result.returncode}")
                logger.error(f"stderr: {stderr}")
                logger.error(f"stdout: {stdout}")
                
                # 尝试从stdout解析JSON错误信息
                try:
                    import json
                    error_result = json.loads(stdout)
                    if error_result.get("success") == False:
                        error_message = error_result.get("message", "脚本执行失败")
                        # 如果错误消息是乱码或没有意义，使用更通用的消息
                        if (not error_message or 
                            len(error_message.strip()) < 3 or 
                            "文件后的文本" in error_message or
                            "名称文中结束的空错" in error_message or
                            "大取同学名称" in error_message or  # 检测错误的文件名
                            "连排" in error_message or  # 检测错误的输出文件名
                            "求正放接探底作品" in error_message or  # 检测错误的文件名
                            "输克" in error_message or  # 检测错误的输出文件名
                            "文章不能为空" in error_message or  # 文件不存在时的错误消息（不准确）
                            "文章输光" in error_message or  # 乱码
                            "文章保存不能" in error_message or  # 乱码
                            error_message.count("，") > 10 or  # 包含大量逗号可能是乱码
                            not any(c.isalnum() or c in "，。！？：；" for c in error_message[:50])  # 前50个字符中没有正常字符
                        ):
                            # 根据stderr判断具体错误类型
                            if stderr and ("FileNotFoundError" in stderr or "文件不存在" in stderr or "No such file" in stderr):
                                error_message = "脚本执行失败：文件不存在或文件路径错误"
                            elif stderr and ("PermissionError" in stderr or "权限" in stderr):
                                error_message = "脚本执行失败：文件权限不足"
                            else:
                                error_message = "脚本执行失败：文件路径错误或文件不存在"
                        return {
                            "success": False,
                            "message": error_message,
                            "data": error_result.get("data"),
                            "error": error_result.get("error", stderr)
                        }
                except:
                    pass
                
                # 构建详细的错误信息
                error_msg = f"脚本执行失败（返回码: {result.returncode}）"
                if stderr:
                    error_msg += f"\n错误输出: {stderr[:500]}"  # 限制长度，避免过长
                if stdout and not stderr:
                    error_msg += f"\n输出: {stdout[:500]}"
                
                return {
                    "success": False,
                    "message": error_msg,
                    "data": None,
                    "error": stderr or stdout or "未知错误"
                }
            
            # 尝试解析JSON输出
            try:
                import json
                script_result = json.loads(stdout)
                
                # 验证结果格式
                if not isinstance(script_result, dict):
                    raise ValueError("脚本输出不是JSON对象")
                
                return {
                    "success": script_result.get("success", True),
                    "message": script_result.get("message", "脚本执行完成"),
                    "data": script_result.get("data"),
                    "error": script_result.get("error")
                }
            except json.JSONDecodeError as e:
                # 如果输出不是JSON，返回原始输出
                logger.warning(f"脚本输出不是有效的JSON: {e}")
                logger.debug(f"原始输出: {stdout}")
                
                return {
                    "success": True,
                    "message": "脚本执行完成（输出不是JSON格式）",
                    "data": {"output": stdout, "stderr": stderr}
                }
            
        except subprocess.TimeoutExpired:
            logger.error("脚本执行超时（超过5分钟）")
            return {
                "success": False,
                "message": "脚本执行超时（超过5分钟）",
                "data": None,
                "error": "超时"
            }
        except Exception as e:
            logger.error(f"执行脚本失败: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"执行脚本失败: {e}",
                "data": None,
                "error": str(e)
            }
        finally:
            # 清理临时脚本文件（可选，保留用于调试）
            # if temp_script_path.exists():
            #     temp_script_path.unlink()
            pass