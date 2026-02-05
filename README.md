# DeskJarvis - 开源桌面AI智能助手

一个轻量级、本地运行的AI Agent桌面应用。用自然语言聊天，就能让电脑自动帮你干活：下载文件、整理资料、浏览器操作等。

**灵感来源**：想做一个“本地JARVIS”（钢铁侠助手），专治手动下载、文件乱七八糟的痛点。比QoderWork/OpenClaw更简单、更隐私、无需复杂配置！

## 为什么用DeskJarvis？
- **零门槛**：一键安装，填个API Key就能用（支持Claude/GPT）。
- **不干扰**：独立浏览器操作，不抢你的鼠标/桌面。
- **隐私强**：全本地执行，你的数据不上传。
- **实用第一**：专注高频场景，如“帮我下载Python最新版并解压整理”。
- **完全开源**：免费无限用，想改就改（GPLv3协议）。

## 核心功能（MVP版本）
- 自然语言指令聊天（例如：“从官网下载最新Chrome安装包，保存到下载文件夹并分类”）
- 自动浏览器下载 + 文件整理（重命名、分类、去重）
- 安全沙盒（只操作指定文件夹，操作前弹窗确认）
- （后续）远程控制（手机Telegram发指令，让电脑干活）

## 快速开始

### 命令行版本（当前可用）

DeskJarvis目前提供命令行版本用于原型验证和测试。

#### 1. 安装依赖

```bash
# 运行快速设置脚本（推荐）
./setup.sh

# 或手动安装
pip install -r requirements.txt
playwright install chromium
```

#### 2. 配置API密钥

首次运行会自动创建配置文件 `~/.deskjarvis/config.json`，编辑并设置你的Claude API密钥：

```json
{
  "api_key": "your-claude-api-key-here",
  "model": "claude-3-5-sonnet-20241022",
  "sandbox_path": "~/.deskjarvis/sandbox"
}
```

#### 3. 运行测试

```bash
# 命令行模式
python agent/main.py "从Python官网下载最新安装包"

# 交互式模式
python agent/main.py
```

### 桌面应用版本（开发中）

桌面应用（Tauri + React）正在开发中，敬请期待！

详细使用说明请查看 [agent/README.md](agent/README.md)

## 截图演示
（等你做好demo后，这里上传GIF截图）

## 开发进度

### ✅ 已完成（MVP阶段）
- [x] 项目架构设计和文档体系
- [x] Python Agent核心模块
  - [x] 配置管理模块
  - [x] 日志系统（JSON格式）
  - [x] Claude规划器（Planner）
  - [x] 浏览器执行器（Browser Executor）
  - [x] 文件管理器（File Manager）
  - [x] 命令行入口
- [x] 代码模板和开发规范

### 🚧 进行中
- [ ] 桌面应用UI（Tauri + React）
- [ ] 集成测试和E2E测试

### 📋 计划中
- [ ] 远程控制（Telegram Bot）
- [ ] 更多文件操作功能
- [ ] 场景模板库

欢迎贡献！提issue或PR~

## 开发文档

**对于开发者**：
- 📐 [架构设计文档](docs/ARCHITECTURE.md) - 了解整体架构和技术栈
- 📝 [开发规范文档](docs/DEVELOPMENT.md) - 代码规范和开发流程
- 🤖 [AI辅助开发指南](docs/AI_WORKFLOW.md) - 如何使用AI辅助开发
- 📋 [技术决策记录](docs/DECISIONS.md) - 重要技术决策和原因

**快速开始开发**：
1. 阅读 [架构设计文档](docs/ARCHITECTURE.md)
2. 阅读 [AI辅助开发指南](docs/AI_WORKFLOW.md)
3. 使用标准提示词模板开始开发

## 作者
今晚打老虎🐯


License: GPLv3
