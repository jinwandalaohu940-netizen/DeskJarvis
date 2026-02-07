# DeskJarvis - AI 桌面智能助手

<p align="center">
  <img src="src-tauri/icons/icon.png" alt="DeskJarvis Logo" width="128" height="128">
</p>

<p align="center">
  <strong>用自然语言控制电脑，让 AI 成为你的私人助理</strong>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#使用示例">使用示例</a> •
  <a href="#技术架构">技术架构</a> •
  <a href="#开发文档">开发文档</a>
</p>

---

## 项目简介

DeskJarvis 是一个基于 AI 的桌面智能助手，让你能够用自然语言控制电脑执行各种任务。无论是文件整理、浏览器操作、文档分析，还是系统控制，只需要像聊天一样告诉它你的需求，AI 会自动规划并执行任务。

这个项目是我在探索 AI Agent 应用场景时的实践，结合了 Tauri、React、Python 等技术栈，打造了一个真正可用的桌面 AI 助手。项目采用模块化设计，代码结构清晰，易于扩展和维护。

## ✨ 功能特性

### 🎯 核心能力

- **自然语言交互** - 像聊天一样控制电脑，无需学习复杂命令
- **智能任务规划** - AI 自动分解复杂任务，生成执行步骤
- **自我反思修正** - 执行失败时自动分析原因，调整方案重试
- **安全沙盒执行** - 所有文件操作限制在指定目录，保护系统安全

### 🛠️ 支持的操作

| 类别 | 功能 |
|------|------|
| 📁 文件管理 | 创建、删除、重命名、移动、复制、搜索、整理文件 |
| 🌐 浏览器自动化 | 打开网页、搜索、点击、填写表单、下载文件、验证码识别 |
| 📸 桌面截图 | 截取桌面截图并保存 |
| 👁️ 视觉助手 | OCR文字识别、VLM视觉理解、元素定位、颜色识别 |
| 📧 邮件管理 | 搜索邮件、读取邮件、下载附件、标记已读、移动邮件 |
| 📄 文档分析 | PDF/Word/Excel 智能分析、内容提取、结构化读取 |
| 📅 日历管理 | 创建/查看日历事件、冲突检测、提醒设置 |
| 📊 数据可视化 | 自动生成图表（饼图、柱状图、折线图等） |
| 🔊 系统控制 | 音量调节、屏幕亮度、通知发送、剪贴板操作 |
| ⌨️ 键盘鼠标 | 键盘输入、快捷键、鼠标点击/移动、窗口控制 |
| 📝 文本处理 | AI 翻译、总结、润色、纠错、扩写 |
| 🖼️ 图片处理 | 压缩、调整大小、格式转换 |
| ⏰ 定时任务 | 设置提醒和定时执行 |
| 📋 任务历史 | 查看历史记录，收藏常用任务 |
| 🔧 工作流 | 创建、管理、执行自定义工作流 |

### 🧠 智能特性

- **增强版代码解释器** - AI 可以编写并执行 Python 代码，自动安装依赖
- **智能错误修复** - 语法错误自动修正，失败自动重试（Reflector 机制）
- **Protocol G+ 路径约束** - 防止 AI 路径幻觉，模糊指令自动触发文件列表
- **SMART 错误反馈** - 文件未找到时提供智能建议（模糊匹配、目录内容）
- **视觉助手分级调度** - OCR 优先（成本0），VLM 兜底（语义理解）
- **长期记忆系统** - 记住你的偏好、习惯和历史操作（SQLite + ChromaDB）
- **上下文理解** - 理解"这张图片"、"刚才的文件"、"最后一份"等指代
- **意图路由** - 快速路径识别，常见操作秒级响应
- **日历实时智化** - 时间锚点注入、冲突检测、智能提醒

## 🚀 快速开始

### 环境要求

- **操作系统**: macOS 12.0+ / Windows 10+ / Linux
- **Node.js**: 18+ （用于前端构建）
- **Python**: 3.11+ （推荐 3.12，用于 AI Agent）
- **Rust**: 最新稳定版（用于 Tauri 编译）

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/jinwandalaohu66/DeskJarvis.git
cd DeskJarvis
```

#### 2. 安装前端依赖

```bash
npm install
```

#### 3. 安装 Python 依赖

```bash
# 使用 Python 3.12（推荐）
python3.12 -m pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium
```

#### 4. （可选）安装 Tesseract OCR 增强

如果你需要更好的文本提取效果（特别是中文），可以安装 Tesseract OCR：

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Windows:**
- 下载安装：https://github.com/UB-Mannheim/tesseract/wiki
- 安装时记得勾选中文语言包

**Linux:**
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim
```

