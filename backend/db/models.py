"""
BRANE Database Models
SQLAlchemy ORM models for PostgreSQL
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum


Base = declarative_base()


def generate_uuid():
    """Generate UUID for primary keys"""
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    USER = "user"
    AUDITOR = "auditor"


class PrivacyTier(int, enum.Enum):
    """Privacy tiers for data processing"""
    LOCAL = 0  # On-premise, no data leaves infrastructure
    PRIVATE_CLOUD = 1  # Encrypted private cloud (HIPAA compliant)
    PUBLIC_API = 2  # Public LLM APIs (no PHI/PII)


class User(Base):
    """User accounts (authenticated via Google OAuth)"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String)
    picture = Column(String)  # Google profile picture URL
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

    # Preferences
    preferences = Column(JSON, default=dict)  # {theme: 'dark', default_neuron: '...'}

    # Relationships
    neurons = relationship("Neuron", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


class Neuron(Base):
    """AI Agent (Neuron) instances"""
    __tablename__ = "neurons"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    description = Column(Text)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    # Configuration
    config = Column(JSON, nullable=False)  # Full YAML config as JSON
    privacy_tier = Column(Enum(PrivacyTier), default=PrivacyTier.LOCAL, nullable=False)

    # State
    is_active = Column(Boolean, default=True, nullable=False)
    status = Column(String, default="idle")  # idle, thinking, executing, error

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used = Column(DateTime)

    # Stats
    total_interactions = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Relationships
    owner = relationship("User", back_populates="neurons")
    sessions = relationship("ChatSession", back_populates="neuron", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Neuron {self.name} (Tier {self.privacy_tier})>"


class ChatSession(Base):
    """Chat conversation sessions"""
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    neuron_id = Column(String, ForeignKey("neurons.id"), nullable=False)

    title = Column(String, default="New Conversation")

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Stats
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="sessions")
    neuron = relationship("Neuron", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession {self.title}>"


class Message(Base):
    """Individual chat messages"""
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=generate_uuid)
    session_id = Column(String, ForeignKey("chat_sessions.id"), nullable=False)

    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Metadata
    privacy_tier = Column(Enum(PrivacyTier), nullable=False)
    model_used = Column(String)  # e.g., "gpt-4", "claude-3-sonnet"
    tokens = Column(Integer, default=0)
    latency_ms = Column(Integer)  # Response time in milliseconds

    # Tool calling
    tool_calls = Column(JSON)  # Array of tool calls made
    tool_results = Column(JSON)  # Results from tool executions

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<Message {self.role}: {self.content[:50]}...>"


class AuditLog(Base):
    """Immutable audit logs for compliance (HIPAA/GDPR)"""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    neuron_id = Column(String, ForeignKey("neurons.id"))

    # Event details
    event_type = Column(String, nullable=False, index=True)  # auth, chat, config_change, data_access, etc.
    action = Column(String, nullable=False)  # login, send_message, update_neuron, etc.
    resource = Column(String)  # Resource affected (neuron_id, document_id, etc.)

    # Result
    result = Column(String, nullable=False)  # success, failure
    error_message = Column(Text)  # If result=failure

    # Context
    details = Column(JSON)  # Additional event-specific data
    ip_address = Column(String)
    user_agent = Column(String)

    # Cryptographic signature (for immutability)
    signature = Column(String, nullable=False)  # SHA-256 HMAC

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog {self.event_type}/{self.action} by {self.user_id}>"


class Document(Base):
    """Documents stored in Axon (RAG memory)"""
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    neuron_id = Column(String, ForeignKey("neurons.id"), nullable=False)

    # Content
    title = Column(String)
    content = Column(Text, nullable=False)
    source = Column(String)  # file path, URL, etc.

    # Metadata
    doc_metadata = Column("metadata", JSON, default=dict)  # Custom metadata (column name "metadata", attribute name "doc_metadata")
    privacy_tier = Column(Enum(PrivacyTier), nullable=False)

    # Embedding info
    embedding_model = Column(String)  # Model used for embeddings
    chunk_count = Column(Integer, default=1)

    # Storage
    vector_store_path = Column(String)  # Path to FAISS index file

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Document {self.title}>"
