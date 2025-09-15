"""This module handles routers of renault report insights chat model"""

import sys
import os
import pandas as pd
import shutil
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status, Body, Form
from typing import List
import uuid
from datetime import datetime,timezone
from pydantic import UUID4
from sqlalchemy.orm import Session
from app.info import auth_info
from app.utils import output_source_correction,EMBEDDINGS, PERSIST_DIRECTORY
from app.info.db_info import get_db,ChatInfo,UploadFileInfo,FileInfo, AuditsConcatenated
from app.info.query_info import QueryInfo, SearchRequest, FileResponse
from app.components.generate_tables.scripts import generate_table
from app.components.file_handler import get_sharepoint_context
from app.components.action_handler import  create_chain, create_specific_chain, get_response,embed_failure_cleaning, create_renault_agent, get_agent_response
from app.components.file_handler import upload_file_to_sharepoint, embed_pdf_in_vectorstore, get_embeded_db
from app import utils
import json
from app.logger import logging
from app.exception import get_error_message_detail, InternalError
from app.info import db_info
from fastapi.responses import JSONResponse
from langchain.schema import HumanMessage, AIMessage
from app.models.vectorstore import FAISS_DB
from app.components.heartbeat import heartbeat
from urllib.parse import urlparse, unquote


# Create FastAPI router
router = APIRouter()


# @router.post("/upload")
# async def upload_file(
#     valid_api_key: bool = Depends(auth_info.validate_api_key),
#     db: Session  = Depends(get_db),
#     file: UploadFile = None,
																			  
# ) -> JSONResponse:
#     """
#     Endpoint to upload a PDF file to SharePoint.
    
#     Parameters:
#         valid_api_key (bool): If validation of API key is success or not
#         db (Session): Postgresql session.
#         file (UploadFile): Uploaded file.
    
#     Returns:
#         (JSONResponse): contains http status code and content with output data.
#     """
#     try:
#         if  file == None:
#             logging.error("Invalid file / File not uploaded")
#             return JSONResponse(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 content={
#                     "message": "Invalid file / File not uploaded",
#                     "error": True,
#                     "data": []
#                 }
#             )
        
#         logging.info(f"Starting RFP file upload process - file: {file.filename}")

#         # Check if the file has already embeded
#         gu_id, file_path, vectorstore = await get_embeded_db(file_name=file.filename,db=db)

#         # Create chain if file already exists
#         if gu_id and vectorstore:
#             logging.info(f"File {file.filename} found in the vectorstore. Creating specific chain.")

#             chatid = str(uuid.uuid4())

#             file_info = db.query(db_info.FileInfo).filter(db_info.FileInfo.gu_id == gu_id).first() # ,db_info.FileInfo.source == "uploaded"

#             upload_entry = UploadFileInfo(
#                             chat_id=chatid,
#                             file_id=gu_id,
#                             chat_type="report upload",
#                             upload_date=datetime.now(timezone.utc),
#                             file_name=file.filename,
#                             file_path=file_path,
#                             file_size = file.size,
#                             link_uri = file_info.link_uri if file_info and file_info.link_uri else ""
#                         )
#             db.add(upload_entry)
#             # db.commit()
#             # db.refresh(upload_entry)
#             chat_log = [
#                 {"sender": "bot", "text": "I have received your uploaded file. The analysis has been successfully completed. You can now ask any questions."}
#             ]
#             chat_entry = ChatInfo(
#                 chat_id=chatid,
#                 chat_type="file-assistant",
#                 access_date=datetime.now(timezone.utc),
#                 chat=json.dumps(chat_log),
#                 chat_title=file.filename, 
#                 chat_title_set=True
#             )
#             db.add(chat_entry)
#             # db.commit()
#             # db.refresh(chat_entry)

#             logging.info(f"Initializing new chat session for chatid: {chatid}  ")
#             persist_path = f'{PERSIST_DIRECTORY}/{chatid}'
#             retriever_chain, chat_history = await create_specific_chain(gu_id, vectorstore,persist_path)
#             utils.chat_sessions[chatid] = {
#                     "retriever_chain":retriever_chain ,
#                     "chat_history":chat_history
#                 }
            
#             db.commit()

#             response_content = {
#                 "message": "File uploaded successfully",
#                 "error": False,
#                 "data": {"chatid": chatid, "gu_id": str(gu_id), "file_path": file_path}
#             }

