# DeskJarvis 架构设计文档

> **重要**：这是项目的核心架构文档，所有开发决策都应参考此文档，确保一致性。

## 1. 整体架构

### 1.1 技术栈（已确定，不可随意更改）

```
前端UI层：Tauri (Rust) + React + TypeScript + Tailwind CSS
后端Agent层：Python 3.11+ + LangGraph/CrewAI
浏览器控制：Playwright
AI模型：Claude API (Anthropic) + 备选 OpenAI GPT-4
通信方式：Tauri Shell Command (子进程调用Python)
```

### 1.2 架构分层

```
┌─────────────────────────────────────┐
│   UI Layer (Tauri + React)          │  ← 用户交互界面
├─────────────────────────────────────┤
│   Communication Layer                │  ← Tauri Shell Command
├─────────────────────────────────────┤
│   Agent Layer (Python)               │  ← AI规划与执行
│   ├── Planner (Claude API)          │
│   ├── Executor (Playwright)         │
│   └── File Manager                   │
├─────────────────────────────────────┤
│   Browser Instance (Headless)        │  ← 独立浏览器
└─────────────────────────────────────┘
```

### 1.3 核心原则

1. **不干扰原则**：所有浏览器操作在独立headless实例中执行
2. **安全沙盒**：文件操作限制在用户指定的沙盒目录
3. **可追溯性**：所有操作记录日志，支持回滚
4. **模块化**：每个功能模块独立，可单独测试

## 2. 目录结构（标准结构，必须遵循）

```
DeskJarvis/
├── src-tauri/              # Tauri Rust后端
│   ├── src/
│   │   ├── main.rs
│   │   └── commands.rs     # 调用Python的命令
│   └── tauri.conf.json
├── src/                    # React前端
│   ├── components/
│   ├── pages/
│   └── App.tsx
├── agent/                  # Python Agent核心
│   ├── planner/           # AI规划模块
│   ├── executor/          # 执行模块
│   │   ├── browser.py    # Playwright浏览器控制
│   │   └── file_manager.py
│   ├── tools/             # 工具函数
│   └── main.py            # Agent入口
├── docs/                   # 项目文档
│   ├── ARCHITECTURE.md    # 本文档
│   ├── DEVELOPMENT.md     # 开发规范
│   └── DECISIONS.md       # 技术决策记录
├── tests/                  # 测试
└── README.md
```

## 3. 数据流

### 3.1 用户指令处理流程

```
用户输入 → UI组件 → Tauri Command → Python Agent
  ↓
Python Agent:
  1. 调用Claude API规划任务
  2. 分解为步骤列表
  3. 执行每个步骤（Playwright）
  4. 文件整理
  5. 返回结果
  ↓
Tauri接收结果 → UI更新 → 用户看到反馈
```

### 3.2 错误处理流程

```
执行失败 → 记录错误日志 → 尝试备用策略 → 
如果仍失败 → 返回错误信息给用户 → 询问是否重试
```

## 4. 关键模块说明

### 4.1 Planner（规划模块）
- **职责**：调用Claude API，将用户指令转换为可执行步骤
- **输入**：用户自然语言指令
- **输出**：结构化任务步骤（JSON格式）
- **文件位置**：`agent/planner/claude_planner.py`

### 4.2 Executor（执行模块）
- **职责**：执行规划好的任务步骤
- **浏览器控制**：`agent/executor/browser.py`（Playwright）
- **文件管理**：`agent/executor/file_manager.py`
- **原则**：每个操作都要有日志记录

### 4.3 UI组件
- **聊天界面**：`src/components/ChatInterface.tsx`
- **进度显示**：`src/components/ProgressView.tsx`
- **设置页面**：`src/components/Settings.tsx`

## 5. 配置管理

### 5.1 用户配置（存储在本地）
```json
{
  "api_key": "sk-xxx",
  "model": "claude-3-5-sonnet",
  "sandbox_path": "/Users/username/DeskJarvis/sandbox",
  "auto_confirm": false,
  "log_level": "INFO"
}
```

### 5.2 安全配置
- 沙盒路径：默认限制在用户指定目录
- 危险操作：删除、系统命令需要确认
- API密钥：加密存储（使用Tauri的secure store）

## 6. 日志与监控

- **日志位置**：`~/.deskjarvis/logs/`
- **日志格式**：JSON格式，包含时间戳、操作类型、结果
- **日志级别**：DEBUG, INFO, WARNING, ERROR

## 7. 测试策略

- **单元测试**：每个Python模块独立测试
- **集成测试**：测试完整流程（使用Mock API）
- **E2E测试**：真实场景测试（需要API Key）

---

**最后更新**：2026-02-06
