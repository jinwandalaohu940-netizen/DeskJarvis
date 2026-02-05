/**
 * 进度面板组件：QoderWork 风格的任务进度面板
 * 
 * 功能：
 * - 可折叠任务面板
 * - 步骤卡片（带图标、进度条、状态徽章）
 * - 动画过渡效果
 * - 现代干净的设计
 * 
 * 遵循 docs/ARCHITECTURE.md 中的UI组件规范
 */

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { TaskStep, StepResult, TaskStatus } from "../types";

interface ProgressPanelProps {
  /** 是否折叠 */
  collapsed: boolean;
  /** 切换折叠状态 */
  onToggleCollapse: () => void;
  /** 当前任务状态 */
  status: TaskStatus;
  /** 任务步骤列表 */
  steps: Array<{
    step: TaskStep;
    result?: StepResult;
  }>;
  /** 当前执行的步骤索引 */
  currentStepIndex: number;
  /** 日志列表 */
  logs: Array<{
    timestamp: Date;
    level: "info" | "warning" | "error" | "success";
    message: string;
  }>;
}

/**
 * 步骤状态类型
 */
type StepStatus = "pending" | "running" | "success" | "error";

/**
 * 获取步骤状态
 */
function getStepStatus(
  index: number,
  currentIndex: number,
  result?: StepResult,
  taskStatus?: TaskStatus
): StepStatus {
  if (result?.success === false) return "error";
  if (result?.success === true) return "success";
  if (index === currentIndex && taskStatus === "executing") return "running";
  if (index < currentIndex) return "success";
  return "pending";
}

/**
 * 获取步骤类型图标
 */
const getStepTypeIcon = (stepType: string): React.ReactNode => {
  const iconClass = "w-4 h-4";
  
  if (stepType.startsWith("browser_")) {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
      </svg>
    );
  } else if (stepType.startsWith("file_")) {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    );
  } else if (stepType === "screenshot_desktop") {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    );
  } else if (stepType === "open_folder" || stepType === "open_app" || stepType === "close_app") {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
      </svg>
    );
  } else if (stepType === "download_file") {
    return (
      <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
    );
  }
  
  // 默认图标
  return (
    <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
};

/**
 * 步骤图标组件
 */
const StepIcon: React.FC<{ status: StepStatus; stepType?: string }> = ({ status, stepType }) => {
  const iconContent = stepType ? getStepTypeIcon(stepType) : null;
  
  switch (status) {
    case "running":
      return (
        <div className="relative w-6 h-6 flex items-center justify-center">
          <div className="absolute w-6 h-6 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
          {iconContent && (
            <div className="absolute inset-0 flex items-center justify-center text-blue-500 opacity-70">
              {iconContent}
            </div>
          )}
        </div>
      );
    case "success":
      return (
        <div className="w-6 h-6 rounded-full bg-green-500 flex items-center justify-center shadow-sm">
          <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      );
    case "error":
      return (
        <div className="w-6 h-6 rounded-full bg-red-500 flex items-center justify-center shadow-sm">
          <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      );
    default:
      return (
        <div className="w-6 h-6 rounded-full border-2 border-gray-400 dark:border-gray-500 flex items-center justify-center bg-gray-100 dark:bg-gray-700">
          {iconContent ? (
            <div className="text-gray-400 dark:text-gray-500">{iconContent}</div>
          ) : (
            <div className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600"></div>
          )}
        </div>
      );
  }
};

/**
 * 步骤卡片组件
 */
