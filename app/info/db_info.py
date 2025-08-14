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