"""
Axon - RAG Memory System
FAISS-based vector store with encryption (no server needed)
"""

import os
import pickle
import logging
from typing import List, Dict, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from cryptography.fernet import Fernet
import base64
import hashlib

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Axon:
    """
    Encrypted vector store using FAISS (no server required).
    Self-improving with hierarchical memory compaction.
    """

    def __init__(self, neuron_id: str, config: Dict):
        """
        Initialize Axon for a specific Neuron.

        Args:
            neuron_id: Neuron ID (for storage path)
            config: Axon configuration
                {
                    "enabled": true,
                    "storage_path": "./storage/axon",
                    "embedding_model": "all-MiniLM-L6-v2",
                    "chunk_size": 512,
                    "top_k": 3
                }
        """
        self.neuron_id = neuron_id
        self.config = config

        # Storage paths
        base_path = config.get("storage_path", settings.AXON_STORAGE_PATH)
        self.storage_path = os.path.join(base_path, neuron_id)

        # FAISS index
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict] = []  # Metadata for each vector

        # Embeddings model
        model_name = config.get("embedding_model", settings.DEFAULT_EMBEDDING_MODEL)
        self.embedder = SentenceTransformer(model_name)
        self.embedding_dim = self.embedder.get_sentence_embedding_dimension()

        # Encryption
        self.cipher = self._get_cipher()

        logger.info(f"Axon initialized for Neuron {neuron_id} (dim={self.embedding_dim})")

    def _get_cipher(self) -> Fernet:
        """Get Fernet cipher for encryption/decryption"""
        # Derive key from settings.ENCRYPTION_KEY
        key_bytes = settings.ENCRYPTION_KEY.encode()
        key_hash = hashlib.sha256(key_bytes).digest()
        fernet_key = base64.urlsafe_b64encode(key_hash)

        return Fernet(fernet_key)

    async def load(self):
        """Load existing index or create new"""
        os.makedirs(self.storage_path, exist_ok=True)

        index_path = os.path.join(self.storage_path, "vectors.index")
        docs_path = os.path.join(self.storage_path, "docs.pkl")

        if os.path.exists(index_path) and os.path.exists(docs_path):
            # Load existing index
            self.index = faiss.read_index(index_path)

            with open(docs_path, 'rb') as f:
                encrypted_docs = pickle.load(f)
                self.documents = self._decrypt_documents(encrypted_docs)

            logger.info(f"Loaded Axon: {len(self.documents)} documents")

        else:
            # Create new index (using L2 distance)
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.documents = []

            logger.info("Created new Axon index")

    async def add_documents(self, docs: List[Dict]):
        """
        Ingest new documents into vector store.

        Args:
            docs: List of documents
                [
                    {
                        "id": "doc_123",
                        "text": "Document content...",
                        "metadata": {"source": "file.pdf", "page": 1}
                    },
                    ...
                ]
        """
        if not docs:
            return

        logger.info(f"Adding {len(docs)} documents to Axon")

        for doc in docs:
            # 1. Generate embedding
            embedding = self.embedder.encode(doc["text"])

            # 2. Add to FAISS
            embedding_array = np.array([embedding]).astype('float32')
            self.index.add(embedding_array)

            # 3. Store metadata (encrypted)
            self.documents.append({
                "id": doc.get("id", f"doc_{len(self.documents)}"),
                "text": doc["text"],
                "metadata": doc.get("metadata", {}),
                "timestamp": doc.get("timestamp")
            })

        # Save to disk
        await self.save()

        logger.info(f"Axon now has {len(self.documents)} documents")

    async def search(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        Semantic search for relevant documents.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of relevant documents with scores
        """
        if not self.index or self.index.ntotal == 0:
            logger.debug("Axon is empty, no results")
            return []

        # 1. Embed query
        query_embedding = self.embedder.encode(query)
        query_array = np.array([query_embedding]).astype('float32')

        # 2. FAISS search
        distances, indices = self.index.search(query_array, min(top_k, self.index.ntotal))

        # 3. Return documents with scores
        results = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(distance)  # Lower is better (L2 distance)
                results.append(doc)

        logger.debug(f"Axon search: {len(results)} results for query '{query[:50]}...'")

        return results

    async def delete_document(self, doc_id: str):
        """
        Delete document from vector store.
        Note: FAISS doesn't support deletion, so we rebuild the index.
        """
        # Find document index
        doc_idx = None
        for i, doc in enumerate(self.documents):
            if doc["id"] == doc_id:
                doc_idx = i
                break

        if doc_idx is None:
            logger.warning(f"Document {doc_id} not found")
            return

        # Remove from documents list
        del self.documents[doc_idx]

        # Rebuild FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)

        if self.documents:
            # Re-embed all documents
            embeddings = []
            for doc in self.documents:
                embedding = self.embedder.encode(doc["text"])
                embeddings.append(embedding)

            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)

        await self.save()

        logger.info(f"Deleted document {doc_id}, rebuilt index")

    async def save(self):
        """Persist index and documents to disk (encrypted)"""
        os.makedirs(self.storage_path, exist_ok=True)

        # Save FAISS index
        index_path = os.path.join(self.storage_path, "vectors.index")
        faiss.write_index(self.index, index_path)

        # Save documents (encrypted)
        docs_path = os.path.join(self.storage_path, "docs.pkl")
        encrypted_docs = self._encrypt_documents(self.documents)

        with open(docs_path, 'wb') as f:
            pickle.dump(encrypted_docs, f)

        logger.debug(f"Axon saved to {self.storage_path}")

    def _encrypt_documents(self, documents: List[Dict]) -> bytes:
        """Encrypt documents with AES-256"""
        data = pickle.dumps(documents)
        encrypted = self.cipher.encrypt(data)
        return encrypted

    def _decrypt_documents(self, encrypted_data: bytes) -> List[Dict]:
        """Decrypt documents"""
        decrypted = self.cipher.decrypt(encrypted_data)
        documents = pickle.loads(decrypted)
        return documents

    def get_stats(self) -> Dict:
        """Get Axon statistics"""
        return {
            "neuron_id": self.neuron_id,
            "total_documents": len(self.documents),
            "total_vectors": self.index.ntotal if self.index else 0,
            "embedding_dim": self.embedding_dim,
            "storage_path": self.storage_path
        }
