/**
 * 聊天界面组件：ChatGPT 风格的消息界面
 * 
 * 功能：
 * - ChatGPT 风格泡泡消息（用户右蓝、AI 左白）
 * - 支持 Markdown 渲染
 * - 图片预览
 * - 与现有代码兼容
 * 
 * 遵循 docs/ARCHITECTURE.md 中的UI组件规范
 */

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
// @ts-ignore - react-markdown types may have issues
import ReactMarkdown from "react-markdown";
// @ts-ignore
import remarkGfm from "remark-gfm";
import { ChatMessage, TaskStatus, AppConfig, LogEntry } from "../types";
import { executeTask, isTauriEnvironment } from "../utils/tauri";
import { ChatSidebar, ChatSession } from "./ChatSidebar";

// 导入Tauri事件API
let listenProgress: any = null;
if (isTauriEnvironment()) {
  import("@tauri-apps/api/event").then((module) => {
    listenProgress = module.listen;
  });
}

interface ChatInterfaceProps {
  config: AppConfig | null;
  /** 任务步骤变化回调 */
  onStepsChange?: (steps: Array<{ step: any; result?: any }>) => void;
  /** 当前步骤索引变化回调 */
  onCurrentStepChange?: (index: number) => void;
  /** 日志变化回调 */
  onLogsChange?: (logs: LogEntry[]) => void;
  /** 任务状态变化回调 */
  onStatusChange?: (status: TaskStatus) => void;
}

/**
 * 聊天界面组件
 */
