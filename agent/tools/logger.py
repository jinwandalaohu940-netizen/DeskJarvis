"""
日志配置模块：配置项目日志系统

遵循 docs/ARCHITECTURE.md 和 docs/DEVELOPMENT.md 中的日志规范
"""

import logging
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class JSONFormatter(logging.Formatter):
    """
    JSON格式日志格式化器
    
    日志格式：JSON格式，包含时间戳、级别、模块、消息等
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为JSON
        
        Args:
            record: 日志记录
        
        Returns:
            JSON格式的日志字符串
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }
        
        # 添加异常信息（如果有）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # 添加额外字段（如果有）
        if hasattr(record, "extra_data"):
            log_data["extra"] = record.extra_data
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(
    log_level: str = "INFO",
    log_dir: Path | None = None,
    log_to_file: bool = True,
    log_to_console: bool = True
) -> None:
    """
    配置项目日志系统
    
    Args:
        log_level: 日志级别（DEBUG/INFO/WARNING/ERROR）
        log_dir: 日志目录，如果为None则使用默认目录
        log_to_file: 是否输出到文件
        log_to_console: 是否输出到控制台
    """
    # 确定日志目录
    if log_dir is None:
        log_dir = Path.home() / ".deskjarvis" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # 清除现有处理器
    root_logger.handlers.clear()
    
    # 控制台处理器（简单格式）
    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        root_logger.addHandler(console_handler)
    
    # 文件处理器（JSON格式）
    if log_to_file:
        log_file = log_dir / f"deskjarvis_{datetime.now().strftime('%Y%m%d')}.jsonl"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)
    
    logging.info(f"日志系统已配置: 级别={log_level}, 目录={log_dir}")
