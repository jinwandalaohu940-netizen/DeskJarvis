"""
Semantic Intent Router

功能：
- 基于语义相似度（Embedding）的意图识别
- 替代脆弱的正则匹配
- 支持意图注册和阈值控制
"""

import logging
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from agent.core.embedding_model import SharedEmbeddingModel

logger = logging.getLogger(__name__)

@dataclass
class IntentMatch:
    intent_type: str
    confidence: float
    metadata: Dict[str, Any]
    is_fast_path: bool

class IntentRouter:
    """
    语义意图路由器
    """
    
    def __init__(self, embedding_model: SharedEmbeddingModel):
        self.embedding_model = embedding_model
        
        # 预定义意图库 (Canonical Examples)
        # 意图类型 -> [示例列表]
        self.intent_registry = {
            # 文本处理类
            "translate": [
                "Translate this to English", "翻译这段话", "How do you say X in Chinese?",
                "Translate the following text", "把这个翻译成英文", "英文翻译"
            ],
            "summarize": [
                "Summarize this text", "总结一下这段话", "Give me a summary",
                "概括核心内容", "提炼要点"
            ],
            "polish": [
                "Polish this text", "润色一下这段文字", "Make this sound more professional",
                "优化这段话的表达", "修改语法错误"
            ],
            
            # 系统操作类
            "screenshot": [
                "Take a screenshot", "Capture the screen", "截个图", "截屏",
                "Screenshot the desktop", "保存屏幕截图"
            ],
            "volume_control": [
                "Turn up the volume", "Mute the sound", "Volume down",
                "调大音量", "静音", "声音小一点"
            ],
            "brightness_control": [
                "Increase brightness", "Dim the screen", "Set brightness to 50%",
                "调亮屏幕", "屏幕太暗了", "亮度调高点"
            ],
            "system_info": [
                "Check disk usage", "Show battery status", "System information",
                "查看系统信息", "内存还剩多少", "电池状态"
            ],
            
            # 常见应用操作 (简单打开/关闭)
            "app_open": [
                "Open Safari", "Launch Calculator", "Open Discord",
                "打开浏览器", "启动计算器", "打开微信"
            ],
             "app_close": [
                "Close Safari", "Quit Music", "Kill the process",
                "关闭浏览器", "退出音乐", "关闭应用"
            ],
        }
        
        # 意图对应的元数据（处理函数映射等）
        self.intent_metadata = {
            "translate": {"type": "text_process", "action": "translate"},
            "summarize": {"type": "text_process", "action": "summarize"},
            "polish": {"type": "text_process", "action": "polish"},
            "screenshot": {"type": "screenshot_desktop", "action": "screenshot"},
            "volume_control": {"type": "system_control", "action": "volume"},
            "brightness_control": {"type": "system_control", "action": "brightness"},
            "system_info": {"type": "system_control", "action": "sys_info"},
            "app_open": {"type": "open_app", "action": "open"},
            "app_close": {"type": "close_app", "action": "close"},
        }
        
        # 缓存意图的 Embeddings
        self.intent_embeddings: Dict[str, np.ndarray] = {}
        self._cache_embeddings()

    def _cache_embeddings(self):
        """预计算意图示例的 Embeddings"""
        if not self.embedding_model.wait_until_ready(timeout=0.1):
            # 如果模型未就绪，首次推理时会尝试加载
            # 但这里我们希望在后台线程加载完后再计算，避免阻塞初始化
            # 可以通过 SharedEmbeddingModel 的 lazy load 特性解决
            return

        for intent, examples in self.intent_registry.items():
            embeddings = []
            for ex in examples:
                vec = self.embedding_model.encode(ex)
                if vec:
                    embeddings.append(vec)
            if embeddings:
                self.intent_embeddings[intent] = np.array(embeddings)
                
    def _cosine_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """计算余弦相似度"""
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return np.dot(v1, v2) / (norm1 * norm2)

    def detect(self, text: str, threshold: float = 0.65) -> Optional[IntentMatch]:
        """
        检测意图
        
        Args:
            text: 用户输入的指令
            threshold: 相似度阈值
            
        Returns:
            IntentMatch (如果匹配成功) 或 None
        """
        # 1. 简单预处理
        text = text.strip()
        if not text:
            return None
            
        # 2. 获取输入文本的 Embedding
        if not self.intent_embeddings:
             # 尝试补初始化
             self._cache_embeddings()
             
        # 如果模型还没好，降级到 None（走通用规划）
        if not self.intent_embeddings:
            logger.warning("[IntentRouter] 意图库 Embeddings 未就绪，跳过语义路由")
            return None
            
        query_vec = self.embedding_model.encode(text)
        if not query_vec:
            return None # 模型出错
            
        query_vec = np.array(query_vec)
        
        best_intent = None
        best_score = -1.0
        
        # 3. 计算与所有意图簇的相似度（取最大值）
        for intent, example_vecs in self.intent_embeddings.items():
            # 计算 query 与该意图所有示例的相似度，取最大值
            # 向量化计算: dot product
            # example_vecs shape: (N, D)
            # query_vec shape: (D,)
            
            # 归一化
            query_norm = np.linalg.norm(query_vec)
            example_norms = np.linalg.norm(example_vecs, axis=1)
            
            dots = np.dot(example_vecs, query_vec)
            if query_norm == 0:
                scores = np.zeros(len(dots))
            else:
                scores = dots / (example_norms * query_norm)
                
            max_score = np.max(scores)
            
            if max_score > best_score:
                best_score = max_score
                best_intent = intent
                
        logger.info(f"[IntentRouter] 最佳匹配: {best_intent} (Score: {best_score:.2f})")
        
        # 4. 阈值判断
        if best_score >= threshold:
            meta = self.intent_metadata.get(best_intent, {})
            return IntentMatch(
                intent_type=best_intent,
                confidence=float(best_score),
                metadata=meta,
                is_fast_path=True # 目前注册的都是 Fast Path 意图
            )
            
        return None