> **注意**: 不安装 Tesseract 也能正常使用，系统会自动降级到 `ddddocr`（已包含在依赖中）。安装 Tesseract 后，系统会自动使用它进行中英文混合识别，效果更好。

#### 5. 启动开发模式

```bash
npm run tauri:dev
```

### 配置 API Key

首次启动后，点击左下角的 ⚙️ 设置图标，配置你的 AI API Key。

| 提供商 | 推荐模型 | 说明 |
|--------|----------|------|
| Claude | claude-3-5-sonnet | 最智能，支持视觉功能，推荐 |
| DeepSeek | deepseek-chat | 性价比高，中文好（不支持视觉） |
| OpenAI | gpt-4o / gpt-4o-mini | 稳定可靠，支持视觉功能 |

**视觉助手配置说明**：
- **OCR（必需）**: `ddddocr` 已包含在 `requirements.txt` 中，会自动安装
- **Tesseract OCR（可选）**: 如需更好的文本提取效果，可安装 Tesseract（见步骤4）
- **VLM（可选）**: 如需视觉理解（颜色、坐标、布局），请配置 Claude 或 OpenAI API Key
- **自动降级**: 系统会自动选择最佳 OCR 引擎（Tesseract > ddddocr），无需手动配置

## 📸 界面预览

```
┌─────────────────────────────────────────────────────────────────┐
│  ☰  DeskJarvis                                            ⚙️   │
├─────┬───────────────────────────────────────────┬───────────────┤
│     │                                           │  任务进度      │
│ 聊  │  你: 统计桌面文件，画个饼图                  │               │
│ 天  │                                           │  ✅ 统计文件   │
│ 记  │  AI: 好的，我来帮你统计并生成图表...         │  ✅ 生成图表   │
│ 录  │      [图表已保存到桌面]                     │               │
│     │                                           │  执行日志      │
│     │                                           │  [SUCCESS]    │
├─────┴───────────────────────────────────────────┴───────────────┤
│  📎  输入你的指令...                                      发送   │
└─────────────────────────────────────────────────────────────────┘
```

## 🎯 使用示例

### 基础操作

**文件管理:**
```
"整理桌面文件，按类型分类"
"删除下载文件夹中所有 .dmg 文件"
"将桌面上的 PDF 文件移动到文档文件夹"
"搜索包含'项目'关键词的所有文件"
```

**浏览器操作:**
```
"打开 GitHub，搜索 'DeskJarvis' 项目"
"从 Python 官网下载最新安装包"
"搜索并下载一张猫咪图片"
"填写登录表单，用户名是 admin，密码是 123456"
```

### 智能分析

**文档分析:**
```
"分析桌面上的合同.pdf，提取关键信息"
"读取报告.docx 的第三页内容"
"统计 Excel 表格中的数据，生成柱状图"
```

**视觉助手:**
```
"提取桌面上的所有文字"
"查看屏幕左上角最明显的图标是什么颜色"
"找到网页上'购买'按钮的位置"
"屏幕中间最明显的文字是什么？请给出它的归一化坐标"
```

### 系统控制

**应用管理:**
```
"打开汽水音乐"
"关闭所有浏览器窗口"
"最小化当前窗口"
```

**系统设置:**
```
"调大音量到 80%"
"屏幕亮度调到最亮"
"发送通知：会议即将开始"
```

### 邮件处理

```
"搜索来自 boss@example.com 的未读邮件"
"下载邮件中的所有 PDF 附件"
"标记所有未读邮件为已读"
"读取最新一封邮件的正文内容"
```

### 日历管理

```
"创建明天下午3点的会议提醒，标题是'项目评审'"
"查看今天的日历安排"
"检查明天是否有时间冲突"
```

## 🏗️ 技术架构

### 项目结构

