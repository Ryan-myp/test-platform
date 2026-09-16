"""Base embedding model interface"""
from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class BaseEmbeddingModel(ABC):
    """嵌入模型基类"""
    
    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档列表"""
        pass
    
    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """嵌入查询"""
        pass
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        import numpy as np
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    
    def find_similar(self, query: str, documents: List[dict], 
                     top_k: int = 5, threshold: float = 0.7) -> List[dict]:
        """查找相似文档"""
        query_embedding = self.embed_query(query)
        results = []
        
        for doc in documents:
            doc_embedding = doc.get("embedding")
            if doc_embedding:
                similarity = self.cosine_similarity(query_embedding, doc_embedding)
                if similarity >= threshold:
                    doc["similarity"] = similarity
                    results.append(doc)
        
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]