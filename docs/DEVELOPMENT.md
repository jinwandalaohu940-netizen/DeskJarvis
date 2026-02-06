# DeskJarvis 开发规范文档

> **重要**：使用AI辅助开发时，必须遵循此规范，确保代码风格和架构一致性。

## 1. 开发工作流（AI辅助开发流程）

### 1.1 开始新功能前

**必须步骤**：
1. ✅ 阅读 `docs/ARCHITECTURE.md` 了解整体架构
2. ✅ 阅读 `docs/DECISIONS.md` 了解已有技术决策
3. ✅ 在 `docs/DECISIONS.md` 中记录新功能的技术决策
4. ✅ 创建功能分支：`git checkout -b feature/功能名`

### 1.2 使用AI辅助开发时的提示词模板

**标准提示词格式**：

```
我正在开发 DeskJarvis 项目，请遵循以下约束：

【项目上下文】
- 项目架构文档：docs/ARCHITECTURE.md
- 开发规范：docs/DEVELOPMENT.md
- 技术栈：Tauri + React + Python + Playwright + Claude API

【当前任务】
[描述你要实现的功能]

【代码规范】
- Python：使用类型提示，遵循PEP 8
- TypeScript：使用严格模式，函数必须有类型
- Rust：遵循Rust标准规范
- 所有函数必须有docstring

【已有代码结构】
[粘贴相关文件的路径和关键代码]

【要求】
1. 保持与现有架构一致
2. 遵循模块化原则
3. 添加适当的错误处理
4. 添加日志记录
5. 如果涉及新依赖，先检查是否与现有依赖冲突
```

### 1.3 代码提交前检查清单

- [ ] 代码遵循项目架构
- [ ] 添加了必要的注释和docstring
- [ ] 错误处理完善
- [ ] 日志记录完整
- [ ] 更新了相关文档（如有变更）
- [ ] 代码格式正确（运行formatter）

## 2. 代码风格规范

### 2.1 Python代码规范

```python
# ✅ 好的示例
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

def download_file(
    url: str,
    save_path: str,
    timeout: int = 30
) -> Optional[str]:
    """
    下载文件到指定路径
    
    Args:
        url: 文件URL
        save_path: 保存路径
        timeout: 超时时间（秒）
    
    Returns:
        成功返回文件路径，失败返回None
    """
    try:
        # 实现逻辑
        logger.info(f"开始下载: {url}")
        # ...
        return save_path
    except Exception as e:
        logger.error(f"下载失败: {e}")
        return None
```

**必须遵循**：
- 使用类型提示（Type Hints）
- 函数必须有docstring（Google风格）
- 使用logging模块记录日志
- 异常处理要具体，不要用裸露的`except:`

### 2.2 TypeScript/React代码规范

```typescript
// ✅ 好的示例
import React, { useState, useCallback } from 'react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onSendMessage: (message: string) => Promise<void>;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ 
  onSendMessage 
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  
  const handleSend = useCallback(async (content: string) => {
    // 实现逻辑
  }, [onSendMessage]);
  
  return (
    // JSX
  );
};
```

**必须遵循**：
- 使用TypeScript严格模式
- 所有组件必须有类型定义
- 使用函数式组件 + Hooks
- Props必须定义interface

### 2.3 Rust代码规范

```rust
// ✅ 好的示例
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
pub struct TaskResult {
    success: bool,
    message: String,
    file_path: Option<String>,
}

/// 执行Python Agent任务
/// 
/// # Arguments
/// * `command` - 用户指令
/// 
/// # Returns
/// 任务执行结果
pub async fn execute_task(command: String) -> Result<TaskResult, String> {
    // 实现逻辑
}
```

**必须遵循**：
- 所有公共函数必须有文档注释（`///`）
- 使用`Result`类型处理错误
- 遵循Rust命名规范（snake_case）

## 3. 模块化开发原则

### 3.1 模块划分规则