#             logging.info(f"--- DEBUG: RETURNING FROM UPLOAD: {response_content} ---")

#             return JSONResponse(
#                 status_code=status.HTTP_200_OK,
#                 content=response_content
#             )

#         # If file not embedded, upload the file to sharepoint.
#         else:
#             if not file.filename.lower().endswith(".pdf"):
#                 logging.warning(f"File upload rejected: {file.filename} is not a PDF")
#                 return JSONResponse(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     content={
#                         "message": "Only PDF files are allowed",
#                         "error": True,
#                         "data": []
#                     }
#                 )
            
#             chat_type="file-assistant-upload"
#             chatid = str(uuid.uuid4())
#             logging.info(f"Generated new chatid: {chatid}")

#             response = await upload_file_to_sharepoint(file, chat_type, db=db, chatid = chatid)# HTTPException handled in function
#             db.commit()

#             gu_id = response.get("gu_id")  # Ensure your SharePoint upload returns this
#             file_path = response.get("file_path", "")

#             # Initialize session status for later polling
#             utils.chat_sessions[chatid] = {
#                 "embedding_done": False,
#                 "tables_done": False
#             }
            
#             return JSONResponse(
#                 status_code=status.HTTP_200_OK,
#                 content={
#                     "message": "PDF file uploaded to SharePoint",
#                     "error": False,
#                     "data": {
#                         "chatid": chatid,
#                         "gu_id": str(gu_id),
#                         "file_path": file_path
#                     }
#                 }
#             )

#     except HTTPException as http_ex:
#         error_message = get_error_message_detail(http_ex, sys)
#         logging.error(f"Error in : {error_message}")
#         return JSONResponse(
#         status_code=http_ex.status_code,
#             content={
#                 "message": http_ex.detail if isinstance(http_ex.detail, str) else str(http_ex.detail),
#                 "error": True,
#                 "data": []
#             }
#         )

#     except Exception as e:
#         db.rollback()
#         error_message = get_error_message_detail(e, sys)
#         logging.error(f"Error in : {error_message}")
#         return JSONResponse(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             content={
#                 "message": "An internal server error occurred while Uploading file",
#                 "error": True,
#                 "data": []
#             }
#         )


#TEST - to fix an error

@router.post("/upload")
async def upload_file(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    db: Session  = Depends(get_db),
    file: UploadFile = None,                        
) -> JSONResponse:
    """
    Endpoint to upload a PDF file. It handles both new and existing files.
    """
    try:
        if file is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "No file uploaded", "error": True, "data": []}
            )
        
        logging.info(f"Starting file upload process for: {file.filename}")

        # Check if the file already exists in the system
        gu_id, file_path, vectorstore = await get_embeded_db(file_name=file.filename, db=db)

        # --- PATH 1: File already exists ---
        if gu_id and vectorstore:
            logging.info(f"File '{file.filename}' found. Creating new chat session for existing document.")
            chatid = str(uuid.uuid4())

            # Create new DB entries for this specific chat session
            file_info = db.query(db_info.FileInfo).filter(db_info.FileInfo.gu_id == gu_id).first()
            upload_entry = UploadFileInfo(
                chat_id=chatid, file_id=gu_id, chat_type="report upload",
                upload_date=datetime.now(timezone.utc), file_name=file.filename,
                file_path=file_path, file_size=file.size,
                link_uri=file_info.link_uri if file_info else ""
            )
            db.add(upload_entry)
            
            chat_log = [{"sender": "bot", "text": "This document has been analyzed before. You can ask any questions."}]
            chat_entry = ChatInfo(
                chat_id=chatid, chat_type="file-assistant", access_date=datetime.now(timezone.utc),
                chat=json.dumps(chat_log), chat_title=file.filename, chat_title_set=True
            )
            db.add(chat_entry)

            # Create and store the conversational chain in memory for this session
            persist_path = f'{PERSIST_DIRECTORY}/{chatid}'
            retriever_chain, chat_history = await create_specific_chain(gu_id, vectorstore, persist_path)
            utils.chat_sessions[chatid] = {
                "retriever_chain": retriever_chain,
                "chat_history": chat_history
            }
            db.commit()

            # Return both IDs to the front-end
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "File already exists. New chat session created.",
                    "error": False,
                    "data": {"chatid": chatid, "gu_id": str(gu_id)}
                }
            )

        # --- PATH 2: New file ---
        else:
            logging.info(f"'{file.filename}' is a new file. Starting upload to SharePoint.")
            if not file.filename.lower().endswith(".pdf"):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Only PDF files are allowed", "error": True, "data": []}
                )
            
            chatid = str(uuid.uuid4())
            response = await upload_file_to_sharepoint(file, "file-assistant-upload", db=db, chatid=chatid)
            db.commit()

            gu_id = response.get("gu_id")
            
            # Return both IDs to the front-end so it can trigger the processing steps
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "New file uploaded successfully. Awaiting processing.",
                    "error": False,
                    "data": {
                        "chatid": chatid,
                        "gu_id": str(gu_id)
                    }
                }
            )

    except Exception as e:
        logging.error(f"An unexpected error occurred in /upload: {e}", exc_info=True)
        db.rollback()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "An internal server error occurred while uploading the file.", "error": True}
        )






