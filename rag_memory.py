# rag_memory.py
import chromadb
from sentence_transformers import SentenceTransformer
from typing import List, Optional
import uuid
import os


class RAGMemory:
    def __init__(self, persist_dir="rag_db"):
        """Initialize RAG memory with modern ChromaDB configuration"""
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Ensure the persist directory exists
        os.makedirs(persist_dir, exist_ok=True)

        # Modern ChromaDB client initialization
        self.client = chromadb.PersistentClient(path=persist_dir)

        # Get or create collection with modern API
        self.collection = self.client.get_or_create_collection(
            name="chat_memory",
            metadata={"hnsw:space": "cosine"}  # Optional: specify distance metric
        )

    def add_message(self, message: str, role: str = "user"):
        """Add a message to the memory store"""
        try:
            embedding = self.model.encode(message).tolist()
            doc_id = str(uuid.uuid4())

            self.collection.add(
                documents=[message],
                embeddings=[embedding],
                metadatas=[{"role": role}],
                ids=[doc_id]
            )
            print(f"✅ Added {role} message to memory (ID: {doc_id[:8]}...)")

        except Exception as e:
            print(f"❌ Error adding message to memory: {e}")

    def query(self, prompt: str, top_k: int = 5, role: Optional[str] = None) -> List[str]:
        """Query the memory store for relevant messages"""
        try:
            embedding = self.model.encode(prompt).tolist()

            # Build where clause for filtering by role
            where_clause = {"role": role} if role else None

            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=min(top_k, self.collection.count()),  # Don't query more than available
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )

            if results["documents"] and results["documents"][0]:
                documents = results["documents"][0]
                distances = results["distances"][0]

                # Filter out very dissimilar results (optional)
                filtered_docs = []
                for doc, distance in zip(documents, distances):
                    if distance < 1.0:  # Adjust threshold as needed
                        filtered_docs.append(doc)

                print(f"🔍 Found {len(filtered_docs)} relevant memories for query")
                return filtered_docs

            return []

        except Exception as e:
            print(f"❌ Error querying memory: {e}")
            return []

    def get_recent_messages(self, count: int = 10, role: Optional[str] = None) -> List[str]:
        """Get recent messages from memory"""
        try:
            where_clause = {"role": role} if role else None

            # Get all documents first (ChromaDB doesn't have direct ordering by time)
            results = self.collection.get(
                where=where_clause,
                include=["documents", "metadatas"]
            )

            if results["documents"]:
                # Return the last 'count' messages
                return results["documents"][-count:] if len(results["documents"]) > count else results["documents"]

            return []

        except Exception as e:
            print(f"❌ Error getting recent messages: {e}")
            return []

    def count_messages(self, role: Optional[str] = None) -> int:
        """Count total messages in memory"""
        try:
            if role:
                results = self.collection.get(
                    where={"role": role},
                    include=[]  # Don't include documents, just count
                )
                return len(results["ids"])
            else:
                return self.collection.count()

        except Exception as e:
            print(f"❌ Error counting messages: {e}")
            return 0

    def clear(self):
        """Clear all memory"""
        try:
            # Delete the collection
            self.client.delete_collection("chat_memory")

            # Recreate it
            self.collection = self.client.get_or_create_collection(
                name="chat_memory",
                metadata={"hnsw:space": "cosine"}
            )

            print("🗑️ Memory cleared successfully")

        except Exception as e:
            print(f"❌ Error clearing memory: {e}")

    def get_memory_stats(self) -> dict:
        """Get statistics about the memory store"""
        try:
            total_messages = self.count_messages()
            user_messages = self.count_messages("user")
            ai_messages = self.count_messages("ai")

            return {
                "total_messages": total_messages,
                "user_messages": user_messages,
                "ai_messages": ai_messages,
                "collection_name": self.collection.name
            }

        except Exception as e:
            print(f"❌ Error getting memory stats: {e}")
            return {}

    def search_by_keyword(self, keyword: str, top_k: int = 5) -> List[str]:
        """Search for messages containing specific keywords"""
        try:
            # Use text-based search
            results = self.collection.get(
                include=["documents", "metadatas"]
            )

            if results["documents"]:
                # Filter documents containing the keyword
                matching_docs = []
                for doc in results["documents"]:
                    if keyword.lower() in doc.lower():
                        matching_docs.append(doc)
                        if len(matching_docs) >= top_k:
                            break

                print(f"🔍 Found {len(matching_docs)} messages containing '{keyword}'")
                return matching_docs

            return []

        except Exception as e:
            print(f"❌ Error searching by keyword: {e}")
            return []

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            # Modern ChromaDB handles persistence automatically
            pass
        except:
            pass