"""RAG (Retrieval-Augmented Generation) for knowledge base"""
import json
from typing import List, Dict, Any, Optional
from loguru import logger
from app.ai.embeddings.openai import OpenAIEmbeddings, LocalEmbeddings
from app.config import settings


class KnowledgeRAG:
    """知识库 RAG 检索增强生成"""
    
    def __init__(self):
        # 尝试使用 OpenAI 嵌入，否则使用本地模型
        if settings.ai_api_key:
            self.embedding_model = OpenAIEmbeddings()
        else:
            self.embedding_model = LocalEmbeddings()
        
        self._documents: List[Dict[str, Any]] = []
        self._embeddings: List[List[float]] = []
    
    async def add_document(self, doc_id: str, content: str, metadata: Dict = None):
        """添加文档到索引"""
        embedding = await self.embedding_model.embed_documents([content])
        
        self._documents.append({
            "id": doc_id,
            "content": content,
            "metadata": metadata or {},
            "embedding": embedding[0]
        })
        self._embeddings.append(embedding[0])
        
        logger.info(f"📚 Document indexed: {doc_id} (dim: {len(embedding[0])})")
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """语义搜索"""
        query_embedding = await self.embedding_model.embed_query(query)
        results = []
        
        for i, doc in enumerate(self._documents):
            similarity = self.embedding_model.cosine_similarity(
                query_embedding, doc["embedding"]
            )
            results.append({
                "id": doc["id"],
                "content": doc["content"],
                "metadata": doc["metadata"],
                "similarity": similarity
            })
        
        # 排序并返回 Top-K
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    async def build_index(self, knowledge_data: List[Dict]):
        """构建知识库索引"""
        logger.info(f"🔄 Building knowledge index with {len(knowledge_data)} documents...")
        
        contents = [k["content"] for k in knowledge_data]
        embeddings = await self.embedding_model.embed_documents(contents)
        
        self._documents = []
        self._embeddings = embeddings
        
        for i, doc in enumerate(knowledge_data):
            self._documents.append({
                "id": doc.get("id", str(i)),
                "content": doc.get("content", ""),
                "metadata": {
                    "title": doc.get("title", ""),
                    "category": doc.get("category", ""),
                    "tags": doc.get("tags", [])
                },
                "embedding": embeddings[i]
            })
        
        logger.info(f"✅ Knowledge index built: {len(self._documents)} documents indexed")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取索引统计"""
        return {
            "total_documents": len(self._documents),
            "embedding_dimension": len(self._embeddings[0]) if self._embeddings else 0,
            "model": type(self.embedding_model).__name__
        }


# 全局单例
rag = KnowledgeRAG()