@router.post("/embed")
async def embed_pdf(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    chatid: str = Form(None),
    gu_id: str = Form(None),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Endpoint to embed a PDF file into a vector database. Create chain
   
    Parameters:
        valid_api_key (bool): If validation of API key is success or not
        chatid (UUID4): Unique identifier of the chat.
        gu_id (UUID4): Unique identifier of the file.
    
    Returns:
        (JSONResponse): contains http status code and content with output data.
    """
    try:
        
        if gu_id is None:
            logging.error("FileID is not passed, removing data from database.")
            try:
                embed_failure_cleaning(db=db, chatid=UUID4(chatid))
                db.commit()
            except Exception as cleanup_err:
                db.rollback()
                logging.error(f"Failed to clear uploaded data for chatid {chatid}: {cleanup_err}")

            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "FileID is not passed, removing data from database. Please upload file again",
                    "error": True,
                    "data": []

                }
            )
        

        # if gu_id is None:
        #     logging.error("FileID (gu_id) was not passed to the /embed endpoint.")
            
        #     # Only attempt cleanup if a chatid was actually provided
        #     if chatid:
        #         try:
        #             # Ensure chatid is a UUID object before passing it to the cleanup function
        #             chat_uuid = UUID4(str(chatid)) 
        #             embed_failure_cleaning(db=db, chatid=chat_uuid)
        #             db.commit()
        #         except Exception as cleanup_err:
        #             db.rollback()
        #             logging.error(f"Failed to clear uploaded data for chatid {chatid}: {cleanup_err}")

        #     return JSONResponse(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         content={
        #             "message": "FileID (gu_id) is required for embedding.",
        #             "error": True,
        #             "data": []
        #         }
        #     )

        chatid = str(chatid)
        gu_id = str(gu_id)

        if chatid not in utils.chat_sessions:
        
            # Embed file to vectorstore
            logging.info(f"Embedding PDF for chatid: {chatid} (fileID: {gu_id})")
            vectorstore = await embed_pdf_in_vectorstore(chatid=chatid, gu_id=gu_id)
        
            # Create chain
            logging.info(f"Initializing new chat session for chatid: {chatid}")
            retriever_chain, chat_history = create_chain(vectorstore)

            utils.chat_sessions[chatid] = {
                "retriever_chain": retriever_chain,
                "chat_history": chat_history
            }
            logging.info(f"Specific retriever chain created for chatid: {chatid}")

            # At the end of /embed after successful processing
            if chatid in utils.chat_sessions:
                utils.chat_sessions[chatid]["embedding_done"] = True
                logging.info(f"Embedding completed for chatid={chatid}")
 
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Specific retriever chain created for chat",
                "error": False,
                "data": {"chatid": chatid}
            }
        )
    
    except HTTPException as http_ex:
        error_message = get_error_message_detail(http_ex, sys)
        logging.error(f"Error in : {error_message}")
        return JSONResponse(
        status_code=http_ex.status_code,
            content={
                "message": http_ex.detail if isinstance(http_ex.detail, str) else str(http_ex.detail),
                "error": True,
                "data": []
            }
        )
   
    except Exception as e:
        logging.error(f"Embedding failed for chat {chatid}: {e}")
        try:
            embed_failure_cleaning(db=db, chatid=UUID4(chatid) )
        except Exception as cleanup_err:
            db.rollback()
            logging.error(f"Failed embedding failure cleanup for chat {chatid}: {cleanup_err}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred while Embedding. Saved data removed",
                "error": True,
                "data": []
            }
        )   

############ table gen##################

@router.post("/generate-tables")
async def generate_tables(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    chatid: str = Form(None),
    gu_id: str = Form(None),
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Endpoint to process uploaded PDF → run generate_table.py → 
    store extracted KPI/value pairs in ft_audits_concatanated.
    
    Parameters:
        valid_api_key (bool): API key validation
        chatid (UUID4): Unique identifier of the chat session
        gu_id (UUID4): Unique identifier of the file
    
    Returns:
        JSONResponse with status, message, and row count
    """
    try:
        if gu_id is None:
            logging.error("FileID not provided, rolling back")
            db.rollback()
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "FileID not provided. Please upload again.",
                    "error": True,
                    "data": []
                }
            )

        chatid = str(chatid)
        gu_id = str(gu_id)

        # Check if file already processed
        existing = db.query(AuditsConcatenated).filter_by(file_id=gu_id).first()
        if existing:
            logging.info(f"file was already processed: {gu_id}")
            return JSONResponse(
                status_code=status.HTTP_208_ALREADY_REPORTED,
                content={
                    "message": f"File {gu_id} already processed",
                    "error": False,
                    "data": []
                }
            )

        logging.info(f"New file - starting table generation: {gu_id}")

        uploaded_file_record = db.query(UploadFileInfo).filter_by(file_id=gu_id).first()
        if not uploaded_file_record:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"message": "File record not found in DB", "error": True, "data": []}
            )
        
        filename = uploaded_file_record.file_name

        # Prepare input path
        input_dir = "app/components/generate_tables/data/input"
        os.makedirs(input_dir, exist_ok=True)
        file_path = os.path.join(input_dir, filename)


        sharepoint_file_path = uploaded_file_record.file_path
        parsed_url = urlparse(sharepoint_file_path)
        # Server-relative path
        server_relative_path = unquote(parsed_url.path)  # decode %20 to spaces, etc.
        logging.info(f"Downloading SharePoint file {sharepoint_file_path} → {file_path}")
        
        try:
            ctx = get_sharepoint_context()
            with open(file_path, "wb") as local_file:
                ctx.web.get_file_by_server_relative_url(server_relative_path).download(local_file).execute_query()
            logging.info("File downloaded successfully from SharePoint.")
        except Exception as e:
            logging.error(f"Error downloading from SharePoint: {e}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": f"Error downloading file: {str(e)}", "error": True, "data": []}
            )
        
        # Process the file
        dealer_stats_df =  generate_table.start_automation()
        rows_inserted = 0
        for _, row in dealer_stats_df.iterrows():
            record = AuditsConcatenated(
                filename=str(row.get("filename", "")),
                statistic=str(row.get("statistic", "")),
                value=str(row.get("value", "")),
                upload_date=datetime.now(timezone.utc),
                file_id=gu_id,
                chat_id=chatid
            )
            db.add(record)
            rows_inserted += 1
        db.commit()


        # Cleanup input file
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info("input file deleted from temporary folder")

        output_dir = "app/components/generate_tables/data/output"
        outputfilepath = os.path.join(output_dir, 'audits_concatenated.xlsx')

        # Cleanup output file
        if os.path.exists(outputfilepath):
            os.remove(outputfilepath)
            logging.info("output excel deleted from temporary folder")

        # At the end of /generate-tables after successful processing
        if chatid in utils.chat_sessions:
            utils.chat_sessions[chatid]["tables_done"] = True
            logging.info(f"Table generation completed for chatid={chatid}")


        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"File {gu_id} processed successfully",
                "error": False,
                "data": {"rows_inserted": rows_inserted}
            }
        )


    except Exception as e:
        db.rollback()
        logging.error(f"Error in /generate-tables: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal error in table generation", "error": True, "data": []}
        )
    
    



