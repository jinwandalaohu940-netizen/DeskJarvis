"""
Browser State Manager

负责管理浏览器会话状态，包括：
- Cookie 持久化（按域名存储）
- 登录状态检测
- 会话恢复

存储路径: ~/.deskjarvis/browser_state/{domain}/
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class BrowserStateManager:
    """浏览器状态管理器"""
    
    def __init__(self, state_dir: Optional[Path] = None):
        """
        初始化浏览器状态管理器
        
        Args:
            state_dir: 状态存储目录，默认为 ~/.deskjarvis/browser_state
        """
        if state_dir is None:
            state_dir = Path.home() / ".deskjarvis" / "browser_state"
        
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"浏览器状态管理器已初始化，存储目录: {self.state_dir}")
    
    def _get_domain_from_url(self, url: str) -> str:
        """
        从 URL 中提取域名
        
        Args:
            url: 完整 URL 或域名
            
        Returns:
            规范化的域名
        """
        # 如果不包含协议，添加一个临时的
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # 移除端口号
        if ":" in domain:
            domain = domain.split(":")[0]
        
        return domain
    
    def _get_domain_dir(self, domain: str) -> Path:
        """
        获取域名的状态存储目录
        
        Args:
            domain: 域名
            
        Returns:
            域名目录路径
        """
        # 清理域名（移除非法文件名字符）
        safe_domain = domain.replace("/", "_").replace(":", "_")
        domain_dir = self.state_dir / safe_domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        return domain_dir
    
    def save_cookies(self, url: str, cookies: List[Dict[str, Any]]) -> None:
        """
        保存 cookies 到文件
        
        Args:
            url: 网站 URL
            cookies: Playwright cookies 列表
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            cookies_file = domain_dir / "cookies.json"
            
            # 保存 cookies
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            
            # 设置文件权限为仅用户可读写（安全考虑）
            cookies_file.chmod(0o600)
            
            logger.info(f"已保存 {len(cookies)} 个 cookies 到 {cookies_file}")
            
        except Exception as e:
            logger.error(f"保存 cookies 失败: {e}", exc_info=True)
    
    def load_cookies(self, url: str) -> Optional[List[Dict[str, Any]]]:
        """
        从文件加载 cookies
        
        Args:
            url: 网站 URL
            
        Returns:
            Playwright cookies 列表，如果不存在则返回 None
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            cookies_file = domain_dir / "cookies.json"
            
            if not cookies_file.exists():
                logger.debug(f"未找到 {domain} 的 cookies 文件")
                return None
            
            with open(cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            logger.info(f"已加载 {len(cookies)} 个 cookies from {cookies_file}")
            return cookies
            
        except Exception as e:
            logger.error(f"加载 cookies 失败: {e}", exc_info=True)
            return None
    
    def has_saved_state(self, url: str) -> bool:
        """
        检查是否存在保存的状态
        
        Args:
            url: 网站 URL
            
        Returns:
            True 如果存在保存的 cookies
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            cookies_file = domain_dir / "cookies.json"
            return cookies_file.exists()
        except Exception as e:
            logger.error(f"检查状态失败: {e}")
            return False
    
    def clear_state(self, url: str) -> None:
        """
        清除指定域名的状态
        
        Args:
            url: 网站 URL
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            cookies_file = domain_dir / "cookies.json"
            
            if cookies_file.exists():
                cookies_file.unlink()
                logger.info(f"已清除 {domain} 的状态")
            
        except Exception as e:
            logger.error(f"清除状态失败: {e}", exc_info=True)
    
    def save_metadata(self, url: str, metadata: Dict[str, Any]) -> None:
        """
        保存额外的元数据（如登录时间、用户名等）
        
        Args:
            url: 网站 URL
            metadata: 元数据字典
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            metadata_file = domain_dir / "metadata.json"
            
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            metadata_file.chmod(0o600)
            logger.info(f"已保存元数据到 {metadata_file}")
            
        except Exception as e:
            logger.error(f"保存元数据失败: {e}", exc_info=True)
    
    def load_metadata(self, url: str) -> Optional[Dict[str, Any]]:
        """
        加载元数据
        
        Args:
            url: 网站 URL
            
        Returns:
            元数据字典，如果不存在则返回 None
        """
        try:
            domain = self._get_domain_from_url(url)
            domain_dir = self._get_domain_dir(domain)
            metadata_file = domain_dir / "metadata.json"
            
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"加载元数据失败: {e}", exc_info=True)
            return None
