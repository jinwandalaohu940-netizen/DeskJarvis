"""
异常模块：定义项目自定义异常类

遵循 docs/DEVELOPMENT.md 中的错误处理规范
"""


class DeskJarvisError(Exception):
    """
    基础异常类：所有项目异常的基类
    
    Attributes:
        message: 错误消息
        details: 错误详情（可选）
    """
    
    def __init__(self, message: str, details: str | None = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            details: 错误详情，可选
        """
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """返回异常字符串表示"""
        if self.details:
            return f"{self.message} | 详情: {self.details}"
        return self.message


class BrowserError(DeskJarvisError):
    """浏览器操作错误"""
    pass


class FileManagerError(DeskJarvisError):
    """文件管理错误"""
    pass


class PlannerError(DeskJarvisError):
    """AI规划错误"""
    pass


class ConfigError(DeskJarvisError):
    """配置错误"""
    pass
