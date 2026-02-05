# DeskJarvis Agent 使用指南

## 快速开始

### 1. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置API密钥

配置文件会自动创建在 `~/.deskjarvis/config.json`，首次运行时会提示你设置API密钥。

或者手动编辑配置文件：

```json
{
  "api_key": "your-claude-api-key-here",
  "model": "claude-3-5-sonnet-20241022",
  "sandbox_path": "~/.deskjarvis/sandbox",
  "auto_confirm": false,
  "log_level": "INFO"
}
```

### 3. 运行Agent

```bash
# 命令行模式
python agent/main.py "从Python官网下载最新安装包"

# 交互式模式
python agent/main.py
```

## 项目结构

```
agent/
├── main.py              # 主入口（命令行版本）
├── planner/             # AI规划模块
│   └── claude_planner.py
├── executor/            # 执行模块
│   ├── browser.py      # 浏览器控制
│   └── file_manager.py # 文件管理
└── tools/               # 工具模块
    ├── config.py       # 配置管理
    ├── logger.py       # 日志配置
    └── exceptions.py   # 异常定义
```

## 使用示例

### 示例1：下载文件

```bash
python agent/main.py "从Python官网下载最新安装包，保存到下载文件夹"
```

### 示例2：浏览器操作

```bash
python agent/main.py "打开GitHub，搜索'DeskJarvis'项目"
```

### 示例3：文件整理

```bash
python agent/main.py "整理下载文件夹，按文件类型分类"
```

## 开发说明

- 遵循 `docs/ARCHITECTURE.md` 中的架构设计
- 遵循 `docs/DEVELOPMENT.md` 中的开发规范
- 使用 `templates/python_module.py` 作为代码模板

## 故障排除

### 问题1：API密钥错误

**症状**：提示"API密钥未设置"

**解决**：检查配置文件 `~/.deskjarvis/config.json`，确保 `api_key` 字段已设置

### 问题2：Playwright浏览器未安装

**症状**：提示"浏览器启动失败"

**解决**：运行 `playwright install chromium`

### 问题3：权限错误

**症状**：无法创建文件或目录

**解决**：检查沙盒目录权限，确保有写入权限
