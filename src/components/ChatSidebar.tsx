/**
 * 聊天侧边栏组件：Ollama 风格的聊天历史列表
 * 
 * 功能：
 * - 显示聊天历史列表（Today/Older 分组）
 * - 新建聊天
 * - 切换聊天
 * - 删除聊天
 * - 折叠/展开功能
 * 
 * 遵循 docs/ARCHITECTURE.md 中的UI组件规范
 */

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messageCount: number;
}

interface ChatSidebarProps {
  /** 当前选中的聊天ID */
  currentChatId: string | null;
  /** 聊天列表 */
  chats: ChatSession[];
  /** 新建聊天回调 */
  onNewChat: () => void;
  /** 切换聊天回调 */
  onSelectChat: (chatId: string) => void;
  /** 删除聊天回调 */
  onDeleteChat: (chatId: string) => void;
  /** 是否折叠 */
  collapsed?: boolean;
  /** 切换折叠状态回调 */
  onToggleCollapse?: () => void;
  /** 清空所有聊天回调（可选） */
  onClearAllChats?: () => void;
}

/**
 * 聊天侧边栏组件
 */
export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  currentChatId,
  chats,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  collapsed = false,
  onToggleCollapse,
  onClearAllChats,
}) => {
  const [hoveredChatId, setHoveredChatId] = useState<string | null>(null);
  
  // 固定宽度：展开 220px，折叠 64px
  const width = collapsed ? 64 : 220;

  // 按日期分组聊天
  const groupChatsByDate = () => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todayChats: ChatSession[] = [];
    const olderChats: ChatSession[] = [];

    chats.forEach((chat) => {
      const chatDate = new Date(chat.updatedAt);
      chatDate.setHours(0, 0, 0, 0);
      
      if (chatDate.getTime() === today.getTime()) {
        todayChats.push(chat);
      } else {
        olderChats.push(chat);
      }
    });

    return { todayChats, olderChats };
  };

  const { todayChats, olderChats } = groupChatsByDate();

  return (
    <>
      <motion.div
        initial={false}
        animate={{ width: collapsed ? 64 : 220 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="h-full bg-black dark:bg-white flex flex-col overflow-hidden relative flex-shrink-0"
        style={{ 
          borderTopRightRadius: '1.5rem',
          borderBottomRightRadius: '1.5rem',
          overflow: 'hidden'
        }}
      >
      {/* 顶部区域 */}
      <div className="flex-shrink-0" style={{ borderRadius: '0 1.5rem 0 0', overflow: 'hidden' }}>
        {/* 展开状态 */}
        {!collapsed && (
          <div className="pt-4 pb-2 px-2 flex items-center gap-2">
            {onToggleCollapse && (
              <button
                onClick={onToggleCollapse}
                className="p-1.5 rounded-xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors flex items-center justify-center"
                title="折叠侧边栏"
              >
                <svg className="w-4 h-4 text-black dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            
            {/* New Chat 按钮 */}
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              onClick={onNewChat}
              className="flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors text-sm font-medium text-black dark:text-white"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              <span>New Chat</span>
            </motion.button>
          </div>
        )}

        {/* 收起状态：展开按钮和加号按钮居中显示 */}
        {collapsed && (
          <div className="pt-4 pb-2 px-2 flex flex-col items-center">
            {onToggleCollapse && (
              <button
                onClick={onToggleCollapse}
                className="w-9 h-9 rounded-2xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors flex items-center justify-center mb-3"
                title="展开侧边栏"
              >
                <svg className="w-4 h-4 text-black dark:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            
            {/* 加号按钮 */}
            <button
              onClick={onNewChat}
              className="w-9 h-9 rounded-2xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors flex items-center justify-center"
              title="新建聊天"
            >
              <svg
                className="w-4 h-4 text-black dark:text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
          </div>
        )}
      </div>

      {/* 聊天列表 */}
      <div className="flex-1 overflow-y-auto">
        <AnimatePresence mode="wait">
          {!collapsed ? (
            <motion.div
              key="expanded"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="h-full"
            >
              {/* Today 分组 */}
              {todayChats.length > 0 && (
                <div className="px-3 py-2">
                  <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-900 uppercase tracking-wider mb-2">
                    Today
                  </h3>
                  <div className="space-y-1">
                    {todayChats.map((chat) => (
                      <ChatItem
                        key={chat.id}
                        chat={chat}
                        isSelected={currentChatId === chat.id}
                        isHovered={hoveredChatId === chat.id}
                        collapsed={false}
                        onSelect={() => onSelectChat(chat.id)}
                        onDelete={() => onDeleteChat(chat.id)}
                        onMouseEnter={() => setHoveredChatId(chat.id)}
                        onMouseLeave={() => setHoveredChatId(null)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Older 分组 */}
              {olderChats.length > 0 && (
                <div className="px-3 py-2">
                  <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-900 uppercase tracking-wider mb-2">
                    Older
                  </h3>
                  <div className="space-y-1">
                    {olderChats.map((chat) => (
                      <ChatItem
                        key={chat.id}
                        chat={chat}
                        isSelected={currentChatId === chat.id}
                        isHovered={hoveredChatId === chat.id}
                        collapsed={false}
                        onSelect={() => onSelectChat(chat.id)}
                        onDelete={() => onDeleteChat(chat.id)}
                        onMouseEnter={() => setHoveredChatId(chat.id)}
                        onMouseLeave={() => setHoveredChatId(null)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* 空状态 */}
              {chats.length === 0 && (
                <div className="px-3 py-8 text-center text-gray-400 dark:text-gray-900 text-sm">
                  <p>还没有聊天记录</p>
                  <p className="text-xs mt-2">点击 "New Chat" 开始对话</p>
                </div>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="collapsed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="px-2 py-2 flex flex-col items-center gap-2"
            >
              <div className="flex flex-col items-center gap-2 w-full">
                {chats.map((chat) => (
                  <ChatItem
                    key={chat.id}
                    chat={chat}
                    isSelected={currentChatId === chat.id}
                    isHovered={hoveredChatId === chat.id}
                    collapsed={true}
                    onSelect={() => onSelectChat(chat.id)}
                    onDelete={() => onDeleteChat(chat.id)}
                    onMouseEnter={() => setHoveredChatId(chat.id)}
                    onMouseLeave={() => setHoveredChatId(null)}
                  />
                ))}
              </div>
              {chats.length === 0 && (
                <div className="py-8 text-center">
                  <svg
                    className="w-6 h-6 mx-auto text-gray-400 dark:text-gray-900"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                    />
                  </svg>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* 底部：设置和清空所有聊天按钮（仅在展开状态显示） */}
      {!collapsed && (
        <div className="flex-shrink-0 pt-2 pb-4 px-2 flex items-center gap-2" style={{ borderRadius: '0 0 1.5rem 0', overflow: 'hidden' }}>
          {/* 设置按钮 */}
          <button
            onClick={() => {
              // 触发设置页面切换（需要通过父组件）
              window.dispatchEvent(new CustomEvent('navigate-to-settings'));
            }}
              className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors text-sm font-medium text-black dark:text-white"
            title="设置"
          >
            <svg
              className="w-4 h-4 text-black dark:text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
            <span>设置</span>
          </button>
          
          {/* 清空所有聊天按钮（仅在有多条聊天时显示） */}
          {chats.length > 0 && onClearAllChats && (
            <button
              onClick={() => {
                if (window.confirm("确定要清空所有聊天记录吗？此操作不可恢复。")) {
                  onClearAllChats();
                }
              }}
              className="w-9 h-9 rounded-full bg-red-600 hover:bg-red-700 dark:bg-red-600 dark:hover:bg-red-700 transition-colors flex items-center justify-center"
              title="清空所有聊天"
            >
              <svg
                className="w-4 h-4 text-white"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
            </button>
          )}
        </div>
      )}

      {/* 底部：设置按钮（仅在收起状态显示） */}
      {collapsed && (
        <div className="flex-shrink-0 pt-2 pb-4 px-2 flex items-center justify-center" style={{ borderRadius: '0 0 1.5rem 0', overflow: 'hidden' }}>
          <button
            onClick={() => {
              // 触发设置页面切换（需要通过父组件）
              window.dispatchEvent(new CustomEvent('navigate-to-settings'));
            }}
            className="w-9 h-9 rounded-2xl bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900 transition-colors flex items-center justify-center"
            title="设置"
          >
            <svg
              className="w-4 h-4 text-black dark:text-white"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
        </div>
      )}
      </motion.div>
    </>
  );
};

/**
 * 聊天项组件
 */
interface ChatItemProps {
  chat: ChatSession;
  isSelected: boolean;
  isHovered: boolean;
  collapsed: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}

const ChatItem: React.FC<ChatItemProps> = ({
  chat,
  isSelected,
  isHovered,
  collapsed,
  onSelect,
  onDelete,
  onMouseEnter,
  onMouseLeave,
}) => {
  const getChatTitle = (chat: ChatSession): string => {
    return chat.title || "新聊天";
  };

  if (collapsed) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className={`group relative flex items-center justify-center w-9 h-9 rounded-2xl cursor-pointer transition-all ${
          isSelected
            ? "bg-white dark:bg-black"
            : "bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900"
        }`}
        onClick={onSelect}
        onMouseEnter={onMouseEnter}
        onMouseLeave={onMouseLeave}
        title={getChatTitle(chat)}
      >
        {/* 折叠状态：只显示图标 */}
        <div className="w-5 h-5 flex items-center justify-center">
          <svg
                className={`w-4 h-4 ${
              isSelected
                ? "text-black dark:text-white"
                : "text-black dark:text-white"
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
        </div>
        
        {/* 折叠状态下的删除按钮 */}
        {isHovered && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="absolute -top-1 -right-1 w-4 h-4 flex items-center justify-center rounded-full bg-red-500 text-white text-xs hover:bg-red-600 transition-colors z-10 shadow-sm"
            title="删除"
          >
            ×
          </motion.button>
        )}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={`group relative flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all ${
        isSelected
          ? "bg-white dark:bg-black"
          : "bg-white dark:bg-black hover:bg-gray-100 dark:hover:bg-gray-900"
      }`}
      onClick={onSelect}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* 聊天图标 */}
      <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
        <svg
                className={`w-4 h-4 ${
              isSelected
                ? "text-black dark:text-white"
                : "text-black dark:text-white"
            }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      </div>

      {/* 聊天标题 */}
      <div className="flex-1 min-w-0">
        <p
          className={`text-sm truncate ${
            isSelected
              ? "text-black dark:text-white font-medium"
              : "text-black dark:text-white"
          }`}
        >
          {getChatTitle(chat)}
        </p>
      </div>

      {/* 删除按钮（hover 时显示） */}
      {(isHovered || isSelected) && (
        <motion.button
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="flex-shrink-0 w-5 h-5 flex items-center justify-center rounded hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
          title="删除聊天"
        >
          <svg
            className="w-3.5 h-3.5 text-gray-500 dark:text-gray-900 hover:text-red-600 dark:hover:text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </motion.button>
      )}
    </motion.div>
  );
};
