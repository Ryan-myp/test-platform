"""OpenAI-compatible embeddings"""
import os
import json
from typing import List, Optional
import httpx
from loguru import logger
from app.ai.embeddings.base import BaseEmbeddingModel
from app.config import settings


class OpenAIEmbeddings(BaseEmbeddingModel):
    """OpenAI 兼容的嵌入模型"""
    
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.api_key = settings.ai_api_key
        self.base_url = settings.ai_base_url.rstrip('/')
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """嵌入文档"""
        embeddings = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(texts), 100):  # 批量处理
                batch = texts[i:i+100]
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": self.model,
                        "input": batch
                    }
                )
                response.raise_for_status()
                data = response.json()
                embeddings.extend([item["embedding"] for item in data["data"]])
        
        return embeddings
    
    async def embed_query(self, text: str) -> List[float]:
        """嵌入查询"""
        return (await self.embed_documents([text]))[0]
    
    async def get_dimension(self) -> int:
        """获取向量维度"""
        test_embedding = await self.embed_query("test")
        return len(test_embedding)


class LocalEmbeddings(BaseEmbeddingModel):
    """本地嵌入模型（使用简单的词袋模型作为fallback）"""
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._hash_table = {}
    
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """使用哈希生成固定维度的向量"""
        embeddings = []
        for text in texts:
            embedding = self._hash_to_vector(text)
            embeddings.append(embedding)
        return embeddings
    
    async def embed_query(self, text: str) -> List[float]:
        return (await self.embed_documents([text]))[0]
    
    def _hash_to_vector(self, text: str) -> List[float]:
        """将文本映射为固定维度向量"""
        import hashlib
        vector = [0.0] * self.dimension
        
        # 使用 n-gram 哈希
        for n in range(2, 5):
            for i in range(len(text) - n + 1):
                ngram = text[i:i+n]
                hash_val = int(hashlib.md5(ngram.encode()).hexdigest(), 16)
                idx = hash_val % self.dimension
                vector[idx] += 1.0
        
        # 归一化
        norm = sum(v*v for v in vector) ** 0.5
        if norm > 0:
            vector = [v/norm for v in vector]
        
        return vector