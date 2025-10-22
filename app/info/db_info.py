"""
This module handles the database connection and session management for the FastAPI application.
"""
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import Column, String, DateTime, Boolean, Text, Date, Integer
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


# class AuditsConcatenated(Base):
#     """
#     Stores extracted KPIs/values from uploaded audit PDFs.
#     """
#     __tablename__ = "ft_audits_concatanated"
#     __table_args__ = {"schema": "users"}

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     filename = Column(String(300) )
#     statistic = Column(String(500) )
#     value = Column(String(500) )
#     upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
#     file_id = Column(UUID(as_uuid=True) )  # link back to uploaded file if needed
#     chat_id = Column(UUID(as_uuid=True) )




class CombinedAudit(Base):
    """
    Represents a single, combined table containing both dealer audit statistics
    and the detailed question/answer data from the audit.
    """
    __tablename__ = "ft_combined_audits"
    __table_args__ = {"schema": "users"}

    # --- Common Columns (De-duplicated) ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = Column(String(300))
    file_id = Column(UUID(as_uuid=True))
    chat_id = Column(UUID(as_uuid=True))
    upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    country = Column(String(50))
    dealer_name = Column(String(50))
    dealer_code = Column(String(50))
    address_full = Column(String(250))
    rrg = Column(String(50))
    renault_sales_per_year = Column(String(50))
    dacia_sales_per_year = Column(String(50))
    workshop_customers_per_day = Column(String(50))
    global_score = Column(String(50))
    auditor = Column(String(50))
    audit_date = Column(String(50))
    new_vehicle_activity = Column(String(50))
    aftersales_activity = Column(String(50))
    appointment_booking_per_preparation = Column(String(50))
    customer_journey = Column(String(50))
    product_presentation = Column(String(50))
    reception = Column(String(50))
    order_management = Column(String(50))
    production = Column(String(50))
    preperation_per_delivery = Column(String(50))
    restitution = Column(String(50))
    new_vehicle_activity_management = Column(String(50))
    aftersales_activity_management = Column(String(50))
    basics_sales_methods = Column(String(50))
    brand_store_renault = Column(String(50))
    basics_aftersales_methods = Column(String(50))
    flash_ares_maintainence = Column(String(50))
    digital_renault = Column(String(50))
    journey_experience_renault = Column(String(50))
    website_conformity_renault = Column(String(50))
    brand_store_dacia = Column(String(50))
    digital_dacia = Column(String(50))
    journey_experience_dacia = Column(String(50))
    website_conformity_dacia = Column(String(50))
    digital_score = Column(String(50))


    q1 = Column(String(500))
    q2 = Column(String(500))
    q3 = Column(String(500))
    q4 = Column(String(500))
    q5 = Column(String(500))
    q6 = Column(String(500))
    q7 = Column(String(500))
    q8 = Column(String(500))
    q9 = Column(String(500))
    q10 = Column(String(500))
    q11 = Column(String(500))
    q12 = Column(String(500))
    q13 = Column(String(500))
    q14 = Column(String(500))
    q15 = Column(String(500))
    q16 = Column(String(500))
    q17 = Column(String(500))
    q18 = Column(String(500))
    q19 = Column(String(500))
    q20 = Column(String(500))
    q21 = Column(String(500))
    q22 = Column(String(500))
    q23 = Column(String(500))
    q24 = Column(String(500))
    q25 = Column(String(500))
    q26 = Column(String(500))
    q27 = Column(String(500))
    q28 = Column(String(500))
    q29 = Column(String(500))
    q30 = Column(String(500))
    q31 = Column(String(500))
    q32 = Column(String(500))
    q33 = Column(String(500))
    q34 = Column(String(500))
    q35 = Column(String(500))
    q36 = Column(String(500))
    q37 = Column(String(500))
    q38 = Column(String(500))
    q39 = Column(String(500))
    q40 = Column(String(500))
    q41 = Column(String(500))
    q42 = Column(String(500))
    q43 = Column(String(500))
    q44 = Column(String(500))
    q45 = Column(String(500))
    q46 = Column(String(500))
    q47 = Column(String(500))
    q48 = Column(String(500))
    q49 = Column(String(500))
    q50 = Column(String(500))
    q51 = Column(String(500))
    q52 = Column(String(500))
    q53 = Column(String(500))
    q54 = Column(String(500))
    q55 = Column(String(500))
    q56 = Column(String(500))
    q57 = Column(String(500))
    q58 = Column(String(500))
    q59 = Column(String(500))
    q60 = Column(String(500))
    q61 = Column(String(500))
    q62 = Column(String(500))
    q63 = Column(String(500))
    q64 = Column(String(500))
    q65 = Column(String(500))
    q66 = Column(String(500))
    q67 = Column(String(500))
    q68 = Column(String(500))
    q69 = Column(String(500))
    q70 = Column(String(500))
    q71 = Column(String(500))
    q72 = Column(String(500))
    q73 = Column(String(500))
    q74 = Column(String(500))
    q75 = Column(String(500))
    q76 = Column(String(500))
    q77 = Column(String(500))
    q78 = Column(String(500))
    q79 = Column(String(500))
    q80 = Column(String(500))
    q81 = Column(String(500))
    q82 = Column(String(500))
    q83 = Column(String(500))
    q84 = Column(String(500))
    q85 = Column(String(500))
    q86 = Column(String(500))
    q87 = Column(String(500))
    q88 = Column(String(500))
    q89 = Column(String(500))
    q90 = Column(String(500))
    q91 = Column(String(500))
    q92 = Column(String(500))
    q93 = Column(String(500))
    q94 = Column(String(500))
    q95 = Column(String(500))
    q96 = Column(String(500))
    q97 = Column(String(500))
    q98 = Column(String(500))
    q99 = Column(String(500))
    q100 = Column(String(500))
    q101 = Column(String(500))
    q102 = Column(String(500))
    q103 = Column(String(500))
    q104 = Column(String(500))
    q105 = Column(String(500))
    q106 = Column(String(500))
    q107 = Column(String(500))
    q108 = Column(String(500))
    q109 = Column(String(500))
    q110 = Column(String(500))
    q111 = Column(String(500))
    q112 = Column(String(500))
    q113 = Column(String(500))
    q114 = Column(String(500))
    q115 = Column(String(500))
    q116 = Column(String(500))
    q117 = Column(String(500))
    q118 = Column(String(500))
    q119 = Column(String(500))
    q120 = Column(String(500))
    q121 = Column(String(500))
    
    ok_count = Column(Integer)
    ko_count = Column(Integer)



