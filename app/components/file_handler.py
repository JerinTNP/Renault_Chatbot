"""
File Handler Module  
This module manages the upload of PDF files to SharePoint, creates unique folders for each file,  
and processes the files by embedding their content into a FAISS vector database for retrieval and search.
"""
 
import os
import sys
import uuid
from pydantic import UUID4
import json
from datetime import datetime,timezone
from fastapi import UploadFile
from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential
from app.models.vectorstore import FAISS_DB
from app.info import db_info
from app.components.embedder import DATA_LOADER_SP
from app.info.sharepoint_info import (
    SITE_URL, CLIENT_ID, CLIENT_SECRET, SP_LIBRARY_TITLE, 
    SP_LIBRARY_TITLE_UP, SHAREPOINT_URL, SP_RENAULT
)
from app.utils import EMBEDDINGS, RENAULT_DB, PERSIST_DIRECTORY

from app.logger import logging
from app.exception import get_error_message_detail
from sqlalchemy.orm import Session

from app.exception import InternalError

def get_sharepoint_context(
        base_url: str = SITE_URL,
        client_id: str = CLIENT_ID,
        client_secret: str = CLIENT_SECRET
) -> ClientContext:
    """
    Authenticate and return a SharePoint ClientContext instance.
 
    Parameters:
        base_url (str): Absolute Web or Site Url.
        client_id (str): Client credential.
        client_secret (str): Client credential.
   
    Returns:
        ClientContext: Authenticated SharePoint context.
   
    Raises:
        HTTPException: If authentication fails.
    """
    try:
        ctx = ClientContext(base_url).with_credentials(ClientCredential(client_id, client_secret))
        logging.info("Successfully connected to SharePoint")
        return ctx
 
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Failed to authenticate SharePoint: {error_message}")
        raise InternalError("SharePoint authentication failed: " + str(e))


async def upload_file_to_sharepoint(
        file: UploadFile, 
        chat_type: str,
        db: Session,
        chatid: UUID4 = None,

        ) -> dict: 
    """
    Uploads a PDF file to SharePoint under a dynamically created folder.
    
    Parameters:
        file (UploadFile): The PDF file to be uploaded.
        chat_type (str): Type of the chat for which chat session is created.
        db (Session): Postgresql session.
    
    Returns:
        (dict): The dict contains success message, chat ID, and uploaded file URL.
    
    Raises:
        HTTPException: When upload fails.
    """
    try:
        logging.info(f"Received file upload request: {file.filename}")

        ctx = get_sharepoint_context()
        uploads_folder_path = f"{SP_LIBRARY_TITLE_UP}/{SP_RENAULT}"
        uploads_folder = ctx.web.get_folder_by_server_relative_url(uploads_folder_path)
        ctx.load(uploads_folder)
        ctx.execute_query()
        logging.info("Verified existence of 'Uploads' folder")

        folder_path = f"{uploads_folder_path}/{chatid}"
        logging.info(f"Generated unique folder name: {chatid}")

        new_folder = ctx.web.folders.add(folder_path).execute_query()
        logging.info(f"Created new folder: {folder_path}")

        file_data = await file.read()
        file_url = f"{folder_path}/{file.filename}"
        
        folder = ctx.web.get_folder_by_server_relative_url(folder_path)
        folder.files.add(file.filename, file_data, True).execute_query()
        logging.info(f"Successfully uploaded PDF file: {file.filename} to {folder_path}")

        file_path = f"{SITE_URL}/{file_url}"
        file_path = file_path.replace(" ","%20")
        print(f"file_path : {file_path}")

        gu_id = str(uuid.uuid4())

        upload_entry = db_info.UploadFileInfo(
                        chat_id=chatid,
                        file_id=gu_id,
                        chat_type=chat_type,
                        upload_date=datetime.now(timezone.utc),
                        file_name=file.filename,
                        file_path=str(file_path),
                        file_size = file.size
                    )
        db.add(upload_entry)
        # db.commit()
        # db.refresh(upload_entry)

        logging.info("Uploaded file data added to Uploaded_File_Info table")

        chat_log = [
                {"sender": "bot", "text": "I have received your uploaded file. The analysis has been successfully completed. You can now ask any questions."}
        ]
        chat_entry = db_info.ChatInfo(
            chat_id=chatid,
            chat_type='-'.join(chat_type.split('-')[:2]),
            access_date=datetime.now(timezone.utc),
            chat=json.dumps(chat_log),
            chat_title=file.filename, 
            chat_title_set=True
        )
        db.add(chat_entry)
        # db.commit()
        # db.refresh(chat_entry)

        logging.info("Chat info added to Chat_Info table")

        response = {"chatid": chatid, "gu_id": gu_id, "file_path": str(file_path)}

        return response
    
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"File upload failed: {error_message}")
        raise InternalError("File upload failed")