```
DeskJarvis/
├── src/                    # React 前端 (TypeScript)
│   ├── components/         # UI 组件
│   │   ├── chat/          # 聊天相关组件
│   │   ├── ChatInterface.tsx  # 主聊天界面
│   │   ├── Settings.tsx   # 设置面板
│   │   └── ...
│   ├── utils/              # 工具函数
│   └── types/              # TypeScript 类型定义
├── src-tauri/              # Tauri 后端 (Rust)
│   ├── src/main.rs         # Rust 入口，处理前端通信
│   └── tauri.conf.json     # Tauri 配置
├── agent/                  # Python AI Agent
│   ├── planner/            # AI 规划器
│   │   ├── base_planner.py      # 规划器基类
│   │   ├── claude_planner.py    # Claude 规划器
│   │   ├── deepseek_planner.py  # DeepSeek 规划器
│   │   └── openai_planner.py    # OpenAI 规划器
│   ├── executor/           # 执行器
│   │   ├── browser.py          # 浏览器自动化
│   │   ├── file_manager.py     # 文件管理
│   │   ├── system_tools.py     # 系统工具（截图、OCR、VLM等）
│   │   └── ...
│   ├── orchestrator/        # 任务编排
│   │   ├── task_orchestrator.py # 任务编排器
│   │   ├── plan_executor.py    # 计划执行器
│   │   └── reflector.py        # 错误反思器
│   ├── memory/             # 记忆系统
│   │   ├── vector_memory.py    # 向量记忆（ChromaDB）
│   │   └── structured_memory.py # 结构化记忆（SQLite）
│   └── main.py             # Agent 入口
├── docs/                   # 开发文档
│   ├── ARCHITECTURE.md     # 架构设计
│   ├── DEVELOPMENT.md      # 开发规范
│   └── ...
└── tests/                  # 测试文件
```

### 技术栈

**前端:**
- React 18 + TypeScript
- Tailwind CSS（样式）
- Framer Motion（动画）
- Tauri（桌面框架）

**后端:**
- Python 3.12+（AI Agent）
- Rust（Tauri 后端）

**AI 模型:**
- Claude 3.5 Sonnet（Anthropic）
- DeepSeek Chat（DeepSeek）
- GPT-4o / GPT-4o-mini（OpenAI）

**核心依赖:**
- Playwright（浏览器自动化）
- ddddocr（OCR 识别，必需）
- Tesseract OCR（OCR 增强，可选）
- ChromaDB（向量数据库）
- SQLite（结构化存储）

### 工作流程

1. **用户输入** → 前端接收自然语言指令
2. **意图路由** → 快速识别常见操作（如打开应用）
3. **任务规划** → AI 规划器将指令分解为执行步骤
4. **步骤执行** → 执行器按步骤执行任务
5. **错误处理** → 失败时 Reflector 分析原因并重试
6. **结果返回** → 将执行结果返回给用户

## 📚 开发文档

项目包含详细的开发文档，位于 `docs/` 目录：

| 文档 | 说明 |
|------|------|
| [架构设计](docs/ARCHITECTURE.md) | 整体架构和模块设计 |
| [开发规范](docs/DEVELOPMENT.md) | 代码规范和开发流程 |
| [AI 工作流](docs/AI_WORKFLOW.md) | AI 辅助开发指南 |
| [技术决策](docs/DECISIONS.md) | 重要技术决策记录 |
| [多代理系统](docs/MULTI_AGENT.md) | 多 Agent 协作设计 |
| [应用名解析](APP_NAME_PARSING_EXPLANATION.md) | AI 应用名解析机制说明 |

## 🤝 贡献指南

欢迎贡献代码、提交 Issue 或改进文档！

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 提交 Pull Request

在提交 PR 前，请确保：
- 代码符合项目规范（见 `docs/DEVELOPMENT.md`）
- 添加必要的测试
- 更新相关文档

## 📜 开源协议

本项目采用 [GPLv3](LICENSE) 协议开源。

## 🙏 致谢

感谢以下优秀的开源项目和技术：

- [Tauri](https://tauri.app/) - 轻量级桌面应用框架
- [Anthropic Claude](https://www.anthropic.com/) - 强大的 AI 模型（支持视觉）
- [DeepSeek](https://www.deepseek.com/) - 高性价比 AI 模型
- [OpenAI](https://openai.com/) - GPT-4o 视觉模型
- [Playwright](https://playwright.dev/) - 浏览器自动化
- [ChromaDB](https://www.trychroma.com/) - 向量数据库
- [ddddocr](https://github.com/sml2h3/ddddocr) - 本地 OCR 识别库
- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - 强大的通用 OCR 引擎

---

<p align="center">
  Made with ❤️ by 今晚打老虎🐯
</p>