@router.post("/chat")
async def specific_chat(
    db: Session = Depends(get_db),
    request: QueryInfo = None
) -> JSONResponse:
    try:
        if request is None:
            logging.error("Invalid input: request is None")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Invalid input", "error": True, "data": []}
            )

        if not request.query:
            logging.error("Missing query in request")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "Query is required", "error": True, "data": []}
            )

        # ----- Handle chatid -----
        if request.chatid in [None, ""]:
            chatid = str(uuid.uuid4())
            logging.info(f"New chat created with chatid={chatid}")
            chat_record = ChatInfo(
                chat_id=chatid,
                chat_type="generic",
                chat="[]",
                access_date=datetime.now(timezone.utc),
            )
            db.add(chat_record)
            db.commit()
            db.refresh(chat_record)
            chat_log = []
            chat_history = []
        else:
            try:
                chatid = str(uuid.UUID(str(request.chatid)))
            except (ValueError, AttributeError, TypeError):
                logging.error(f"Invalid chatid format: {request.chatid}")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"message": "Invalid chatid format", "error": True, "data": []}
                )

            chat_record = db.query(ChatInfo).filter_by(chat_id=chatid).first()
            if not chat_record:
                logging.warning(f"Chat not found: {chatid}, Creating new one")
                
                chat_record = ChatInfo(
                chat_id=chatid,
                chat_type="generic",
                chat="[]",
                access_date=datetime.now(timezone.utc),
                )
                db.add(chat_record)
                db.commit()
                db.refresh(chat_record)
                chat_log = []
                chat_history = []
                logging.info(f"new chat record for {chatid}")
                
                # return JSONResponse(
                #     status_code=status.HTTP_404_NOT_FOUND,
                #     content={"message": "Invalid chat ID.", "error": True, "data": []}
                # )

            chat_log = json.loads(chat_record.chat)
            chat_history = [
                HumanMessage(content=msg["text"]) if msg["sender"] == "user"
                else AIMessage(content=msg["text"])
                for msg in chat_log
            ]

        # ----- Update heartbeat -----
        heartbeat(chatid)

        # ----- Initialize / rebuild session -----
        if chatid not in utils.chat_sessions:
            logging.info(f"Reconstructing session for chatid {chatid}")
            vectorstore = None
            vectorstore_path = f'{PERSIST_DIRECTORY}/{chatid}'

            if os.path.exists(vectorstore_path):
                vectorstore = FAISS_DB(embedding_function=EMBEDDINGS, persist_directory=vectorstore_path)
                vectorstore.load()
                logging.info("Vectorstore loaded for chat session.")
            else:
                logging.info("No vectorstore found. Proceeding without document retrieval.")



            # Create the agent — pass vectorstore only if it exists
            graph, _ = await create_renault_agent(
                existing_file_db=vectorstore,
                chat_history=chat_history
            )

            utils.chat_sessions[chatid] = {
                "graph": graph,
                "chat_history": chat_history
            }

        session = utils.chat_sessions.get(chatid)
        if not session:
            logging.error("Session reconstruction failed unexpectedly")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "Session not found", "error": True, "data": []}
            )

        # ----- Generate response -----
        if "graph" in session:
            graph = session["graph"]
            chat_history = session["chat_history"]
            graph, result = await get_agent_response(
                graph=graph,
                chat_history=chat_history,
                query=request.query
            )
        elif "retriever_chain" in session:
            retriever_chain = session["retriever_chain"]
            chat_history = session["chat_history"]
            chat_history, result = await get_response(
                chain=retriever_chain,
                chat_history=chat_history,
                question=request.query
            )
        else:
            logging.error("No valid chain or graph found in session")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"message": "No valid session chain", "error": True, "data": []}
            )

        # ----- Save updated history -----
        session["chat_history"] = chat_history
        final_out = output_source_correction(result=result)

        chat_log.append({"sender": "user", "text": request.query})
        chat_log.append({"sender": "bot", "text": final_out})
        chat_record.chat = json.dumps(chat_log)
        chat_record.access_date = datetime.now(timezone.utc)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Response generated successfully",
                "error": False,
                "data": {"chatid": chatid, "response": final_out}
            }
        )

    except Exception as e:
        db.rollback()
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error in Specific chat: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"message": "Internal server error", "error": True, "data": []}
        )


@router.get("/status/{chatid}")
async def get_status(chatid: str):
    session = utils.chat_sessions.get(chatid)
    if not session:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"message": "Chat session not found", "error": True, "data": []}
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Status retrieved successfully",
            "error": False,
            "data": {
                "embedding_done": session.get("embedding_done", False),
                "tables_done": session.get("tables_done", False)
            }
        }
    )
