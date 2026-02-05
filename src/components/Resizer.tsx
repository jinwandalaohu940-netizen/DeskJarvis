/**
 * 拖动调整大小组件
 * 
 * 功能：
 * - 提供拖动条，允许用户拖动调整相邻元素的宽度
 * - 支持垂直和水平方向
 * - 使用 requestAnimationFrame 优化性能
 */

import React, { useRef, useEffect, useState, useCallback } from "react";

interface ResizerProps {
  /** 方向：'vertical' 垂直（调整宽度）或 'horizontal' 水平（调整高度） */
  direction?: "vertical" | "horizontal";
  /** 拖动开始时的回调 */
  onResizeStart?: () => void;
  /** 拖动时的回调，传入新的尺寸 */
  onResize: (size: number) => void;
  /** 拖动结束时的回调 */
  onResizeEnd?: () => void;
  /** 最小尺寸 */
  minSize?: number;
  /** 最大尺寸 */
  maxSize?: number;
  /** 是否禁用 */
  disabled?: boolean;
  /** 当前尺寸（用于初始化） */
  currentSize?: number;
  /** 是否反转拖动方向（用于右侧面板，向右拖动时缩小） */
  reverse?: boolean;
}

/**
 * 拖动调整大小组件
 */
export const Resizer: React.FC<ResizerProps> = ({
  direction = "vertical",
  onResizeStart,
  onResize,
  onResizeEnd,
  minSize,
  maxSize,
  disabled = false,
  currentSize,
  reverse = false,
}) => {
  const resizerRef = useRef<HTMLDivElement>(null);
  const targetElementRef = useRef<HTMLElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const startPosRef = useRef<number>(0);
  const startSizeRef = useRef<number>(0);

  // 直接操作 DOM，确保实时跟随鼠标
  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!targetElementRef.current) return;

    let delta: number;
    if (direction === "vertical") {
      delta = e.clientX - startPosRef.current;
    } else {
      delta = e.clientY - startPosRef.current;
    }

    // 如果 reverse 为 true，反转 delta（用于右侧面板）
    if (reverse) {
      delta = -delta;
    }

    let newSize = startSizeRef.current + delta;

    // 应用最小/最大限制
    if (minSize !== undefined && newSize < minSize) {
      newSize = minSize;
    }
    if (maxSize !== undefined && newSize > maxSize) {
      newSize = maxSize;
    }

    // 直接操作 DOM，立即更新，不等待 React 重新渲染
    // 使用 !important 确保覆盖 framer-motion 的动画
    targetElementRef.current.style.setProperty("width", `${newSize}px`, "important");
    targetElementRef.current.style.setProperty("transition", "none", "important");
    targetElementRef.current.style.setProperty("flex-shrink", "0", "important");
    targetElementRef.current.style.setProperty("flex-grow", "0", "important");

    // 同时更新 React 状态（用于持久化等）
    onResize(newSize);
  }, [direction, onResize, minSize, maxSize, reverse]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
    
    // 恢复过渡动画
    if (targetElementRef.current) {
      const finalSize = direction === "vertical" 
        ? targetElementRef.current.offsetWidth 
        : targetElementRef.current.offsetHeight;
      
      // 移除 !important，让 framer-motion 重新接管
      targetElementRef.current.style.removeProperty("width");
      targetElementRef.current.style.removeProperty("transition");
      
      onResize(finalSize);
      targetElementRef.current = null;
    }
    
    onResizeEnd?.();
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
    document.body.style.pointerEvents = "";
  }, [onResizeEnd, direction, onResize]);

  useEffect(() => {
    if (!isDragging) return;

    // 使用 capture 模式确保事件优先处理
    document.addEventListener("mousemove", handleMouseMove, { passive: false, capture: true });
    document.addEventListener("mouseup", handleMouseUp, { capture: true });

    return () => {
      document.removeEventListener("mousemove", handleMouseMove, { capture: true });
      document.removeEventListener("mouseup", handleMouseUp, { capture: true });
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (disabled) return;
    e.preventDefault();
    e.stopPropagation();
    
    if (!resizerRef.current) return;
    
    // 找到要调整的目标元素
    const parent = resizerRef.current.parentElement;
    if (!parent) return;
    
    // 找到 resizer 的索引
    const resizerIndex = Array.from(parent.children).indexOf(resizerRef.current);
    
    // 根据 reverse 属性决定调整哪个元素
    // reverse=true（右侧面板）：调整 resizer 之后的元素
    // reverse=false（左侧面板）：调整 resizer 之前的元素
    let targetElement: HTMLElement | null = null;
    
    if (reverse) {
      // 右侧面板：找 resizer 之后的元素
      if (resizerIndex < parent.children.length - 1) {
        targetElement = parent.children[resizerIndex + 1] as HTMLElement;
      }
    } else {
      // 左侧面板：找 resizer 之前的元素
      if (resizerIndex > 0) {
        targetElement = parent.children[resizerIndex - 1] as HTMLElement;
      }
    }
    
    if (targetElement) {
      targetElementRef.current = targetElement;
      
      // 获取当前实际尺寸
      const rect = targetElement.getBoundingClientRect();
      const initialSize = direction === "vertical" ? rect.width : rect.height;
      
      // 记录初始位置和尺寸
      if (direction === "vertical") {
        startPosRef.current = e.clientX;
        startSizeRef.current = initialSize;
      } else {
        startPosRef.current = e.clientY;
        startSizeRef.current = initialSize;
      }
      
      // 确保目标元素使用固定宽度（而不是 flex）
      targetElement.style.flexShrink = "0";
      targetElement.style.flexGrow = "0";
      targetElement.style.width = `${initialSize}px`;
      
      setIsDragging(true);
      onResizeStart?.();
      
      // 设置全局样式
      document.body.style.cursor = direction === "vertical" ? "col-resize" : "row-resize";
      document.body.style.userSelect = "none";
      // 只在拖动时禁用其他元素的指针事件，但保持 resizer 本身可交互
      document.body.style.pointerEvents = "none";
      if (resizerRef.current) {
        resizerRef.current.style.pointerEvents = "auto";
      }
    }
  };

  return (
    <div
      ref={resizerRef}
      onMouseDown={handleMouseDown}
      className={`${
        direction === "vertical"
          ? "w-1 cursor-col-resize hover:w-2"
          : "h-1 cursor-row-resize hover:h-2"
      } ${
        disabled ? "cursor-default opacity-50" : ""
      } ${
        isDragging ? "bg-blue-500 dark:bg-blue-400" : "bg-transparent hover:bg-blue-500 dark:hover:bg-blue-400"
      } transition-colors duration-100 group flex-shrink-0`}
      style={{
        position: "relative",
        zIndex: 100,
        touchAction: "none", // 防止移动端触摸滚动干扰
      }}
    >
      {/* 拖动指示线 */}
      {isDragging && (
        <div
          className={`absolute ${
            direction === "vertical"
              ? "w-0.5 h-full left-1/2 -translate-x-1/2"
              : "h-0.5 w-full top-1/2 -translate-y-1/2"
          } bg-blue-500 dark:bg-blue-400`}
        />
      )}
    </div>
  );
};
