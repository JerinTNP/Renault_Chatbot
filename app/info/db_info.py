"""
This module handles the database connection and session management for the FastAPI application.
"""
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, DateTime, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone

from app.exception import InternalError
from app.logger import logging
from app.utils import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=10,          
    max_overflow=20,    
    pool_timeout=30,        
)

Base = declarative_base()					 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency to get the database session

# For FastAPI route handlers (generator)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class FileInfo(Base):
    """
    Represents information stored in the 'ft_files_info' table within the 'filemanagement' schema.
    This class maps to a database table that stores embedded file information.
    """
    __tablename__ = "ft_files_info"
    __table_args__ = {"schema": "file_management"}
 
    file_name = Column(String(255))
    file_path = Column(String(500))
    link_uri = Column(String(500))
    upload_date = Column(Date)
    gu_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    embed_done = Column(Boolean)
    source = Column(String(255))


class ChatInfo(Base):
    """
    Represents a chat history record in the 'ft_chat_history' table within the 'users' schema.
    This class maps to a database table that stores essential details about chat history.

    """

    __tablename__ = "ft_chat_history"
    __table_args__ = {"schema": "users"}

    chat_id = Column(UUID(as_uuid=True),primary_key=True)
    chat_type = Column(String(100))
    access_date = Column(DateTime())
    chat = Column(Text)
    chat_title = Column(Text)
    chat_history = Column(Text)
    chat_title_set = Column(Boolean)


class UploadFileInfo(Base):
    """
    Represents a chat history record of uploaded file in the 'ft_uploaded_files' table within the 'users' schema.
    This class maps to a database table that stores essential details about chat history of uploaded file.
    """
    
    __tablename__ = "ft_uploaded_files"
    __table_args__ = {"schema": "users"}

    chat_id = Column(UUID(as_uuid=True),primary_key=True)
    file_id = Column(UUID(as_uuid=True))
    chat_type = Column(String(100))
    upload_date = Column(DateTime())
    file_name = Column(String(300))
    file_path = Column(String(500))
    file_size = Column(String(150))
    link_uri = Column(String(500))
    requirement = Column(Text)
    istext_flag = Column(Boolean)
    search_details = Column(Text)


class AuditsConcatenated(Base):
    """
    Stores extracted KPIs/values from uploaded audit PDFs.
    """
    __tablename__ = "ft_audits_concatanated"
    __table_args__ = {"schema": "users"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(300) )
    statistic = Column(String(500) )
    value = Column(String(500) )
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    file_id = Column(UUID(as_uuid=True) )  # link back to uploaded file if needed
    chat_id = Column(UUID(as_uuid=True) )

def init_db():
    """
    Initializes the database by creating all tables defined in the SQLAlchemy models.
 
    This function checks if each table already exists in the connected database.
    If a table does not exist, it creates it. If it already exists, it is left unchanged.
    Useful for ensuring the necessary schema is in place during application startup.
    """
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logging.info("Database tables checked and created if not existing.")
    except Exception as e:
        logging.error(f"Failed to initialize the database: {e}")
        raise InternalError("An error occurred while initializing the database: " + str(e))
