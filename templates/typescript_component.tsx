/**
 * 组件模板：React TypeScript组件标准模板
 * 
 * 使用说明：
 * 1. 复制此模板创建新组件
 * 2. 替换组件名、Props接口和实现
 * 3. 保持代码风格一致
 */

import React, { useState, useCallback, useEffect } from 'react';

/**
 * 组件Props接口
 */
interface ComponentNameProps {
  /** 必需的prop描述 */
  requiredProp: string;
  /** 可选的prop描述 */
  optionalProp?: number;
  /** 回调函数描述 */
  onAction?: (value: string) => void;
}

/**
 * 内部状态接口（如果需要）
 */
interface ComponentState {
  loading: boolean;
  data: string | null;
  error: string | null;
}

/**
 * 组件：ComponentName
 * 
 * 功能描述：
 * - 功能1
 * - 功能2
 * 
 * @param props 组件属性
 * @returns React组件
 */
export const ComponentName: React.FC<ComponentNameProps> = ({
  requiredProp,
  optionalProp = 10,
  onAction,
}) => {
  // 状态管理
  const [state, setState] = useState<ComponentState>({
    loading: false,
    data: null,
    error: null,
  });

  // 副作用处理
  useEffect(() => {
    // 初始化逻辑
    console.log('Component mounted');
    
    return () => {
      // 清理逻辑
      console.log('Component unmounted');
    };
  }, []);

  // 事件处理函数
  const handleClick = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, loading: true, error: null }));
      
      // 执行操作
      const result = await performAction(requiredProp);
      
      setState(prev => ({ ...prev, loading: false, data: result }));
      
      // 调用回调
      onAction?.(result);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      setState(prev => ({ ...prev, loading: false, error: errorMessage }));
    }
  }, [requiredProp, onAction]);

  // 渲染
  return (
    <div className="component-name">
      <h2>{requiredProp}</h2>
      
      {state.loading && <div>加载中...</div>}
      {state.error && <div className="error">{state.error}</div>}
      {state.data && <div>{state.data}</div>}
      
      <button onClick={handleClick} disabled={state.loading}>
        执行操作
      </button>
    </div>
  );
};

/**
 * 辅助函数：执行操作
 */
async function performAction(input: string): Promise<string> {
  // 实现逻辑
  return `处理结果: ${input}`;
}