const StepCard: React.FC<{
  step: TaskStep;
  result?: StepResult;
  status: StepStatus;
  index: number;
}> = ({ step, result, status, index }) => {
  const progress = status === "running" ? 50 : status === "success" ? 100 : status === "error" ? 100 : 0;
  const stepType = step.type || "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ 
        duration: 0.3, 
        delay: index * 0.05,
        type: "spring",
        stiffness: 300,
        damping: 25
      }}
      whileHover={{ scale: 1.02 }}
      className={`bg-white dark:bg-[#1a1a1a] rounded-3xl p-5 transition-all ${
        status === "running"
          ? ""
          : status === "success"
          ? ""
          : status === "error"
          ? ""
          : ""
      }`}
      style={{ boxShadow: 'none' }}
    >
      <div className="flex items-start gap-2">
        {/* 状态图标 */}
        <div className="flex-shrink-0 mt-0.5">
          <StepIcon status={status} stepType={stepType} />
        </div>

        {/* 内容区域 */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {/* 步骤名称 */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <h4 className="text-xs font-semibold text-gray-900 dark:text-gray-100 break-words flex-1 min-w-0">
              {step.description || step.action}
            </h4>
            {/* 状态徽章 */}
            {status !== "pending" && (
              <span
                className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${
                  status === "success"
                    ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400"
                    : status === "error"
                    ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
                    : "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-400"
                }`}
              >
                {status === "success" ? "完成" : status === "error" ? "失败" : "执行中"}
              </span>
            )}
          </div>

          {/* 进度条 */}
          {status !== "pending" && (
            <div className="mb-2">
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
                <motion.div
                  className={`h-full ${
                    status === "success"
                      ? "bg-gradient-to-r from-green-400 to-green-500"
                      : status === "error"
                      ? "bg-gradient-to-r from-red-400 to-red-500"
                      : "bg-gradient-to-r from-blue-400 to-blue-500"
                  }`}
                  initial={{ width: 0 }}
                  animate={{ width: `${progress}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                />
              </div>
            </div>
          )}

          {/* 消息 */}
          {result?.message && (
            <p
              className={`text-xs mt-2 break-words overflow-wrap-anywhere ${
                result.success
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-600 dark:text-red-400"
              }`}
            >
              {result.message}
            </p>
          )}

          {/* 步骤类型标签 */}
          <div className="mt-2 flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300 break-all">
              {step.type}
            </span>
            {status === "running" && (
              <motion.span
                animate={{ opacity: [1, 0.5, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="text-xs text-blue-500 dark:text-blue-400 font-medium flex-shrink-0"
              >
                执行中...
              </motion.span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

/**
 * 进度面板组件
 */
export const ProgressPanel: React.FC<ProgressPanelProps> = ({
  collapsed,
  onToggleCollapse,
  status,
  steps,
  currentStepIndex,
  logs,
}) => {
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  // 固定宽度：展开 300px，折叠 64px
  const width = collapsed ? 64 : 300;

  // 自动滚动日志到底部
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // 计算总体进度
  const overallProgress =
    steps.length > 0
      ? ((currentStepIndex + (status === "completed" || status === "error" ? 1 : 0)) / steps.length) * 100
      : 0;

  // 折叠状态
  if (collapsed) {
    return (
      <motion.div
        initial={false}
        animate={{ width: width }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="bg-white dark:bg-[#0a0a0a] flex flex-col items-center flex-shrink-0 shadow-none"
        style={{ 
          width: `${width}px`,
          overflow: 'hidden',
          paddingTop: '1rem',
          paddingBottom: '1rem',
          paddingLeft: '0.5rem',
          paddingRight: '0.5rem',
          boxShadow: 'none'
        }}
      >
        {/* 展开/收起按钮 */}
        <button
          onClick={onToggleCollapse}
          className="w-9 h-9 rounded-2xl bg-black dark:bg-white hover:bg-gray-900 dark:hover:bg-gray-100 transition-colors flex items-center justify-center mb-2"
          title="展开进度面板"
        >
          <svg className="w-4 h-4 text-white dark:text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </button>
        {status !== "idle" && (
          <div className="mt-4 flex flex-col items-center">
            <div className="w-8 h-8 rounded-full border-2 border-blue-500 border-t-transparent animate-spin"></div>
            <div className="mt-2 text-xs text-gray-600 dark:text-gray-400 text-center font-medium">
              {Math.round(overallProgress)}%
            </div>
          </div>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={false}
      animate={{ width: width }}
      transition={{ duration: 0.3, ease: "easeInOut" }}
      style={{ 
        width: `${width}px`,
        flexShrink: 0,
        overflow: 'hidden',
        boxShadow: 'none'
      }}
      className="bg-white dark:bg-[#0a0a0a] flex flex-col h-full overflow-hidden shadow-none"
    >
      {/* 头部 */}
      <div className="px-4 py-3 flex items-center justify-between bg-white dark:bg-[#0a0a0a]" style={{ boxShadow: 'none' }}>
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">任务进度</h3>
        <button
          onClick={onToggleCollapse}
          className="w-9 h-9 rounded-2xl bg-black dark:bg-white hover:bg-gray-900 dark:hover:bg-gray-100 transition-colors flex items-center justify-center"
          title={collapsed ? "展开进度面板" : "折叠进度面板"}
        >
          <svg className="w-4 h-4 text-white dark:text-black" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        </button>
      </div>

      {/* 总体进度条 */}
      {status !== "idle" && (
        <div className="px-4 py-3 bg-white dark:bg-[#0a0a0a]" style={{ boxShadow: 'none' }}>
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
              {status === "planning" && "规划中"}
              {status === "executing" && "执行中"}
              {status === "completed" && "已完成"}
              {status === "error" && "执行失败"}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {steps.length > 0 ? `${currentStepIndex + 1} / ${steps.length}` : "0 / 0"}
            </span>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 overflow-hidden">
            <motion.div
              className={`h-2 rounded-full ${
                status === "error"
                  ? "bg-red-500"
                  : status === "completed"
                  ? "bg-green-500"
                  : "bg-blue-500"
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress}%` }}
              transition={{ duration: 0.3 }}
            />
          </div>
        </div>
      )}

      {/* 步骤列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 bg-white dark:bg-[#0a0a0a]" style={{ boxShadow: 'none' }}>
        {steps.length === 0 ? (
          <div className="text-center text-gray-400 dark:text-gray-500 py-8">
            <svg className="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p className="text-sm">暂无任务步骤</p>
          </div>
        ) : (
          <div className="space-y-2">
            <AnimatePresence>
              {steps.map((item, index) => {
                const stepStatus = getStepStatus(index, currentStepIndex, item.result, status);
                return (
                  <StepCard
                    key={index}
                    step={item.step}
                    result={item.result}
                    status={stepStatus}
                    index={index}
                  />
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>

      {/* 日志区域（可选，折叠在底部） */}
      {logs.length > 0 && (
        <div className="bg-gray-100 dark:bg-gray-800/50">
          <details className="px-5 py-3">
            <summary className="text-sm font-semibold text-gray-700 dark:text-gray-300 cursor-pointer">
              执行日志 ({logs.length})
            </summary>
            <div className="mt-2 max-h-32 overflow-y-auto space-y-1 font-mono text-xs">
              {logs.slice(-10).map((log, index) => (
                <div
                  key={index}
                  className={`py-1 px-2 rounded ${
                    log.level === "error"
                      ? "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20"
                      : log.level === "warning"
                      ? "text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20"
                      : log.level === "success"
                      ? "text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20"
                      : "text-gray-600 dark:text-gray-400"
                  }`}
                >
                  <span className="text-gray-400 dark:text-gray-500">
                    {log.timestamp.toLocaleTimeString()}
                  </span>{" "}
                  <span className="font-semibold">[{log.level.toUpperCase()}]</span> {log.message}
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </details>
        </div>
      )}
    </motion.div>
  );
};
