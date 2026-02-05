/**
 * 类型定义：项目全局类型
 */

/**
 * 任务步骤
 */
export interface TaskStep {
  type: string;
  action: string;
  params: Record<string, any>;
  description: string;
}

/**
 * 步骤执行结果
 */
export interface StepResult {
  success: boolean;
  message: string;
  data: any;
}

/**
 * 任务执行结果
 */
export interface TaskResult {
  success: boolean;
  message: string;
  steps: Array<{
    step: TaskStep;
    result: StepResult;
  }>;
  user_instruction: string;
}

/**
 * 聊天消息
 */
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  taskResult?: TaskResult;
  /** 图片附件（用于截图预览等） */
  images?: string[]; // base64 或文件路径
}

/**
 * AI提供商类型
 */
export type AIProvider = "claude" | "openai" | "deepseek" | "grok";

/**
 * 应用配置
 */
export interface AppConfig {
  provider: AIProvider;
  api_key: string;
  model: string;
  sandbox_path: string;
  auto_confirm: boolean;
  log_level: string;
}

/**
 * 任务状态
 */
export type TaskStatus = "idle" | "planning" | "executing" | "completed" | "error";

/**
 * 日志条目
 */
export interface LogEntry {
  timestamp: Date;
  level: "info" | "warning" | "error" | "success";
  message: string;
}
