import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), default="application/pdf")
    file_size = Column(Integer, default=0)
    status = Column(String(50), default="indexed")  # 'uploading', 'processing', 'indexing', 'indexed', 'failed'
    chunk_count = Column(Integer, default=0)
    product_name = Column(String(255), nullable=True)   # Auto-detected product name from document
    category = Column(String(100), nullable=True)        # Auto-detected product category
    summary = Column(Text, nullable=True)                # Auto-generated document summary
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0)
    page_number = Column(Integer, nullable=True)         # Which PDF page this chunk came from
    section_title = Column(String(255), nullable=True)   # Detected section heading (e.g. "Specifications")
    product_name = Column(String(255), nullable=True)    # Detected product name
    category = Column(String(100), nullable=True)        # Detected product category
    source = Column(String(255), nullable=True)          # Document source identifier
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
