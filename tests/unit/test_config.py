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

    def test_reload_config(self, tmp_path: Path):
        """测试重新加载配置"""
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        cfg.set("provider", "claude")
        cfg.save()
        
        # 修改文件
        cfg.set("provider", "deepseek")
        cfg.reload()  # 应该重新加载，恢复为 claude
        assert cfg.provider == "claude"

    def test_save_failure_raises_error(self, tmp_path: Path):
        """测试保存失败时抛出异常"""
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        
        # 创建一个只读目录来模拟保存失败
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)  # 只读
        
        cfg.config_path = readonly_dir / "config.json"
        with pytest.raises(ConfigError):
            cfg.save()
        
        readonly_dir.chmod(0o755)  # 恢复权限以便清理

    def test_load_failure_raises_error(self, tmp_path: Path):
        """测试加载失败时抛出异常"""
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text('{"provider": "claude"}', encoding="utf-8")
        
        # 创建一个不可读的文件来模拟加载失败
        import os
        cfg_path.chmod(0o000)
        
        try:
            with pytest.raises(ConfigError):
                Config(config_path=str(cfg_path))
        finally:
            cfg_path.chmod(0o644)  # 恢复权限

    def test_default_config_path_creation(self, tmp_path, monkeypatch):
        """测试默认配置路径创建"""
        # 模拟 home 目录
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)
        
        cfg = Config()  # 使用默认路径
        config_path = fake_home / ".deskjarvis" / "config.json"
        assert config_path.exists()

    def test_email_properties(self, tmp_path: Path):
        """测试邮件相关属性"""
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        
        # 测试默认值
        assert cfg.email_sender is None
        assert cfg.email_password is None
        assert cfg.email_smtp_server == "smtp.gmail.com"
        assert cfg.email_smtp_port == 587
        assert cfg.email_imap_port == 993
        
        # 测试设置值
        cfg.set("email_sender", "test@example.com")
        cfg.set("email_password", "password123")
        cfg.set("email_smtp_server", "smtp.qq.com")
        cfg.set("email_smtp_port", "465")
        cfg.set("email_imap_port", "143")
        cfg.save()
        
        cfg2 = Config(config_path=str(cfg_path))
        assert cfg2.email_sender == "test@example.com"
        assert cfg2.email_password == "password123"
        assert cfg2.email_smtp_server == "smtp.qq.com"
        assert cfg2.email_smtp_port == 465
        assert cfg2.email_imap_port == 143

    def test_email_imap_server_inference(self, tmp_path: Path):
        """测试 IMAP 服务器自动推断"""
        cfg_path = tmp_path / "config.json"
        cfg = Config(config_path=str(cfg_path))
        
        # 测试 Gmail
        cfg.set("email_smtp_server", "smtp.gmail.com")
        cfg.save()
        cfg2 = Config(config_path=str(cfg_path))
        assert cfg2.email_imap_server == "imap.gmail.com"
        
        # 测试 QQ
        cfg.set("email_smtp_server", "smtp.qq.com")
        cfg.save()
        cfg3 = Config(config_path=str(cfg_path))
        assert cfg3.email_imap_server == "imap.qq.com"
        
        # 测试 Outlook
        cfg.set("email_smtp_server", "smtp.outlook.com")
        cfg.save()
        cfg4 = Config(config_path=str(cfg_path))
        assert cfg4.email_imap_server == "outlook.office365.com"
        
        # 测试自定义 SMTP（带 smtp. 前缀）
        cfg.set("email_smtp_server", "smtp.custom.com")
        cfg.save()
        cfg5 = Config(config_path=str(cfg_path))
        assert cfg5.email_imap_server == "imap.custom.com"
        
        # 测试显式设置 IMAP
        cfg.set("email_imap_server", "imap.custom.com")
        cfg.save()
        cfg6 = Config(config_path=str(cfg_path))
        assert cfg6.email_imap_server == "imap.custom.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