class QuestionsMetadata(Base):
    """
    Represents the mapping of question codes to their full text, tags, and subtags.
    Maps to the 'ft_questions_metadata' table in the 'users' schema.
    """
    __tablename__ = "ft_questions_metadata"
    __table_args__ = {"schema": "users"}

    question = Column(Text, nullable=False)
    tag_1 = Column(String(255))
    subtag_1 = Column(String(255))
    mapping = Column(String(10), primary_key=True, nullable=False, unique=True)


# class DealerStats(Base):
#     """
#     Represents individual dealer statistics from an audit report.
#     Maps to the 'dealer_stats' table in the 'users' schema.
#     """
#     __tablename__ = "dealer_stats"
#     __table_args__ = {"schema": "users"}

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     statistic = Column(Text)
#     value = Column(Text)
#     dealer_name = Column(String(255))
#     dealer_code = Column(String(50))
#     country = Column(String(100))
#     address_full = Column(Text)
#     file_name = Column(Text)
#     file_id = Column(UUID(as_uuid=True))
#     chat_id = Column(UUID(as_uuid=True))
#     upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
#     auditor = Column(String(255))

# class DealerQaStats(Base):
#     """
#     Represents question and answer details from a dealer audit report.
#     Maps to the 'dealer_qa_stats' table in the 'users' schema.
#     """
#     __tablename__ = "dealer_qa_stats"
#     __table_args__ = {"schema": "users"}

#     id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
#     dealer_name = Column(String(255))
#     dealer_code = Column(String(50))
#     file_name = Column(Text)
#     country = Column(String(100))
#     auditor = Column(String(255))
#     question = Column(Text)
#     answer = Column(Text)
#     upload_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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