export const ChatInterface: React.FC<ChatInterfaceProps> = ({
  config,
  onStepsChange,
  onCurrentStepChange,
  onLogsChange,
  onStatusChange,
  onProgressPanelToggle,
}) => {
  // 聊天会话管理
  const [chats, setChats] = useState<ChatSession[]>([]);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState<boolean>(() => {
    // 从 localStorage 加载折叠状态
    const saved = localStorage.getItem("deskjarvis_sidebar_collapsed");
    return saved === "true";
  });
  // 当前聊天的消息
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [status, setStatus] = useState<TaskStatus>("idle");
  const statusRef = useRef<TaskStatus>("idle"); // 用于在定时器中访问最新状态
  const [currentSteps, setCurrentSteps] = useState<Array<{ step: any; result?: any }>>([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [lastTaskContext, setLastTaskContext] = useState<any>(null); // 保存上次任务上下文
  const [isDragging, setIsDragging] = useState(false);
  const [attachedPath, setAttachedPath] = useState<string | null>(null);
  const [copyToast, setCopyToast] = useState<{ show: boolean; message: string }>({ show: false, message: "" });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const currentAssistantMessageIdRef = useRef<string | null>(null); // 跟踪当前正在更新的AI消息ID
  const prevMessagesLengthRef = useRef<number>(0); // 用于优化滚动性能
  const typingStateRef = useRef<{
    messageIndex: number;
    charIndex: number;
    isTyping: boolean;
    currentMessage: string;
    _clearingScheduled?: boolean; // 标记是否已安排清除延迟
  } | null>(null); // 打字机效果状态
  const planningUpdateIntervalRef = useRef<NodeJS.Timeout | null>(null); // 打字机效果定时器
  const isTaskCancelledRef = useRef<boolean>(false); // 任务是否被取消
  const unlistenProgressRef = useRef<(() => void) | null>(null); // 进度事件监听器的清理函数

  // 组件加载时输出日志，确认控制台正常工作
  useEffect(() => {
    console.log("🚀 [ChatInterface] 组件已加载");
    console.log("🚀 [ChatInterface] Tauri环境:", isTauriEnvironment());
    console.log("🚀 [ChatInterface] 当前消息数量:", messages.length);
    
    // 添加提示：如何打开开发者工具
    console.log("💡 [提示] 要打开开发者工具，请在应用窗口内按：");
    console.log("   macOS: Cmd + Option + I");
    console.log("   Windows/Linux: F12");
    console.log("   或者右键点击页面 → 选择'检查'");
  }, []);

  // 从 localStorage 加载聊天历史
  useEffect(() => {
    const savedChats = localStorage.getItem("deskjarvis_chats");
    if (savedChats) {
      try {
        const parsedChats = JSON.parse(savedChats).map((chat: any) => ({
          ...chat,
          createdAt: new Date(chat.createdAt),
          updatedAt: new Date(chat.updatedAt),
        }));
        setChats(parsedChats);
        
        // 如果有聊天记录，默认选中第一个
        if (parsedChats.length > 0) {
          setCurrentChatId(parsedChats[0].id);
          loadChatMessages(parsedChats[0].id);
        }
      } catch (e) {
        console.error("加载聊天历史失败:", e);
      }
    }
  }, []);

  // 当 currentChatId 变化时，保存上一个聊天的消息（作为额外保护）
  const prevChatIdRef = useRef<string | null>(null);
  const prevMessagesRef = useRef<ChatMessage[]>([]);
  useEffect(() => {
    // 如果之前有聊天ID且有消息，保存它
    if (prevChatIdRef.current && prevChatIdRef.current !== currentChatId && prevMessagesRef.current.length > 0) {
      saveChatMessages(prevChatIdRef.current, prevMessagesRef.current);
    }
    // 更新 ref
    prevChatIdRef.current = currentChatId;
    prevMessagesRef.current = messages;
  }, [currentChatId, messages]);

  // 组件卸载时保存当前聊天的消息
  useEffect(() => {
    return () => {
      if (currentChatId && messages.length > 0) {
        saveChatMessages(currentChatId, messages);
      }
    };
  }, []);

  // 保存聊天历史到 localStorage
  const saveChats = (updatedChats: ChatSession[]) => {
    localStorage.setItem("deskjarvis_chats", JSON.stringify(updatedChats));
    setChats(updatedChats);
  };

  // 加载指定聊天的消息
  const loadChatMessages = (chatId: string) => {
    const savedMessages = localStorage.getItem(`deskjarvis_messages_${chatId}`);
    if (savedMessages) {
      try {
        const parsedMessages = JSON.parse(savedMessages).map((msg: any) => ({
          ...msg,
          timestamp: new Date(msg.timestamp),
        }));
        setMessages(parsedMessages);
      } catch (e) {
        console.error("加载消息失败:", e);
        setMessages([]);
      }
    } else {
      setMessages([]);
    }
  };

  // 保存当前聊天的消息
  const saveChatMessages = (chatId: string, msgs: ChatMessage[]) => {
    localStorage.setItem(`deskjarvis_messages_${chatId}`, JSON.stringify(msgs));
  };

  // 新建聊天
  const handleNewChat = () => {
    // 先保存当前聊天的消息（如果存在）
    if (currentChatId && messages.length > 0) {
      saveChatMessages(currentChatId, messages);
    }
    
    const newChatId = `chat_${Date.now()}`;
    const newChat: ChatSession = {
      id: newChatId,
      title: "新聊天",
      createdAt: new Date(),
      updatedAt: new Date(),
      messageCount: 0,
    };
    
    const updatedChats = [newChat, ...chats];
    saveChats(updatedChats);
    setCurrentChatId(newChatId);
    setMessages([]);
    setInput("");
    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = "56px";
    }
    // 重置任务进度相关状态
    setStatus("idle");
    setCurrentSteps([]);
    setCurrentStepIndex(-1);
    setLogs([]);
    setLastTaskContext(null);
    // 通知父组件重置进度面板
    onStepsChange?.([]);
    onCurrentStepChange?.(-1);
    onLogsChange?.([]);
    onStatusChange?.("idle");
  };

  // 切换聊天
  const handleSelectChat = (chatId: string) => {
    // 先保存当前聊天的消息（如果存在且不是同一个聊天）
    if (currentChatId && currentChatId !== chatId && messages.length > 0) {
      saveChatMessages(currentChatId, messages);
    }
    
    setCurrentChatId(chatId);
    loadChatMessages(chatId);
    setInput("");
    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = "56px";
    }
    // 重置任务进度相关状态
    setStatus("idle");
    setCurrentSteps([]);
    setCurrentStepIndex(-1);
    setLogs([]);
    setLastTaskContext(null);
    // 通知父组件重置进度面板
    onStepsChange?.([]);
    onCurrentStepChange?.(-1);
    onLogsChange?.([]);
    onStatusChange?.("idle");
  };

  // 删除聊天
  const handleDeleteChat = (chatId: string) => {
    const updatedChats = chats.filter((chat) => chat.id !== chatId);
    saveChats(updatedChats);
    
    // 删除消息记录
    localStorage.removeItem(`deskjarvis_messages_${chatId}`);
    
    // 如果删除的是当前聊天，切换到其他聊天或新建
    if (currentChatId === chatId) {
      if (updatedChats.length > 0) {
        setCurrentChatId(updatedChats[0].id);
        loadChatMessages(updatedChats[0].id);
      } else {
        setCurrentChatId(null);
        setMessages([]);
      }
    }
  };

  // 清空当前聊天消息
  const handleClearCurrentChat = () => {
    if (!currentChatId) return;
    
    if (window.confirm("确定要清空当前聊天的所有消息吗？")) {
      setMessages([]);
      setStatus("idle");
      setCurrentSteps([]);
      setCurrentStepIndex(-1);
      setLogs([]);
      setLastTaskContext(null);
      setAttachedPath(null);
      
      // 清空 localStorage 中的消息
      localStorage.removeItem(`deskjarvis_messages_${currentChatId}`);
      
      // 更新聊天标题
      const updatedChats = chats.map((chat) =>
        chat.id === currentChatId
          ? { ...chat, title: "新聊天", messageCount: 0, updatedAt: new Date() }
          : chat
      );
      saveChats(updatedChats);
    }
  };

  // 清空所有聊天
  const handleClearAllChats = () => {
    // 清空所有聊天记录
    chats.forEach((chat) => {
      localStorage.removeItem(`deskjarvis_messages_${chat.id}`);
    });
    
    // 重置状态
    setChats([]);
    setCurrentChatId(null);
    setMessages([]);
    setStatus("idle");
    setCurrentSteps([]);
    setCurrentStepIndex(-1);
    setLogs([]);
    setLastTaskContext(null);
    setAttachedPath(null);
    
    // 清空 localStorage
    localStorage.removeItem("deskjarvis_chats");
  };

  // 更新聊天标题（从第一条用户消息提取）
  const updateChatTitle = (chatId: string, firstMessage: string) => {
    const title = firstMessage.slice(0, 30) || "新聊天";
    const updatedChats = chats.map((chat) =>
      chat.id === chatId
        ? { ...chat, title, updatedAt: new Date(), messageCount: messages.length + 1 }
        : chat
    );
    saveChats(updatedChats);
  };

  // 更新状态并通知父组件
  const updateStatus = (newStatus: TaskStatus) => {
    setStatus(newStatus);
    statusRef.current = newStatus; // 同步更新 ref
    onStatusChange?.(newStatus);
  };

  const addLog = (level: LogEntry["level"], message: string) => {
    const newLog: LogEntry = {
      timestamp: new Date(),
      level,
      message,
    };
    setLogs((prev) => {
      const updated = [...prev, newLog];
      onLogsChange?.(updated);
      return updated;
    });
  };

  // 自动滚动到底部（优化：只在消息数量变化时滚动，避免打字机效果时频繁滚动）
  useEffect(() => {
    // 只在消息数量变化时滚动，避免打字机效果时频繁滚动
    if (messages.length !== prevMessagesLengthRef.current) {
      prevMessagesLengthRef.current = messages.length;
      // 使用 requestAnimationFrame 确保滚动在下一帧执行，避免阻塞
      requestAnimationFrame(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
      });
    }
    // 打字机效果时的滚动由打字机效果内部处理，这里不再重复滚动
  }, [messages.length]); // 只依赖消息数量，不依赖整个 messages 数组，避免打字机效果时频繁触发

  // 处理消息中的图片：当消息加载后，检查并加载图片
  useEffect(() => {
    console.log("🔄 [图片处理] useEffect 触发，消息数量:", messages.length);
    
    const processImagesForMessages = async () => {
      if (!isTauriEnvironment()) {
        console.log("⚠️ [图片处理] 不在Tauri环境，跳过图片处理");
        return;
      }

      const messagesToUpdate: ChatMessage[] = [];
      let hasUpdates = false;

      for (const message of messages) {
        // 如果消息已经有图片数据，跳过
        if (message.images && message.images.length > 0) {
          console.log(`✅ [图片处理] 消息 ${message.id} 已有图片数据`);
          continue;
        }

        // 检查是否有截图路径但还没有图片数据
        if (message.taskResult?.steps) {
          const screenshotPaths: string[] = [];
          for (const stepItem of message.taskResult.steps) {
            if (
              stepItem.step?.type === "screenshot_desktop" &&
              stepItem.result?.success &&
              stepItem.result?.data?.path
            ) {
              screenshotPaths.push(stepItem.result.data.path);
            }
          }

          if (screenshotPaths.length > 0) {
            console.log(`🔄 [图片处理] 消息 ${message.id} 需要加载图片，路径:`, screenshotPaths);
            
            try {
              const fs = await import("@tauri-apps/plugin-fs");
              const imageDataUrls: string[] = [];

              for (const path of screenshotPaths) {
                try {
                  // 先检查文件是否存在
                  try {
                    const exists = await fs.exists(path);
                    if (!exists) {
                      console.warn(`⚠️ [图片处理] 文件不存在，跳过: ${path}`);
                      continue; // 跳过不存在的文件，不显示错误
                    }
                  } catch (checkError) {
                    // 如果检查文件存在性失败，尝试直接读取（某些情况下 exists 可能不可用）
                    console.log(`ℹ️ [图片处理] 无法检查文件存在性，尝试直接读取: ${path}`);
                  }
                  
                  console.log(`📖 [图片处理] 读取文件: ${path}`);
                  const imageBytes = await fs.readFile(path);
                  console.log(`✅ [图片处理] 文件读取成功，大小: ${imageBytes.length} 字节`);

                  // 转换为 base64
                  let binaryString = '';
                  const len = imageBytes.length;
                  const chunkSize = 8192;
                  for (let i = 0; i < len; i += chunkSize) {
                    const chunk = imageBytes.slice(i, i + chunkSize);
                    binaryString += String.fromCharCode(...chunk);
                  }

                  const base64 = btoa(binaryString);
                  const dataUrl = `data:image/png;base64,${base64}`;
                  imageDataUrls.push(dataUrl);
                  console.log(`✅ [图片处理] 图片转换成功，已添加到列表`);
                } catch (e: any) {
                  // 文件不存在或其他错误：静默处理，不显示错误日志
                  const errorMessage = e?.message || String(e);
                  if (errorMessage.includes("No such file") || errorMessage.includes("os error 2")) {
                    console.warn(`⚠️ [图片处理] 文件不存在，跳过: ${path}`);
                  } else {
                    // 其他错误（权限问题等）才显示警告
                    console.warn(`⚠️ [图片处理] 读取文件失败，跳过: ${path}`, errorMessage);
                  }
                }
              }

              if (imageDataUrls.length > 0) {
                const updatedMessage: ChatMessage = {
                  ...message,
                  images: imageDataUrls,
                };
                messagesToUpdate.push(updatedMessage);
                hasUpdates = true;
                console.log(`✅ [图片处理] 消息 ${message.id} 图片加载完成`);
              }
            } catch (e: any) {
              console.error(`❌ [图片处理] 导入 fs 插件失败:`, e);
            }
          }
        }
      }

      if (hasUpdates) {
        console.log(`🔄 [图片处理] 更新 ${messagesToUpdate.length} 条消息的图片数据`);
        setMessages((prev) => {
          const updated = prev.map((msg) => {
            const updatedMsg = messagesToUpdate.find((u) => u.id === msg.id);
            return updatedMsg || msg;
          });
          // 保存更新后的消息
          if (currentChatId) {
            saveChatMessages(currentChatId, updated);
          }
          return updated;
        });
      }
    };

    processImagesForMessages();
  }, [messages, currentChatId]);

  // 停止当前任务
  const handleStop = () => {
    console.log("🛑 [handleStop] 用户请求停止任务");
    isTaskCancelledRef.current = true;
    
    // 清理进度事件监听器
    if (unlistenProgressRef.current) {
      unlistenProgressRef.current();
      unlistenProgressRef.current = null;
    }
    
    // 停止打字机效果
    if (typingStateRef.current) {
      typingStateRef.current = null;
    }
    
    // 更新状态
    updateStatus("idle");
    addLog("warning", "任务已取消");
    
    // 更新AI消息，显示任务已取消
    if (currentAssistantMessageIdRef.current) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant"
            ? { ...msg, content: "任务已取消" }
            : msg
        )
      );
    }
    
    // 重置引用
    currentAssistantMessageIdRef.current = null;
  };

  const handleSend = async () => {
    // 如果正在执行任务，点击发送按钮就是停止任务
    if (status !== "idle") {
      handleStop();
      return;
    }
    
    if (!input.trim()) return;

    // 如果没有当前聊天，先创建一个
    if (!currentChatId) {
      handleNewChat();
      // 等待状态更新
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // 检查配置
    if (!config?.api_key) {
      addMessage({
        id: Date.now().toString(),
        role: "system",
        content: "请先在设置中配置API密钥",
        timestamp: new Date(),
      });
      return;
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    // 如果是第一条消息，更新聊天标题
    if (messages.length === 0 && currentChatId) {
      updateChatTitle(currentChatId, input.trim());
    }

    setMessages((prev) => [...prev, userMessage]);
    const instruction = input.trim();
    setInput("");
    // 重置 textarea 高度
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = "56px";
    }
    // 重置取消标记
    isTaskCancelledRef.current = false;
    
    updateStatus("planning");
    setCurrentSteps([]);
    setCurrentStepIndex(-1);
    setLogs([]);
    addLog("info", "开始规划任务...");

    // ✅ 先设置进度事件监听器（在消息创建之前，避免竞态条件）
    let unlistenProgress: (() => void) | null = null;
    if (isTauriEnvironment()) {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlistenProgress = await listen("task-progress", (event: any) => {
          // 如果任务已被取消，忽略进度事件
          if (isTaskCancelledRef.current) {
            return;
          }
          const progressEvent = event.payload as any;
          handleProgressEvent(progressEvent);
        });
        unlistenProgressRef.current = unlistenProgress;
      } catch (e) {
        console.error("设置进度事件监听器失败:", e);
      }
    }

    // ✅ 立即创建并显示 AI 回复消息（初始内容就是"正在规划任务..."，避免后续更新时出现两个气泡）
    // 先检查是否已经有"正在规划任务"的消息，如果有就删除（避免重复）
    setMessages((prev) => {
      // 删除所有"正在规划任务"的消息（避免重复）
      const filtered = prev.filter(
        (msg) => !(msg.role === "assistant" && msg.content.includes("正在规划任务"))
      );
      return filtered;
    });
    
    const tempAssistantId = `temp-assistant-${Date.now()}`;
    currentAssistantMessageIdRef.current = tempAssistantId;
    const initialAssistantMessage: ChatMessage = {
      id: tempAssistantId,
      role: "assistant",
      content: "",  // 初始为空，打字机效果会逐步显示
      timestamp: new Date(),
    };
    console.log("✅ [handleSend] 创建AI消息，ID:", tempAssistantId);
    setMessages((prev) => {
      // 再次检查，确保没有重复的规划消息
      const hasPlanningMessage = prev.some(
        (msg) => msg.role === "assistant" && (msg.content.includes("正在规划任务") || msg.content.includes("正在分析任务") || msg.content.includes("正在生成步骤"))
      );
      if (hasPlanningMessage) {
        console.warn("⚠️ [handleSend] 发现重复的规划消息，跳过创建");
        return prev;
      }
      console.log("✅ [handleSend] 添加AI消息到列表");
      return [...prev, initialAssistantMessage];
    });
    
    // 打字机效果：逐字显示，然后清除，再显示下一个
    // 使用 ref 来保存定时器，确保可以在其他地方访问
    planningUpdateIntervalRef.current = null;
    const planningMessages = [
      "正在分析任务...",
      "正在规划任务...",
      "正在生成步骤...",
    ];
    
    // 使用 ref 保存状态，避免闭包问题
    typingStateRef.current = {
      messageIndex: 0,
      charIndex: 0,
      isTyping: true,
      currentMessage: planningMessages[0],
      _clearingScheduled: false,
    };
    
    // 使用 requestAnimationFrame 来节流滚动，避免频繁滚动导致抖动
    let scrollAnimationFrame: number | null = null;
    const scheduleScroll = () => {
      if (scrollAnimationFrame) return; // 如果已经有待执行的滚动，跳过
      scrollAnimationFrame = requestAnimationFrame(() => {
        if (messagesEndRef.current) {
          messagesEndRef.current.scrollIntoView({ behavior: "instant" });
        }
        scrollAnimationFrame = null;
      });
    };
    
    planningUpdateIntervalRef.current = setInterval(() => {
      // 使用 ref 获取最新状态，避免闭包问题
      // 注意：只在状态不是 planning 且不是 executing 时才停止（executing 时可能还在更新消息）
      if (!currentAssistantMessageIdRef.current || !typingStateRef.current) {
        if (planningUpdateIntervalRef.current) {
          clearInterval(planningUpdateIntervalRef.current);
          planningUpdateIntervalRef.current = null;
        }
        typingStateRef.current = null;
        return;
      }
      
      // 如果状态不再是 planning 和 executing，停止打字机效果
      // 注意：executing 状态时可能还在更新消息，所以也要继续
      if (statusRef.current !== "planning" && statusRef.current !== "executing") {
        if (planningUpdateIntervalRef.current) {
          clearInterval(planningUpdateIntervalRef.current);
          planningUpdateIntervalRef.current = null;
        }
        // 如果消息内容为空，设置一个默认内容，避免显示空白
        setMessages((prev) => {
          return prev.map((msg) => {
            if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant" && (!msg.content || !msg.content.trim())) {
              return { ...msg, content: "正在处理..." };
            }
            return msg;
          });
        });
        typingStateRef.current = null;
        return; // 停止打字机效果，让事件处理更新消息
      }
      
      const state = typingStateRef.current;
      
      setMessages((prev) => {
        return prev.map((msg) => {
          if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant") {
            
            // 如果消息内容已经不是规划相关的，停止打字机效果
            const content = msg.content.trim();
            
            // 只有在明确包含"规划完成"时才停止打字机效果
            // 其他情况（包括空内容、部分内容如"正在"）都继续打字机效果
            if (content.includes("规划完成") && !content.includes("正在分析任务") && !content.includes("正在规划任务") && !content.includes("正在生成步骤")) {
              if (planningUpdateIntervalRef.current) {
                clearInterval(planningUpdateIntervalRef.current);
                planningUpdateIntervalRef.current = null;
              }
              typingStateRef.current = null;
              return msg;
            }
            
            if (state.isTyping) {
              // 打字阶段：逐字添加
              if (state.charIndex < state.currentMessage.length) {
                const newContent = state.currentMessage.substring(0, state.charIndex + 1);
                state.charIndex++;
                // 只在每3个字符更新一次时触发滚动，减少滚动频率
                if (state.charIndex % 3 === 0) {
                  scheduleScroll();
                }
                return { ...msg, content: newContent };
              } else {
                // 打字完成，延迟0.5秒后开始清除（进一步减少延迟时间，提升流畅度）
                // 使用一个标记来避免重复设置延迟
                if (!state._clearingScheduled) {
                  state._clearingScheduled = true;
                  setTimeout(() => {
                    if (typingStateRef.current) {
                      typingStateRef.current.isTyping = false;
                      typingStateRef.current._clearingScheduled = false;
                    }
                  }, 500); // 从800ms减少到500ms，提升流畅度
                }
                return msg;
              }
            } else {
              // 清除阶段：逐字删除
              if (state.charIndex > 0) {
                const newContent = state.currentMessage.substring(0, state.charIndex - 1);
                state.charIndex--;
                // 清除阶段不触发滚动，避免抖动
                return { ...msg, content: newContent };
              } else {
                // 清除完成，切换到下一个消息
                state.messageIndex = (state.messageIndex + 1) % planningMessages.length;
                state.currentMessage = planningMessages[state.messageIndex];
                state.isTyping = true;
                state.charIndex = 0;
                state._clearingScheduled = false;
                // 不要将内容设为空，而是立即显示第一个字符，避免出现空白
                const firstChar = state.currentMessage.substring(0, 1);
                return { ...msg, content: firstChar };
              }
            }
          }
          return msg;
        });
      });
    }, 50); // 从30ms增加到50ms，减少更新频率，降低抖动

    console.log("✅ [handleSend] 打字机效果已启动");

    try {
      console.log("🚀 [handleSend] 进入 try 块，准备执行任务");
      // 构建上下文信息（包含之前创建的文件和附加的文件路径）
      const context: any = lastTaskContext ? {
        created_files: lastTaskContext.created_files || [],
        last_created_file: lastTaskContext.last_created_file || null,
      } : {};
      
      // 如果用户附加了文件/文件夹路径，添加到上下文中
      if (attachedPath) {
        context.attached_path = attachedPath;
        console.log(`[上下文] 用户附加了路径: ${attachedPath}`);
      }
      
      // 添加聊天历史到上下文（只包含用户和AI的消息，排除系统消息）
      const chatHistory = messages
        .filter(msg => msg.role === "user" || msg.role === "assistant")
        .slice(-10) // 只保留最近10条消息，避免token过多
        .map(msg => ({
          role: msg.role === "user" ? "user" : "assistant",
          content: msg.content,
        }));
      
      if (chatHistory.length > 0) {
        context.chat_history = chatHistory;
        console.log(`[上下文] 添加聊天历史: ${chatHistory.length} 条消息`);
      }
      
      // 调用Tauri命令执行任务（传递上下文）
      // 如果任务已被取消，不执行
      if (isTaskCancelledRef.current) {
        console.log("🛑 [handleSend] 任务已被取消，跳过执行");
        return;
      }
      
      console.log("🚀 [handleSend] 准备调用 executeTask");
      console.log("🚀 [handleSend] 指令:", instruction);
      console.log("🚀 [handleSend] 上下文:", context);
      console.log("🚀 [handleSend] Tauri环境:", isTauriEnvironment());
      
      let result;
      try {
        result = await executeTask(instruction, Object.keys(context).length > 0 ? context : null);
        console.log("✅ [handleSend] executeTask 调用成功，结果:", result);
      } catch (executeError: any) {
        console.error("❌ [handleSend] executeTask 调用失败:", executeError);
        console.error("❌ [handleSend] 错误详情:", {
          message: executeError?.message,
          stack: executeError?.stack,
          name: executeError?.name
        });
        throw executeError; // 重新抛出错误，让 catch 块处理
      }
      
      // 检查任务是否在执行过程中被取消
      if (isTaskCancelledRef.current) {
        console.log("🛑 [handleSend] 任务在执行过程中被取消");
        return;
      }

      // 更新步骤列表（如果进度事件没有更新）
      if (result.steps && result.steps.length > 0) {
        // 只有在步骤列表为空时才更新（避免覆盖实时更新的数据）
        setCurrentSteps((prev) => {
          if (prev.length === 0) {
            return result.steps;
          }
          return prev;
        });
        onStepsChange?.(result.steps);
      }

      // 检查是否有截图结果，提取图片路径
      console.log("🔍 [图片预览] 开始检查任务结果...");
      console.log("🔍 [图片预览] 任务结果:", JSON.stringify(result, null, 2));
      
      const screenshotPaths: string[] = [];
      if (result.steps && result.steps.length > 0) {
        console.log(`🔍 [图片预览] 找到 ${result.steps.length} 个步骤`);
        for (const stepItem of result.steps) {
          const stepType = stepItem.step?.type;
          const stepResult = stepItem.result;
          const stepData = stepResult?.data;
          
          console.log("🔍 [图片预览] 检查步骤:", { 
            stepType, 
            success: stepResult?.success, 
            path: stepData?.path,
            data: stepData
          });
          
          if (
            stepType === "screenshot_desktop" &&
            stepResult?.success &&
            stepData?.path
          ) {
            console.log("✅ [图片预览] 找到截图路径:", stepData.path);
            screenshotPaths.push(stepData.path);
          }
        }
      } else {
        console.log("⚠️ [图片预览] 没有找到步骤数据");
      }
      
      console.log(`📊 [图片预览] 提取的截图路径数量: ${screenshotPaths.length}`);
      console.log(`📊 [图片预览] 截图路径列表:`, screenshotPaths);

      // 如果有截图，读取图片文件并转换为base64
      const imageDataUrls: string[] = [];
      const isTauri = isTauriEnvironment();
      console.log(`🔍 [图片预览] Tauri环境检测: ${isTauri}`);
      console.log(`🔍 [图片预览] window对象:`, typeof window !== "undefined" ? "存在" : "不存在");
      console.log(`🔍 [图片预览] __TAURI__:`, typeof window !== "undefined" && "__TAURI__" in window);
      console.log(`🔍 [图片预览] __TAURI_INTERNALS__:`, typeof window !== "undefined" && "__TAURI_INTERNALS__" in window);
      
      if (screenshotPaths.length > 0) {
        if (isTauri) {
          console.log("✅ [图片预览] 开始读取截图文件（Tauri环境）");
          try {
            const fs = await import("@tauri-apps/plugin-fs");
            console.log("✅ [图片预览] fs 模块导入成功");
            console.log("✅ [图片预览] fs 模块内容:", Object.keys(fs));
            
            for (const path of screenshotPaths) {
              try {
                console.log(`📖 [图片预览] 开始读取文件: ${path}`);
                
                // 先检查文件是否存在
                try {
                  const exists = await fs.exists(path);
                  if (!exists) {
                    console.warn(`⚠️ [图片预览] 文件不存在，跳过: ${path}`);
                    continue; // 跳过不存在的文件，不显示错误
                  }
                } catch (checkError) {
                  // 如果检查文件存在性失败，尝试直接读取（某些情况下 exists 可能不可用）
                  console.log(`ℹ️ [图片预览] 无法检查文件存在性，尝试直接读取: ${path}`);
                }
                
                // Tauri 2.0 fs 插件：readFile 支持绝对路径
                const imageBytes = await fs.readFile(path);
                console.log(`✅ [图片预览] 文件读取成功，大小: ${imageBytes.length} 字节`);
                
                // 转换为 base64
                let binaryString = '';
                const len = imageBytes.length;
                
                // 使用更高效的方式转换（分批处理，避免栈溢出）
                const chunkSize = 8192;
                for (let i = 0; i < len; i += chunkSize) {
                  const chunk = imageBytes.slice(i, i + chunkSize);
                  binaryString += String.fromCharCode(...chunk);
                }
                
                const base64 = btoa(binaryString);
                const dataUrl = `data:image/png;base64,${base64}`;
                imageDataUrls.push(dataUrl);
                console.log(`✅ [图片预览] 图片已添加到预览列表: ${path}`);
              } catch (e: any) {
                // 文件不存在或其他错误：静默处理，不显示错误日志
                // 只在开发模式下显示详细错误信息
                const errorMessage = e?.message || String(e);
                if (errorMessage.includes("No such file") || errorMessage.includes("os error 2")) {
                  console.warn(`⚠️ [图片预览] 文件不存在，跳过: ${path}`);
                } else {
                  // 其他错误（权限问题等）才显示警告
                  console.warn(`⚠️ [图片预览] 读取文件失败，跳过: ${path}`, errorMessage);
                }
              }
            }
          } catch (e: any) {
            console.error("❌ [图片预览] 导入 fs 插件失败:", e);
            console.error("❌ [图片预览] 错误详情:", {
              message: e?.message,
              stack: e?.stack,
              name: e?.name
            });
          }
        } else {
          console.warn("⚠️ [图片预览] 不在Tauri环境，无法读取文件");
        }
      } else {
        console.log("⚠️ [图片预览] 没有找到截图路径");
      }
      
      console.log(`📊 [图片预览] 最终图片数据URL数量: ${imageDataUrls.length}`);
      if (imageDataUrls.length > 0) {
        console.log(`✅ [图片预览] 图片数据URL已准备就绪，将添加到消息中`);
      } else {
        console.warn(`⚠️ [图片预览] 没有成功加载任何图片`);
      }

      // 构建消息内容
      let messageContent = result.success
        ? (result.message || "任务执行完成")
        : `执行失败: ${result.message || "未知错误"}`;
      
      console.log("📝 [handleSend] 原始消息内容:", messageContent);
      console.log("📝 [handleSend] result对象:", { success: result.success, message: result.message, hasSteps: !!result.steps });
      
      // 如果有截图，显示保存路径
      if (screenshotPaths.length > 0) {
        const paths = screenshotPaths.map(p => `\n📁 ${p}`).join('');
        messageContent += paths;
      }

      // ✅ 停止打字机效果（如果还在运行）
      if (planningUpdateIntervalRef.current) {
        clearInterval(planningUpdateIntervalRef.current);
        planningUpdateIntervalRef.current = null;
      }
      if (typingStateRef.current) {
        typingStateRef.current = null;
      }

      // ✅ 更新临时AI消息为最终消息（替换临时消息）
      const finalAssistantId = `assistant-${Date.now()}`;
      
      // 确保消息内容不为空
      const finalMessageContent = messageContent?.trim() || (result.success ? "任务执行完成" : "任务执行失败");
      console.log("📝 [handleSend] 准备更新最终消息，内容长度:", finalMessageContent.length);
      
      setMessages((prev) => {
        // 确保能找到AI消息并更新
        const hasAssistantMessage = prev.some(
          (msg) => msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant"
        );
        
        if (!hasAssistantMessage && currentAssistantMessageIdRef.current) {
          // 如果找不到临时消息，直接添加新消息
          console.warn("⚠️ [handleSend] 未找到临时AI消息，直接添加最终消息");
          return [
            ...prev,
            {
              id: finalAssistantId,
              role: "assistant" as const,
              content: finalMessageContent,
              timestamp: new Date(),
              taskResult: result,
              images: imageDataUrls.length > 0 ? imageDataUrls : undefined,
            },
          ];
        }
        
        const updated = prev.map((msg) => {
          if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant") {
            console.log("✅ [handleSend] 找到并更新AI消息");
            return {
              ...msg,
              id: finalAssistantId,
              content: finalMessageContent, // 确保内容不为空
              taskResult: result,
              images: imageDataUrls.length > 0 ? imageDataUrls : undefined,
            };
          }
          return msg;
        });
        
        // 验证更新后的消息
        const finalMsg = updated.find(m => m.id === finalAssistantId);
        if (!finalMsg || !finalMsg.content || !finalMsg.content.trim()) {
          console.error("❌ [handleSend] 更新后的消息内容为空！");
        }
        
        return updated;
      });
      currentAssistantMessageIdRef.current = null; // 清除引用
      
      // 保存任务上下文（用于下次任务理解"这个文件"等引用）
      if (result.steps && result.steps.length > 0) {
        const contextFiles: string[] = [];
        let latestFile: string | null = null; // 最新的文件路径（优先使用重命名/移动后的新路径）
        
        // 按步骤顺序处理，确保最新的操作排在前面
        for (const stepItem of result.steps) {
          const stepType = stepItem.step?.type;
          const stepResult = stepItem.result;
          const stepData = stepResult?.data;
          
          if (!stepResult?.success) continue; // 跳过失败的操作
          
          // 收集创建的文件路径
          if (stepType === "file_create" && stepData?.path) {
            contextFiles.push(stepData.path);
            if (!latestFile) latestFile = stepData.path; // 如果没有最新文件，使用这个
          }
          // 收集截图创建的文件路径
          if (stepType === "screenshot_desktop" && stepData?.path) {
            contextFiles.push(stepData.path);
            if (!latestFile) latestFile = stepData.path; // 如果没有最新文件，使用这个
          }
          // 收集重命名/移动操作的文件路径（优先使用新路径）
          if (stepType === "file_rename" || stepType === "file_move") {
            // 对于重命名/移动操作，优先使用新路径作为最新文件
            // file_rename 返回: {source: "...", target: "..."}
            // file_move 返回: {path: "...", new_path: "..."}
            const newPath = stepData?.target || stepData?.new_path; // file_rename 用 target，file_move 用 new_path
            const oldPath = stepData?.source || stepData?.path; // file_rename 用 source，file_move 用 path
            
            if (newPath) {
              contextFiles.push(newPath);
              latestFile = newPath; // 重命名/移动后的新路径是最新的
              console.log(`✅ [上下文] 重命名/移动操作: ${oldPath} → ${newPath}，更新最新文件为: ${newPath}`);
            } else if (oldPath) {
              contextFiles.push(oldPath);
              if (!latestFile) latestFile = oldPath;
            }
          }
        }
        
        if (contextFiles.length > 0) {
          const finalLatestFile = latestFile || contextFiles[0];
          setLastTaskContext({
            created_files: contextFiles,
            last_created_file: finalLatestFile, // 优先使用最新操作的文件路径
            timestamp: Date.now(),
          });
          console.log(`✅ [上下文] 更新上下文: 最新文件 = ${finalLatestFile}, 所有文件 = [${contextFiles.join(", ")}]`);
        } else {
          // 如果没有收集到文件，但之前有上下文，保持之前的上下文（不要清空）
          console.log(`⚠️ [上下文] 本次任务没有操作文件，保持之前的上下文`);
        }
      }
      
      if (result.success) {
        addLog("success", "任务执行完成");
        updateStatus("completed");
      } else {
        addLog("error", "任务执行失败");
        updateStatus("error");
      }
    } catch (error) {
      // 如果任务已被取消，不显示错误
      if (isTaskCancelledRef.current) {
        console.log("🛑 [handleSend] 任务已取消，忽略错误");
        return;
      }
      
      const errorMsg = error instanceof Error ? error.message : "未知错误";
      addLog("error", `执行失败: ${errorMsg}`);
      
      // ✅ 更新AI消息为错误信息
      if (currentAssistantMessageIdRef.current) {
        setMessages((prev) => {
          return prev.map((msg) => {
            if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant") {
              return {
                ...msg,
                content: `执行失败: ${errorMsg}`,
              };
            }
            return msg;
          });
        });
        currentAssistantMessageIdRef.current = null;
      } else {
        // 只有在没有现有消息可更新时才创建新消息
        const errorMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `执行失败: ${errorMsg}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
      updateStatus("error");
    } finally {
      // 清理事件监听器和定时器
      if (unlistenProgress) {
        unlistenProgress();
        unlistenProgressRef.current = null;
      }
      if (planningUpdateIntervalRef.current) {
        clearInterval(planningUpdateIntervalRef.current);
        planningUpdateIntervalRef.current = null;
      }
      typingStateRef.current = null; // 清除打字机状态
      
      // 检查任务是否被取消（在重置标记之前）
      const wasCancelled = isTaskCancelledRef.current;
      
      // 重置取消标记
      isTaskCancelledRef.current = false;
      
      // 如果任务没有被取消，延迟重置状态
      if (!wasCancelled) {
        setTimeout(() => {
          updateStatus("idle");
        }, 2000);
      } else {
        // 如果任务被取消，立即重置状态
        updateStatus("idle");
      }
    }
  };

  // 处理进度事件
  const handleProgressEvent = (event: any) => {
    const eventType = event.type;
    const eventData = event.data || {};

    console.log("📊 [进度事件]", eventType, eventData);

    // ✅ 实时更新AI回复内容（只更新，不创建新消息）
    if (currentAssistantMessageIdRef.current) {
      setMessages((prev) => {
        // 确保只更新现有消息，不创建新消息
        const messageExists = prev.some(
          (msg) => msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant"
        );
        
        if (!messageExists) {
          // 如果消息不存在，直接返回，不创建新消息
          console.warn("⚠️ [进度事件] 找不到要更新的消息，跳过更新");
          return prev;
        }
        
        // 检查是否已经有多个"正在规划任务"的消息（避免重复显示）
        const planningMessages = prev.filter(
          (msg) => msg.role === "assistant" && msg.content.includes("正在规划任务")
        );
        
        // 如果已经有多个"正在规划任务"的消息，删除多余的（只保留当前正在更新的消息）
        if (planningMessages.length > 1) {
          console.warn(`⚠️ [进度事件] 发现 ${planningMessages.length} 个规划消息，删除多余的`);
          const messagesToKeep = prev.filter((msg) => {
            // 保留当前正在更新的消息
            if (msg.id === currentAssistantMessageIdRef.current) {
              return true;
            }
            // 删除其他"正在规划任务"的消息
            if (msg.role === "assistant" && msg.content.includes("正在规划任务")) {
              return false;
            }
            // 保留其他消息
            return true;
          });
          
          return messagesToKeep.map((msg) => {
            if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant") {
              let newContent = msg.content;
              
              switch (eventType) {
                case "planning_started":
                  // 规划阶段：不覆盖消息内容，让打字机效果继续工作
                  return msg; // 返回原消息，让打字机效果继续
                  break;
                default:
                  // 其他事件类型保持原有逻辑
                  break;
              }
              
              return { ...msg, content: newContent };
            }
            return msg;
          });
        }
        
        return prev.map((msg) => {
          if (msg.id === currentAssistantMessageIdRef.current && msg.role === "assistant") {
            let newContent = msg.content;
            
            switch (eventType) {
              case "planning_started":
                // 规划阶段：不覆盖消息内容，让打字机效果继续工作
                // 如果打字机效果还没开始，初始化它
                if (!typingStateRef.current) {
                  typingStateRef.current = {
                    messageIndex: 0,
                    charIndex: 0,
                    isTyping: true,
                    currentMessage: planningMessages[0],
                  };
                }
                return msg; // 返回原消息，让打字机效果继续
                break;
              case "planning_completed":
                // 停止打字机效果
                if (typingStateRef.current) {
                  typingStateRef.current = null;
                }
                // 清除打字机效果的定时器
                if (planningUpdateIntervalRef.current) {
                  clearInterval(planningUpdateIntervalRef.current);
                  planningUpdateIntervalRef.current = null;
                }
                const stepCount = eventData.step_count || 0;
                newContent = `规划完成，共 ${stepCount} 个步骤\n\n`;
                console.log("✅ [进度事件] planning_completed，更新消息内容:", newContent);
                break;
              case "browser_starting":
                newContent = `规划完成\n\n正在启动浏览器...`;
                break;
              case "browser_started":
                newContent = `规划完成\n\n浏览器已启动`;
                break;
              case "step_started":
                const stepIndex = eventData.step_index || 0;
                const totalSteps = eventData.total_steps || 0;
                const stepAction = eventData.step?.action || eventData.step?.description || "";
                newContent = `规划完成\n\n正在执行步骤 ${stepIndex + 1}/${totalSteps}: ${stepAction}`;
                break;
              case "step_completed":
                const completedIndex = eventData.step_index || 0;
                const completedTotal = eventData.total_steps || 0;
                const completedAction = eventData.step?.action || eventData.step?.description || "";
                const stepResult = eventData.result || {};
                newContent = `规划完成\n\n步骤 ${completedIndex + 1}/${completedTotal}: ${completedAction} ${stepResult.success ? "完成" : "失败"}`;
                break;
              case "step_failed":
                const failedIndex = eventData.step_index || 0;
                const failedTotal = eventData.total_steps || 0;
                const failedAction = eventData.step?.action || eventData.step?.description || "";
                newContent = `规划完成\n\n步骤 ${failedIndex + 1}/${failedTotal}: ${failedAction} 失败`;
                break;
              case "task_completed":
                const successCount = eventData.success_count || 0;
                const totalCount = eventData.total_count || 0;
                newContent = `任务完成：${successCount}/${totalCount} 个步骤成功`;
                break;
              case "task_failed":
                newContent = `任务失败: ${eventData.error || "未知错误"}`;
                break;
            }
            
            return { ...msg, content: newContent };
          }
          return msg;
        });
      });
    }

    switch (eventType) {
      case "task_started":
        updateStatus("planning");
        addLog("info", `开始执行任务: ${eventData.instruction || ""}`);
        break;

      case "planning_started":
        updateStatus("planning");
        addLog("info", "AI正在规划任务...");
        break;

      case "planning_completed":
        updateStatus("executing");
        const stepCount = eventData.step_count || 0;
        addLog("success", `规划完成，共 ${stepCount} 个步骤`);
        if (eventData.steps && eventData.steps.length > 0) {
          // 初始化步骤列表（带空结果）
          const initialSteps = eventData.steps.map((step: any) => ({
            step,
            result: undefined,
          }));
          setCurrentSteps(initialSteps);
          onStepsChange?.(initialSteps);
        }
        break;

      case "browser_starting":
        addLog("info", "正在启动浏览器...");
        break;

      case "browser_started":
        addLog("success", "浏览器已启动");
        break;

      case "step_started":
        const stepIndex = eventData.step_index || 0;
        const totalSteps = eventData.total_steps || 0;
        const step = eventData.step || {};
        setCurrentStepIndex(stepIndex);
        onCurrentStepChange?.(stepIndex);
        addLog("info", `执行步骤 ${stepIndex + 1}/${totalSteps}: ${step.action || step.description || ""}`);
        break;

      case "step_completed":
        const completedStepIndex = eventData.step_index || 0;
        const completedStep = eventData.step || {};
        const stepResult = eventData.result || {};
        
        setCurrentSteps((prev) => {
          const updated = [...prev];
          if (updated[completedStepIndex]) {
            updated[completedStepIndex] = {
              step: completedStep,
              result: stepResult,
            };
          }
          return updated;
        });
        
        if (stepResult.success) {
          addLog("success", `步骤 ${completedStepIndex + 1} 成功: ${stepResult.message || ""}`);
        } else {
          addLog("error", `步骤 ${completedStepIndex + 1} 失败: ${stepResult.message || ""}`);
        }
        break;

      case "step_failed":
        const failedStepIndex = eventData.step_index || 0;
        addLog("error", `步骤 ${failedStepIndex + 1} 失败: ${eventData.error || ""}`);
        break;

      case "task_completed":
        updateStatus("idle");
        const success = eventData.success || false;
        const successCount = eventData.success_count || 0;
        const totalCount = eventData.total_count || 0;
        addLog("success", `任务完成: ${successCount}/${totalCount} 个步骤成功`);
        break;

      case "task_failed":
        updateStatus("idle");
        addLog("error", `任务失败: ${eventData.error || ""}`);
        break;

      case "browser_stopping":
        addLog("info", "正在停止浏览器...");
        break;

      case "browser_stopped":
        addLog("success", "浏览器已停止");
        break;

      default:
        console.log("未知进度事件类型:", eventType);
    }
  };

  const addMessage = (message: ChatMessage) => {
    setMessages((prev) => {
      const updated = [...prev, message];
      // 保存到 localStorage
      if (currentChatId) {
        saveChatMessages(currentChatId, updated);
      }
      return updated;
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 处理文件/文件夹选择
  const handleFileSelect = () => {
    // 使用文件输入来选择文件/文件夹
    fileInputRef.current?.click();
  };

  // 处理拖拽
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      // 尝试获取完整路径（Tauri 环境）
      const path = (file as any).path || file.name;
      
      if (path) {
        setAttachedPath(path);
        setInput((prev) => {
          const trimmed = prev.trim();
          return trimmed ? `${trimmed} ${path}` : path;
        });
      }
    }
  };

  // 移除附加的路径
  const handleRemoveAttachment = () => {
    setAttachedPath(null);
    if (attachedPath) {
      setInput((prev) => prev.replace(attachedPath, "").trim());
    }
  };

  // 复制消息内容
  const handleCopyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      // 显示成功提示
      setCopyToast({ show: true, message: "已复制到剪贴板" });
      // 3秒后自动隐藏
      setTimeout(() => {
        setCopyToast({ show: false, message: "" });
      }, 3000);
    } catch (error) {
      console.error("复制失败:", error);
      // 降级方案：使用传统方法
      const textArea = document.createElement("textarea");
      textArea.value = content;
      textArea.style.position = "fixed";
      textArea.style.opacity = "0";
      document.body.appendChild(textArea);
      textArea.select();
      try {
        document.execCommand("copy");
        // 显示成功提示
        setCopyToast({ show: true, message: "已复制到剪贴板" });
        // 3秒后自动隐藏
        setTimeout(() => {
          setCopyToast({ show: false, message: "" });
        }, 3000);
      } catch (err) {
        console.error("复制失败（降级方案）:", err);
        // 显示失败提示
        setCopyToast({ show: true, message: "复制失败" });
        setTimeout(() => {
          setCopyToast({ show: false, message: "" });
        }, 3000);
      }
      document.body.removeChild(textArea);
    }
  };

  // 撤回操作
  const handleUndo = async (taskResult: TaskResult) => {
    try {
      if (!taskResult?.steps || taskResult.steps.length === 0) {
        console.warn("没有可撤回的操作");
        addMessage({
          id: Date.now().toString(),
          role: "system",
          content: "没有可撤回的操作",
          timestamp: new Date(),
        });
        return;
      }

      // 检查是否有可撤回的操作
      const undoableSteps = taskResult.steps.filter((stepItem) => {
      const stepType = stepItem.step?.type;
      const stepResult = stepItem.result;
      // 只撤回成功的操作
      if (!stepResult?.success) return false;
      
      // 可撤回的操作类型
      const undoableTypes = [
        "file_delete", "file_rename", "file_move", "file_create", 
        "file_write", "file_copy", "file_batch_rename", "file_batch_copy",
        "execute_python_script" // 可能包含删除操作
      ];
      
      // 对于execute_python_script，检查是否是删除操作
      if (stepType === "execute_python_script") {
        const stepParams = stepItem.step?.params || {};
        const script = stepParams.script || "";
        const action = stepParams.action || stepItem.step?.action || "";
        const description = stepItem.step?.description || "";
        const scriptLower = script.toLowerCase();
        const actionStr = typeof action === "string" ? action : String(action || "");
        const descriptionStr = typeof description === "string" ? description : String(description || "");
        
        // 检查是否是删除操作（使用 includes 而不是 in）
        return (
          actionStr.includes("删除") || descriptionStr.includes("删除") ||
          scriptLower.includes("os.remove") || scriptLower.includes("os.unlink") || 
          scriptLower.includes("path.unlink") || (scriptLower.includes("pathlib") && scriptLower.includes("unlink"))
        );
      }
      
        return undoableTypes.includes(stepType);
      });

      if (undoableSteps.length === 0) {
        addMessage({
          id: Date.now().toString(),
          role: "system",
          content: "没有可撤回的操作",
          timestamp: new Date(),
        });
        return;
      }

      // 构建撤回指令：反向执行所有操作
      const undoInstructions: string[] = [];
      
      // 反向处理步骤（从后往前）
      for (let i = undoableSteps.length - 1; i >= 0; i--) {
        const stepItem = undoableSteps[i];
        const stepType = stepItem.step?.type;
        const stepParams = stepItem.step?.params || {};
        const stepResult = stepItem.result;
        const stepData = stepResult?.data || {};

        if (stepType === "file_delete" || stepType === "execute_python_script") {
          // 检查是否是删除操作（通过execute_python_script执行os.remove）
          const scriptContent = stepParams.script || "";
          const action = stepParams.action || stepItem.step?.action || "";
          const description = stepItem.step?.description || "";
          const actionStr = typeof action === "string" ? action : String(action || "");
          const descriptionStr = typeof description === "string" ? description : String(description || "");
          const scriptContentStr = typeof scriptContent === "string" ? scriptContent : String(scriptContent || "");
          
          // 判断是否是删除操作（使用 includes 而不是 in）
          const isDeleteOperation = 
            stepType === "file_delete" ||
            (stepType === "execute_python_script" && (
              actionStr.includes("删除") || descriptionStr.includes("删除") ||
              (scriptContentStr.includes("os.remove") || scriptContentStr.includes("os.unlink") || scriptContentStr.includes("Path.unlink"))
            ));
          
          if (isDeleteOperation) {
            // 尝试从结果中提取文件路径
            let filePath = stepData.path || stepParams.file_path;
            
            // 如果是从脚本删除，尝试从脚本中提取路径
            if (!filePath && scriptContent) {
              // 尝试从脚本中提取文件路径（简化处理）
              const pathMatch = scriptContent.match(/['"]([^'"]+\.(txt|docx|pdf|png|jpg|jpeg|zip|dmg|pkg))['"]/);
              if (pathMatch) {
                filePath = pathMatch[1];
              }
            }
            
            // 如果从结果消息中提取路径
            if (!filePath && stepResult?.message) {
              const messageMatch = stepResult.message.match(/删除.*?([\/~][^\s]+)/);
              if (messageMatch) {
                filePath = messageMatch[1];
              }
            }
            
            if (filePath) {
              // macOS: 尝试从Trash恢复，如果不行则提示用户
              undoInstructions.push(`恢复文件 ${filePath}（从回收站）`);
            }
          }
        } else if (stepType === "file_rename") {
          // 重命名的反向：改回原名
          const target = stepData.target || stepParams.new_name;
          const source = stepData.source || stepParams.file_path;
          if (target && source && target !== source) {
            // 提取文件名（不包含路径）
            const targetName = target.split("/").pop() || target;
            const sourceName = source.split("/").pop() || source;
            undoInstructions.push(`将文件 ${targetName} 重命名为 ${sourceName}`);
          }
        } else if (stepType === "file_move") {
          // 移动的反向：移回原位置
          const newPath = stepData.new_path || stepData.target;
          const oldPath = stepData.path || stepParams.file_path;
          if (newPath && oldPath && newPath !== oldPath) {
            const newFileName = newPath.split("/").pop() || newPath;
            const oldDir = oldPath.split("/").slice(0, -1).join("/") || "原位置";
            undoInstructions.push(`将文件 ${newFileName} 移动回 ${oldDir}`);
          }
        } else if (stepType === "file_create") {
          // 创建文件的反向：删除文件
          const filePath = stepData.path || stepParams.file_path;
          if (filePath) {
            const fileName = filePath.split("/").pop() || filePath;
            undoInstructions.push(`删除文件 ${fileName}`);
          }
        } else if (stepType === "file_write") {
          // 写入文件的反向：恢复原内容（需要保存原内容，这里简化处理）
          const filePath = stepParams.file_path;
          if (filePath) {
            const fileName = filePath.split("/").pop() || filePath;
            undoInstructions.push(`恢复文件 ${fileName} 的原始内容`);
          }
        } else if (stepType === "file_copy") {
          // 复制的反向：删除副本
          const target = stepData.target || stepParams.target_path;
          if (target) {
            const fileName = target.split("/").pop() || target;
            undoInstructions.push(`删除复制的文件 ${fileName}`);
          }
        }
      }

      if (undoInstructions.length === 0) {
        addMessage({
          id: Date.now().toString(),
          role: "system",
          content: "无法生成撤回操作",
          timestamp: new Date(),
        });
        return;
      }

      // 构建撤回指令
      const undoInstruction = `撤回刚才的操作：${undoInstructions.join("，")}`;
      
      // 添加用户消息
      const undoUserMessage: ChatMessage = {
        id: Date.now().toString(),
        role: "user",
        content: undoInstruction,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, undoUserMessage]);

      // 执行撤回操作
      try {
        updateStatus("planning");
        addLog("info", "开始撤回操作...");

        // 构建上下文（使用原始任务的结果）
        const context: any = {};
        if (taskResult.steps && taskResult.steps.length > 0) {
          const contextFiles: string[] = [];
          for (const stepItem of taskResult.steps) {
            const stepData = stepItem.result?.data;
            if (stepData?.path) contextFiles.push(stepData.path);
            if (stepData?.target) contextFiles.push(stepData.target);
            if (stepData?.new_path) contextFiles.push(stepData.new_path);
          }
          if (contextFiles.length > 0) {
            context.created_files = contextFiles;
            context.last_created_file = contextFiles[contextFiles.length - 1];
          }
        }

        // 检查任务是否被取消
        if (isTaskCancelledRef.current) {
          console.log("🛑 [handleUndo] 任务已被取消，跳过执行");
          return;
        }

        const result = await executeTask(undoInstruction, Object.keys(context).length > 0 ? context : null);

        // 检查任务是否在执行过程中被取消
        if (isTaskCancelledRef.current) {
          console.log("🛑 [handleUndo] 任务在执行过程中被取消");
          return;
        }

        // 更新消息
        const undoAssistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: result.success ? `撤回成功：${result.message}` : `撤回失败：${result.message}`,
          timestamp: new Date(),
          taskResult: result,
        };
        setMessages((prev) => [...prev, undoAssistantMessage]);

        if (result.success) {
          addLog("success", "撤回操作完成");
          updateStatus("completed");
        } else {
          addLog("error", "撤回操作失败");
          updateStatus("error");
        }
      } catch (error: any) {
        // 如果任务已被取消，不显示错误
        if (isTaskCancelledRef.current) {
          console.log("🛑 [handleUndo] 任务已取消，忽略错误");
          return;
        }

        console.error("撤回操作失败:", error);
        addLog("error", `撤回失败: ${error.message || error}`);
        updateStatus("error");
        
        const errorMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: `撤回失败: ${error.message || error}`,
          timestamp: new Date(),
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (outerError: any) {
      // 捕获所有未预期的错误，防止组件崩溃
      console.error("撤回操作发生未预期错误:", outerError);
      addLog("error", `撤回操作失败: ${outerError.message || outerError}`);
      updateStatus("idle");
      
      const errorMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        role: "assistant",
        content: `撤回操作失败: ${outerError.message || "未知错误，请查看控制台"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <div className="h-full w-full flex flex-col bg-white dark:bg-[#0a0a0a] overflow-hidden relative">
      {/* 复制成功提示 Toast */}
      <AnimatePresence>
        {copyToast.show && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 pointer-events-none"
          >
            <div className="bg-gray-900 dark:bg-gray-800 text-white px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              <span className="text-sm font-medium">{copyToast.message}</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      
      {/* 主内容区域 */}
      <div className="flex-1 flex overflow-hidden">
        {/* 左侧边栏 */}
        <ChatSidebar
        currentChatId={currentChatId}
        chats={chats}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => {
          const newState = !sidebarCollapsed;
          setSidebarCollapsed(newState);
          localStorage.setItem("deskjarvis_sidebar_collapsed", String(newState));
        }}
        onClearAllChats={handleClearAllChats}
      />

      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 bg-white dark:bg-[#0a0a0a]" style={{
          // 优化滚动性能，减少抖动
          scrollBehavior: "smooth",
          willChange: status === "planning" ? "scroll-position" : "auto",
        }}>
        {messages.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 mt-20">
            <p className="text-xl font-medium mb-3 text-gray-700 dark:text-gray-300">👋 欢迎使用 DeskJarvis</p>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              用自然语言告诉我你想做什么，我会帮你完成！
            </p>
            <div className="mt-10 text-left max-w-md mx-auto space-y-3 text-sm">
              <p className="font-semibold text-gray-700 dark:text-gray-300">示例指令：</p>
              <ul className="space-y-2 text-gray-600 dark:text-gray-400">
                <li className="flex items-start gap-2">
                  <span className="text-blue-500 dark:text-blue-400 mt-0.5">•</span>
                  <span>从Python官网下载最新安装包</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500 dark:text-blue-400 mt-0.5">•</span>
                  <span>整理下载文件夹，按文件类型分类</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-blue-500 dark:text-blue-400 mt-0.5">•</span>
                  <span>帮我截图桌面</span>
                </li>
              </ul>
            </div>
          </div>
        )}

        <AnimatePresence>
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className={`flex ${
                message.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div className={`flex items-start gap-2 max-w-[85%] ${
                message.role === "user" ? "flex-row-reverse" : "flex-row"
              }`}>
                {/* 头像 */}
                <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : message.role === "system"
                    ? "bg-yellow-500 text-white"
                    : "bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                }`}>
                  {message.role === "user" ? "你" : message.role === "system" ? "!" : "AI"}
                </div>

                {/* 消息气泡容器 */}
                <div className={`flex flex-col ${
                  message.role === "user" ? "items-end" : "items-start"
                }`}>
                  {/* 消息气泡 */}
                  <div className={`rounded-2xl px-4 py-3 ${
                    message.role === "user"
                      ? "bg-blue-600 dark:bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                      : message.role === "system"
                      ? "bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 rounded-2xl"
                      : "bg-gray-50 dark:bg-[#1e1e1e] text-gray-900 dark:text-gray-100 shadow-sm border border-gray-100 dark:border-gray-800/50"
                  }`}>
                  {/* Markdown 内容 */}
                  {message.role === "user" ? (
                    <p className="text-white whitespace-pre-wrap m-0 text-sm leading-relaxed font-mono">{message.content}</p>
                  ) : (
                    <div className="markdown-content prose prose-sm dark:prose-invert max-w-none text-sm font-mono">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          // 段落
                          p: ({ children }: any) => <p className="m-0 mb-2 last:mb-0 leading-relaxed text-sm">{children}</p>,
                          
                          // 标题
                          h1: ({ children }: any) => <h1 className="text-lg font-bold mt-4 mb-2 first:mt-0">{children}</h1>,
                          h2: ({ children }: any) => <h2 className="text-base font-bold mt-3 mb-2 first:mt-0">{children}</h2>,
                          h3: ({ children }: any) => <h3 className="text-sm font-semibold mt-2 mb-1 first:mt-0">{children}</h3>,
                          
                          // 代码块
                          code: ({ className, children, ...props }: any) => {
                            const match = /language-(\w+)/.exec(className || '');
                            const isInline = !match;
                            
                            if (isInline) {
                              return (
                                <code 
                                  className="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800 dark:text-gray-200" 
                                  {...props}
                                >
                                  {children}
                                </code>
                              );
                            }
                            
                            return (
                              <pre className="bg-gray-900 dark:bg-gray-950 p-3 rounded-lg overflow-x-auto my-2 border border-gray-700">
                                <code className={`text-sm font-mono text-gray-100 ${className || ''}`} {...props}>
                                  {children}
                                </code>
                              </pre>
                            );
                          },
                          
                          // 列表
                          ul: ({ children }: any) => (
                            <ul className="list-disc list-inside my-2 space-y-1 ml-2">{children}</ul>
                          ),
                          ol: ({ children }: any) => (
                            <ol className="list-decimal list-inside my-2 space-y-1 ml-2">{children}</ol>
                          ),
                          li: ({ children }: any) => (
                            <li className="ml-2">{children}</li>
                          ),
                          
                          // 表格
                          table: ({ children }: any) => (
                            <div className="overflow-x-auto my-2">
                              <table className="min-w-full border-collapse border border-gray-300 dark:border-gray-600">
                                {children}
                              </table>
                            </div>
                          ),
                          thead: ({ children }: any) => (
                            <thead className="bg-gray-100 dark:bg-gray-800">{children}</thead>
                          ),
                          tbody: ({ children }: any) => <tbody>{children}</tbody>,
                          tr: ({ children }: any) => (
                            <tr className="border-b border-gray-200 dark:border-gray-700">{children}</tr>
                          ),
                          th: ({ children }: any) => (
                            <th className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-left font-semibold text-sm">
                              {children}
                            </th>
                          ),
                          td: ({ children }: any) => (
                            <td className="border border-gray-300 dark:border-gray-600 px-3 py-2 text-sm">
                              {children}
                            </td>
                          ),
                          
                          // 引用
                          blockquote: ({ children }: any) => (
                            <blockquote className="border-l-4 border-blue-500 pl-4 my-2 italic text-gray-600 dark:text-gray-400">
                              {children}
                            </blockquote>
                          ),
                          
                          // 链接
                          a: ({ href, children }: any) => (
                            <a 
                              href={href} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-blue-600 dark:text-blue-400 hover:underline"
                            >
                              {children}
                            </a>
                          ),
                          
                          // 粗体、斜体
                          strong: ({ children }: any) => (
                            <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>
                          ),
                          em: ({ children }: any) => (
                            <em className="italic">{children}</em>
                          ),
                          
                          // 水平线
                          hr: () => <hr className="my-4 border-gray-300 dark:border-gray-700" />,
                          
                          // 任务列表（GFM）
                          input: ({ checked, ...props }: any) => (
                            <input 
                              type="checkbox" 
                              checked={checked} 
                              readOnly 
                              className="mr-2"
                              {...props}
                            />
                          ),
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  )}

                  {/* 图片预览 */}
                  {message.images && message.images.length > 0 ? (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ duration: 0.2 }}
                      className="mt-3 space-y-2"
                    >
                      {message.images.map((imageDataUrl, idx) => {
                        console.log(`🖼️ 渲染图片 ${idx + 1}, 数据URL长度: ${imageDataUrl.length}`);
                        return (
                          <div
                            key={idx}
                            className="rounded-lg overflow-hidden border-2 border-gray-200 dark:border-gray-700 shadow-md hover:shadow-lg transition-shadow cursor-pointer group"
                            onClick={() => {
                              // 点击图片在新窗口打开大图
                              const newWindow = window.open();
                              if (newWindow) {
                                newWindow.document.write(`
                                  <!DOCTYPE html>
                                  <html>
                                    <head>
                                      <title>图片预览</title>
                                      <style>
                                        body { margin: 0; padding: 20px; background: #1a1a1a; display: flex; justify-content: center; align-items: center; min-height: 100vh; }
                                        img { max-width: 100%; max-height: 100vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
                                      </style>
                                    </head>
                                    <body>
                                      <img src="${imageDataUrl}" alt="截图预览" />
                                    </body>
                                  </html>
                                `);
                              }
                            }}
                          >
                            <img
                              src={imageDataUrl}
                              alt={`截图 ${idx + 1}`}
                              className="max-w-full h-auto block group-hover:opacity-90 transition-opacity"
                              onError={(e) => {
                                console.error(`❌ 图片加载失败 ${idx + 1}:`, e);
                              }}
                              onLoad={() => {
                                console.log(`✅ 图片加载成功 ${idx + 1}`);
                              }}
                            />
                            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-900/50 text-xs text-gray-500 dark:text-gray-400 text-center">
                              点击查看大图
                            </div>
                          </div>
                        );
                      })}
                    </motion.div>
                  ) : (
                    // 如果有截图路径但图片未加载，显示提示
                    message.taskResult && message.taskResult.steps && (() => {
                      console.log("🔍 [渲染] 检查是否有截图路径但图片未加载");
                      const paths: string[] = [];
                      for (const stepItem of message.taskResult.steps) {
                        if (
                          stepItem.step?.type === "screenshot_desktop" &&
                          stepItem.result?.success &&
                          stepItem.result?.data?.path
                        ) {
                          paths.push(stepItem.result.data.path);
                        }
                      }
                      console.log(`🔍 [渲染] 找到 ${paths.length} 个截图路径，但图片未加载`);
                      return paths.length > 0 ? (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="mt-3 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg"
                        >
                          <p className="text-sm text-yellow-800 dark:text-yellow-200 mb-1">
                            ⚠️ 图片预览加载失败
                          </p>
                          <p className="text-xs text-yellow-600 dark:text-yellow-400">
                            文件已保存到: {paths[0]}
                          </p>
                          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                            请打开开发者工具（F12）查看控制台日志
                          </p>
                          <p className="text-xs text-yellow-600 dark:text-yellow-400 mt-1">
                            Tauri环境: {isTauriEnvironment() ? "是" : "否"}
                          </p>
                        </motion.div>
                      ) : null;
                    })()
                  )}
                  </div>

                  {/* 操作按钮 - 在气泡下方 */}
                  <div className={`mt-1 flex items-center gap-2 ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}>
                    {/* 复制按钮 */}
                    <button
                      onClick={() => handleCopyMessage(message.content)}
                      className={`flex items-center justify-center w-6 h-6 rounded transition-all hover:bg-gray-100 dark:hover:bg-gray-800 ${
                        message.role === "user"
                          ? "text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300"
                          : "text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                      }`}
                      title="复制消息"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                    </button>

                    {/* 撤回按钮 - 仅AI消息且有任务结果时显示 */}
                    {message.role === "assistant" && message.taskResult && message.taskResult.steps && message.taskResult.steps.length > 0 && (
                      <button
                        onClick={() => handleUndo(message.taskResult!)}
                        className="flex items-center justify-center w-6 h-6 rounded transition-all hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
                        title="撤回操作"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
                          />
                        </svg>
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>


        <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div className="flex-shrink-0 bg-white dark:bg-[#0a0a0a] px-4 py-4">
          <div className="max-w-4xl mx-auto">
            {/* 已附加的路径显示 */}
            {attachedPath && (
              <div className="mb-3 flex items-center gap-2 px-4 py-2.5 bg-blue-50 dark:bg-blue-900/20 rounded-2xl">
                <svg className="w-4 h-4 text-blue-600 dark:text-blue-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <span className="flex-1 text-sm text-blue-800 dark:text-blue-200 truncate" title={attachedPath}>
                  {attachedPath}
                </span>
                <button
                  onClick={handleRemoveAttachment}
                  className="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded-lg hover:bg-blue-200 dark:hover:bg-blue-800/50 transition-colors"
                  title="移除"
                >
                  <svg className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
            
            {/* 输入框容器：嵌入式按钮 */}
            <div 
              className={`relative ${isDragging ? "opacity-50" : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  // 自动调整高度
                  const textarea = e.target as HTMLTextAreaElement;
                  textarea.style.height = "auto";
                  const scrollHeight = textarea.scrollHeight;
                  const minHeight = 56;
                  const maxHeight = 200;
                  
                  if (scrollHeight <= maxHeight) {
                    // 内容未超过最大高度，自动调整高度
                    textarea.style.height = `${Math.max(scrollHeight, minHeight)}px`;
                    textarea.style.overflowY = "hidden";
                  } else {
                    // 内容超过最大高度，固定高度并允许滚动
                    textarea.style.height = `${maxHeight}px`;
                    textarea.style.overflowY = "auto";
                  }
                }}
                onKeyPress={handleKeyPress}
                placeholder={isDragging ? "松开鼠标以附加文件..." : "输入你的指令或拖拽文件/文件夹到这里..."}
                disabled={status !== "idle"}
                className="w-full px-5 py-4 pr-32 rounded-[2rem] border border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1a1a1a] text-gray-900 dark:text-gray-100 placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed resize-none transition-all overflow-y-auto"
                rows={1}
                style={{ minHeight: "56px", maxHeight: "200px" }}
              />
              
              {/* 右侧嵌入式按钮组 */}
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1.5">
                {/* 文件选择按钮 */}
                <button
                  onClick={handleFileSelect}
                  disabled={status !== "idle"}
                  className="flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-2xl text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  title="选择文件或文件夹"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </button>
                
                {/* 发送/停止按钮 */}
                <button
                  onClick={handleSend}
                  disabled={status === "idle" && !input.trim()}
                  className={`flex-shrink-0 w-10 h-10 flex items-center justify-center rounded-full bg-black dark:bg-white text-white dark:text-black hover:bg-gray-800 dark:hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-black dark:focus:ring-white disabled:opacity-50 disabled:cursor-not-allowed transition-all ${
                    status !== "idle" ? "hover:bg-red-600 dark:hover:bg-red-400" : "shadow-sm hover:shadow-md"
                  }`}
                  title={status !== "idle" ? "停止任务" : "发送"}
                >
                  {status !== "idle" ? (
                    // 任务执行中显示停止图标
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  ) : (
                    // 正常状态显示箭头
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 15l7-7 7 7" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
            
            {/* 隐藏的文件输入 */}
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: "none" }}
              webkitdirectory=""
              multiple={false}
              onChange={(e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                  const file = files[0];
                  // 尝试获取完整路径（Tauri 环境）
                  const path = (file as any).path || file.webkitRelativePath || file.name;
                  setAttachedPath(path);
                  setInput((prev) => {
                    const trimmed = prev.trim();
                    return trimmed ? `${trimmed} ${path}` : path;
                  });
                }
              }}
            />
          </div>
        </div>
      </div>
      </div>
    </div>
  );
};