每个模块应该：
- **单一职责**：一个模块只做一件事
- **独立测试**：可以单独测试，不依赖其他模块
- **清晰接口**：输入输出明确，文档完整
- **错误处理**：模块内部处理错误，向上抛出明确的异常

### 3.2 模块间通信

- **Python模块间**：通过函数调用，使用类型提示
- **Tauri ↔ Python**：通过Shell Command，JSON格式传递数据
- **React ↔ Tauri**：通过Tauri Commands（invoke）

## 4. 错误处理规范

### 4.1 错误类型定义

```python
# agent/tools/exceptions.py
class DeskJarvisError(Exception):
    """基础异常类"""
    pass

class BrowserError(DeskJarvisError):
    """浏览器操作错误"""
    pass

class FileManagerError(DeskJarvisError):
    """文件管理错误"""
    pass

class PlannerError(DeskJarvisError):
    """规划错误"""
    pass
```

### 4.2 错误处理模式

```python
# ✅ 好的示例
try:
    result = browser.download_file(url)
except BrowserError as e:
    logger.error(f"浏览器操作失败: {e}")
    # 尝试备用策略
    result = try_alternative_method(url)
except Exception as e:
    logger.error(f"未知错误: {e}", exc_info=True)
    raise DeskJarvisError(f"任务执行失败: {e}")
```

## 5. 日志规范

### 5.1 日志级别使用

- **DEBUG**：详细的调试信息（开发时使用）
- **INFO**：正常操作信息（用户操作、任务开始/完成）
- **WARNING**：警告信息（非致命错误，可恢复）
- **ERROR**：错误信息（操作失败，需要处理）

### 5.2 日志格式

```python
# ✅ 好的示例
logger.info(f"开始执行任务: {task_id}")
logger.debug(f"浏览器导航到: {url}")
logger.warning(f"文件已存在，跳过下载: {file_path}")
logger.error(f"下载失败: {url}", exc_info=True)
```

## 6. 测试规范

### 6.1 测试文件结构

```
tests/
├── unit/              # 单元测试
│   ├── test_planner.py
│   └── test_file_manager.py
├── integration/       # 集成测试
│   └── test_agent_flow.py
└── fixtures/          # 测试数据
```

### 6.2 测试命名规范

```python
# ✅ 好的示例
def test_download_file_success():
    """测试成功下载文件"""
    pass

def test_download_file_network_error():
    """测试网络错误处理"""
    pass
```

## 7. 依赖管理

### 7.1 Python依赖

- 使用 `requirements.txt` 或 `pyproject.toml`
- 固定版本号，避免自动更新导致问题
- 新增依赖前检查是否与现有依赖冲突

### 7.2 前端依赖

- 使用 `package.json`，固定版本
- 使用 `package-lock.json` 锁定版本

## 8. 文档更新规范

### 8.1 何时更新文档

- 添加新功能 → 更新 `ARCHITECTURE.md`
- 改变技术决策 → 更新 `DECISIONS.md`
- 改变开发流程 → 更新 `DEVELOPMENT.md`（本文档）
- 用户可见的功能变更 → 更新 `README.md`

### 8.2 文档格式

- 使用Markdown格式
- 代码示例要有注释说明
- 重要变更要标注日期和原因

## 9. AI辅助开发的注意事项

### 9.1 上下文管理

**问题**：AI可能忘记之前的决策

**解决方案**：
1. 每次对话开始时，引用相关文档
2. 重要决策记录在 `DECISIONS.md`
3. 代码变更要同步更新文档

### 9.2 代码一致性检查

**检查清单**：
- [ ] 新代码是否遵循架构文档？
- [ ] 命名规范是否一致？
- [ ] 错误处理模式是否一致？
- [ ] 日志格式是否一致？

### 9.3 遇到不一致时

如果AI生成的代码与现有代码不一致：
1. **停止**：不要直接使用不一致的代码
2. **检查**：对比架构文档和现有代码
3. **修正**：要求AI修正，或手动调整
4. **记录**：如果发现架构问题，更新架构文档

---

**最后更新**：2026-02-06