async def embed_pdf_in_vectorstore(
        chatid: str,
        gu_id: str = None
        ) -> FAISS_DB:
    """
    Processes an uploaded PDF file for embedding.
   
    Parameters:
        chatid (str): Identifier for the chat session.
        gu_id (str): gu_id of the uploaded PDF file.
   
    Returns:
        uploaded_db : Vector store
   
    Raises:
        HTTPException: If embedding fails.
    """
    try:
        # Connect to the database
        with db_info.get_db_context() as db:
            logging.info(f"Received request to embed file for chatid: {chatid}")
            persist_directory = f"{PERSIST_DIRECTORY}/{chatid}"
            uploaded_db = FAISS_DB(embedding_function=EMBEDDINGS, persist_directory=persist_directory)
            uploaded_db.load()
    
            data_loader = DATA_LOADER_SP(
                client_id=CLIENT_ID,
                client_secret=CLIENT_SECRET,
                site_url=SITE_URL,
                sharepoint_url=SHAREPOINT_URL
            )
        
            await data_loader.data_to_db_sp(
                sp_library_title=SP_LIBRARY_TITLE,
                sp_folder_relative_path=f"{SP_RENAULT}/{chatid}",
                vectorstore=uploaded_db,
                source="uploaded",
                gu_id=gu_id,
            )
    
            logging.info(f"Embedding successful for: {chatid}")
    
            return uploaded_db
 
    except Exception as e:
        with db_info.get_db_context() as db:
            # remove the added file information from UploadFileInfo if embedding has not happened
            record_to_delete = db.query(db_info.UploadFileInfo).filter_by(file_id=gu_id, chat_id=chatid).first() 
            embedded_data = db.query(db_info.FileInfo).filter_by(file_id=gu_id).first()
            if record_to_delete and embedded_data and not embedded_data.embed_done:
                db.delete(record_to_delete)
                db.commit()
            error_message = get_error_message_detail(e, sys)
            logging.error(f"Embedding failed for {chatid}: {error_message}")
            raise InternalError("Embedding process failed")



async def get_embeded_db(
        file_name: str=None,
        gu_id: str=None,
        db: Session = None
        ) -> tuple[str, str, FAISS_DB]:
    """
    Identify the vectorstore in which embeddings of the corresponding file is present.
   
    Parameters:
        file_name (str): Name of the file
        gu_id (str): UUID of the file (if available)
        db (Session): Postgresql session.

    Returns:
       (guid, str, FAISS_DB) : UUID of the file, the file path in sharepoint ,FAISS_DB in which the embeddings of the file is present.
    """
    try:
        if gu_id:
            fileinfo = db.query(db_info.FileInfo).filter((db_info.FileInfo.gu_id==gu_id),(db_info.FileInfo.source=="sharepoint")).first()
        
            if not fileinfo:
                logging.error(f"File with guid '{gu_id}' does not exist in sharepoint.")
                raise InternalError(f"File with guid '{gu_id}' does not exist in sharepoint.")
            
            else:
                filepath = fileinfo.file_path
                logging.info(f"File exists in sharepoint: {filepath}")

        elif file_name:
            fileinfo = db.query(db_info.FileInfo).filter((db_info.FileInfo.file_name==file_name),(db_info.FileInfo.source=="sharepoint")).first()

            if not fileinfo:
                logging.error(f"File '{file_name}' does not exist in sharepoint.")
                raise InternalError(f"File '{file_name}' does not exist in sharepoint.")
        
            else:
                filepath = fileinfo.file_path
                gu_id= fileinfo.gu_id
                logging.info(f"File exists in sharepoint: {filepath}")
    
        elif not gu_id and not file_name:
            logging.error("Error: Neither file_name nor gu_id is passed.")
            raise InternalError("Error: Neither file_name nor gu_id is passed.")
    
        # Extract file name and get folder name
        normalized_path = os.path.normpath(filepath)
            
        # Load vectorstore based on folder_identifier
        if SP_RENAULT in normalized_path:
            vectorstore= RENAULT_DB
            logging.info(f"The given file is found in vectorstore:{vectorstore.persist_directory}")

        else:
            logging.error(f"Unable to determine vectorstore path for: {normalized_path}")
            raise InternalError(f"Unable to determine vectorstore path for: {normalized_path}")
    
        return gu_id, filepath, vectorstore
 
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.info(error_message)
        return None, None, None

