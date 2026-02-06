"""
配置模块单元测试
"""

import pytest
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.tools.config import Config
from agent.tools.exceptions import ConfigError


class TestConfigModels:
    """配置模型映射测试"""
    
    def test_claude_models(self):
        """测试 Claude 模型"""
        assert "claude" in Config.DEFAULT_MODELS
        assert Config.DEFAULT_MODELS["claude"] == "claude-3-5-sonnet-20241022"
    
    def test_deepseek_models(self):
        """测试 DeepSeek 模型"""
        assert "deepseek" in Config.DEFAULT_MODELS
        assert Config.DEFAULT_MODELS["deepseek"] == "deepseek-chat"
    
    def test_openai_models(self):
        """测试 OpenAI 模型"""
        assert "openai" in Config.DEFAULT_MODELS
    
    def test_grok_models(self):
        """测试 Grok 模型"""
        assert "grok" in Config.DEFAULT_MODELS


class TestDefaultConfig:
    """默认配置测试"""
    
    def test_default_config_exists(self):
        """测试默认配置存在"""
        assert hasattr(Config, 'DEFAULT_CONFIG')
        assert "provider" in Config.DEFAULT_CONFIG
        assert "model" in Config.DEFAULT_CONFIG
    
    def test_all_providers_have_models(self):
        """测试所有提供商都有模型"""
        providers = ["claude", "openai", "deepseek", "grok"]
        for provider in providers:
            assert provider in Config.DEFAULT_MODELS, f"Provider {provider} not found"
    
    def test_default_provider(self):
        """测试默认提供商"""
        assert Config.DEFAULT_CONFIG["provider"] in Config.DEFAULT_MODELS


class TestConfigIOAndProperties:
    """Config 读写与属性行为测试（提高覆盖率，防止回归）"""

    def test_creates_default_config_when_missing(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        assert not cfg_path.exists()
        cfg = Config(config_path=str(cfg_path))
        assert cfg_path.exists()
        assert cfg.provider in Config.DEFAULT_MODELS
        assert isinstance(cfg.sandbox_path, Path)

    def test_validate_requires_api_key(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        cfg.set("api_key", "")
        cfg.save()
        assert cfg.validate() is False
        cfg.set("api_key", "test-key")
        cfg.save()
        assert cfg.validate() is True

    def test_model_fallback_by_provider(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        cfg.set("provider", "deepseek")
        cfg.set("model", "")  # 触发 fallback
        cfg.save()
        # 重新加载验证 fallback 生效
        cfg2 = Config(config_path=str(cfg_path))
        assert cfg2.provider == "deepseek"
        assert cfg2.model == Config.DEFAULT_MODELS["deepseek"]

    def test_auto_confirm_and_log_level_defaults(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        assert cfg.auto_confirm is False
        assert cfg.log_level == "INFO"
        cfg.set("auto_confirm", True)
        cfg.set("log_level", "DEBUG")
        cfg.save()
        cfg2 = Config(config_path=str(cfg_path))
        assert cfg2.auto_confirm is True
        assert cfg2.log_level == "DEBUG"

    def test_invalid_json_raises_config_error(self, tmp_path: Path):
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(ConfigError):
            Config(config_path=str(cfg_path))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
