from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from enum import Enum

from fastapi import Depends
from fastapi_users.db import (
    SQLAlchemyBaseOAuthAccountTableUUID,
    SQLAlchemyBaseUserTableUUID,
    SQLAlchemyUserDatabase,
)
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum as SQLAlchemyEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    text,
    TIMESTAMP
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, relationship

from app.config import config
from app.retriver.chunks_hybrid_search import ChucksHybridSearchRetriever
from app.retriver.documents_hybrid_search import DocumentHybridSearchRetriever

DATABASE_URL = config.DATABASE_URL


class DocumentType(str, Enum):
    EXTENSION = "EXTENSION"
    CRAWLED_URL = "CRAWLED_URL"
    FILE = "FILE"
    SLACK_CONNECTOR = "SLACK_CONNECTOR"
    NOTION_CONNECTOR = "NOTION_CONNECTOR"
    YOUTUBE_VIDEO = "YOUTUBE_VIDEO"
    GITHUB_CONNECTOR = "GITHUB_CONNECTOR"

class SearchSourceConnectorType(str, Enum):
    SERPER_API = "SERPER_API"
    TAVILY_API = "TAVILY_API"
    SLACK_CONNECTOR = "SLACK_CONNECTOR"
    NOTION_CONNECTOR = "NOTION_CONNECTOR"
    GITHUB_CONNECTOR = "GITHUB_CONNECTOR"
    
class ChatType(str, Enum):
    GENERAL = "GENERAL"
    DEEP = "DEEP"
    DEEPER = "DEEPER"
    DEEPEST = "DEEPEST"
    
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    @declared_attr
    def created_at(cls):
        return Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

class BaseModel(Base):
    __abstract__ = True
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)

class Chat(BaseModel, TimestampMixin):
    __tablename__ = "chats"

    type = Column(SQLAlchemyEnum(ChatType), nullable=False)
    title = Column(String(200), nullable=False, index=True)
    initial_connectors = Column(ARRAY(String), nullable=True)
    messages = Column(JSON, nullable=False)
    
    search_space_id = Column(Integer, ForeignKey('searchspaces.id', ondelete='CASCADE'), nullable=False)
    search_space = relationship('SearchSpace', back_populates='chats')

class Document(BaseModel, TimestampMixin):
    __tablename__ = "documents"
    
    title = Column(String(200), nullable=False, index=True)
    document_type = Column(SQLAlchemyEnum(DocumentType), nullable=False)
    document_metadata = Column(JSON, nullable=True)
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(config.embedding_model_instance.dimension))
    
    search_space_id = Column(Integer, ForeignKey("searchspaces.id", ondelete='CASCADE'), nullable=False)
    search_space = relationship("SearchSpace", back_populates="documents")
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(BaseModel, TimestampMixin):
    __tablename__ = "chunks"
    
    content = Column(Text, nullable=False)
    embedding = Column(Vector(config.embedding_model_instance.dimension))
    
    document_id = Column(Integer, ForeignKey("documents.id", ondelete='CASCADE'), nullable=False)
    document = relationship("Document", back_populates="chunks")

class Podcast(BaseModel, TimestampMixin):
    __tablename__ = "podcasts"
    
    title = Column(String(200), nullable=False, index=True)
    is_generated = Column(Boolean, nullable=False, default=False)
    podcast_content = Column(Text, nullable=False, default="")
    file_location = Column(String(500), nullable=False, default="")
    
    search_space_id = Column(Integer, ForeignKey("searchspaces.id", ondelete='CASCADE'), nullable=False)
    search_space = relationship("SearchSpace", back_populates="podcasts")
    
class SearchSpace(BaseModel, TimestampMixin):
    __tablename__ = "searchspaces"
    
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="search_spaces")
    
    documents = relationship("Document", back_populates="search_space", order_by="Document.id", cascade="all, delete-orphan")
    podcasts = relationship("Podcast", back_populates="search_space", order_by="Podcast.id", cascade="all, delete-orphan")
    chats = relationship('Chat', back_populates='search_space', order_by='Chat.id', cascade="all, delete-orphan")
    
class SearchSourceConnector(BaseModel, TimestampMixin):
    __tablename__ = "search_source_connectors"
    
    name = Column(String(100), nullable=False, index=True)
    connector_type = Column(SQLAlchemyEnum(SearchSourceConnectorType), nullable=False, unique=True)
    is_indexable = Column(Boolean, nullable=False, default=False)
    last_indexed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    config = Column(JSON, nullable=False)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("user.id", ondelete='CASCADE'), nullable=False)
    user = relationship("User", back_populates="search_source_connectors")


class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship(
        "OAuthAccount", lazy="joined"
    )
    search_spaces = relationship("SearchSpace", back_populates="user")
    search_source_connectors = relationship("SearchSourceConnector", back_populates="user")


engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
        

async def setup_indexes():
    async with engine.begin() as conn:
        # Create indexes 
        # Document Summary Indexes
        await conn.execute(text('CREATE INDEX IF NOT EXISTS document_vector_index ON documents USING hnsw (embedding public.vector_cosine_ops)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS document_search_index ON documents USING gin (to_tsvector(\'english\', content))'))
        # Document Chuck Indexes
        await conn.execute(text('CREATE INDEX IF NOT EXISTS chucks_vector_index ON chunks USING hnsw (embedding public.vector_cosine_ops)'))
        await conn.execute(text('CREATE INDEX IF NOT EXISTS chucks_search_index ON chunks USING gin (to_tsvector(\'english\', content))'))

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS vector'))
        await conn.run_sync(Base.metadata.create_all)
    await setup_indexes()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
    
async def get_chucks_hybrid_search_retriever(session: AsyncSession = Depends(get_async_session)):
    return ChucksHybridSearchRetriever(session)

async def get_documents_hybrid_search_retriever(session: AsyncSession = Depends(get_async_session)):
    return DocumentHybridSearchRetriever(session)
