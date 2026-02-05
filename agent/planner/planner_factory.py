"""
规划器工厂：根据配置创建对应的AI规划器

遵循 docs/ARCHITECTURE.md 中的Planner模块规范
"""

from typing import Optional
import logging
from agent.tools.config import Config
from agent.tools.exceptions import PlannerError
from agent.planner.base_planner import BasePlanner

logger = logging.getLogger(__name__)


def create_planner(config: Config) -> BasePlanner:
    """
    根据配置创建对应的规划器
    
    Args:
        config: 配置对象
    
    Returns:
        规划器实例
    
    Raises:
        PlannerError: 当provider不支持或初始化失败时
    """
    provider = config.get("provider", "claude").lower()
    
    try:
        if provider == "claude":
            from agent.planner.claude_planner import ClaudePlanner
            return ClaudePlanner(config)
        
        elif provider == "openai" or provider == "chatgpt":
            from agent.planner.openai_planner import OpenAIPlanner
            return OpenAIPlanner(config)
        
        elif provider == "deepseek":
            from agent.planner.deepseek_planner import DeepSeekPlanner
            return DeepSeekPlanner(config)
        
        elif provider == "grok":
            # Grok暂时使用OpenAI兼容接口（如果X提供）
            # 或者可以单独实现
            from agent.planner.openai_planner import OpenAIPlanner
            # 注意：需要设置base_url为Grok的API地址
            logger.warning("Grok规划器使用OpenAI兼容接口，请确保配置正确的base_url")
            return OpenAIPlanner(config)
        
        else:
            raise PlannerError(f"不支持的AI提供商: {provider}。支持: claude, openai, deepseek, grok")
    
    except ImportError as e:
        raise PlannerError(f"导入规划器模块失败: {e}。请确保已安装相应的依赖包")
    except Exception as e:
        raise PlannerError(f"创建规划器失败: {e}")
