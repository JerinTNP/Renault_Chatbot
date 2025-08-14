"""This module handles routers of specific chat model"""

import sys
import os
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status, Body
from typing import List
import uuid
from datetime import datetime,timezone
from pydantic import UUID4
from sqlalchemy.orm import Session
from app.info import auth_info
from app.utils import output_source_correction,EMBEDDINGS, PERSIST_DIRECTORY
from app.info.db_info import get_db, UserInfo,ChatInfo,UploadFileInfo,FileInfo
from app.info.query_info import QueryInfo, SearchRequest, FileResponse
from app.components.action_handler import search_files_by_keyword, create_chain, create_specific_chain, get_response,embed_failure_cleaning
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


# Create FastAPI router
router = APIRouter()


@router.post("/upload")
async def upload_file(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    authorization: dict = Depends(auth_info.get_auth_token_user),
    db: Session  = Depends(get_db),
    file: UploadFile = None,
    # userid: UUID4 = Query(..., description="User ID as UUID")
																			  
) -> JSONResponse:
    """
    Endpoint to upload a PDF file to SharePoint.
    
    Parameters:
        valid_api_key (bool): If validation of API key is success or not
        authorization (dict): Payload of the autorised user.
        db (Session): Postgresql session.
        file (UploadFile): Uploaded file.
    
    Returns:
        (JSONResponse): contains http status code and content with output data.
    """
    try:
        userid = str(authorization.get("user_id"))

        if not db.query(UserInfo).filter(UserInfo.user_id == userid).first():
            return JSONResponse(
                status_code =  status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": "User is not autherized or does not exist",
                    "error":True,
                    "data":[]
                }
            )
        if  file == None:
            logging.error("Invalid file / File not uploaded")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid file / File not uploaded",
                    "error": True,
                    "data": []
                }
            )
        userid = str(userid)
        
        # Initialise user session
        if userid not in utils.chat_sessions:
            utils.chat_sessions[userid] = {}

        logging.info(f"Starting RFP file upload process for userid: {userid}, file: {file.filename}")

        # Check if the file has already embeded
        gu_id, file_path, vectorstore = await get_embeded_db(userid=userid, file_name=file.filename,db=db)

        # Create chain if file already exists
        if gu_id and vectorstore:
            logging.info(f"File {file.filename} found in the vectorstore. Creating specific chain.")

            chatid = str(uuid.uuid4())

            file_info = db.query(db_info.FileInfo).filter(db_info.FileInfo.gu_id == gu_id).first() # ,db_info.FileInfo.source == "uploaded"

            upload_entry = UploadFileInfo(
                            user_id=userid,
                            chat_id=chatid,
                            file_id=gu_id,
                            chat_type="file-assistant-upload",
                            upload_date=datetime.now(timezone.utc),
                            file_name=file.filename,
                            file_path=file_path,
                            file_size = file.size,
                            link_uri = file_info.link_uri if file_info and file_info.link_uri else ""
                        )
            db.add(upload_entry)
            # db.commit()
            # db.refresh(upload_entry)
            chat_log = [
                {"sender": "bot", "text": "I have received your uploaded file. The analysis has been successfully completed. You can now ask any questions."}
            ]
            chat_entry = ChatInfo(
                user_id=userid,
                chat_id=chatid,
                chat_type="file-assistant",
                access_date=datetime.now(timezone.utc),
                chat=json.dumps(chat_log),
                chat_title=file.filename, 
                chat_title_set=True
            )
            db.add(chat_entry)
            # db.commit()
            # db.refresh(chat_entry)

            logging.info(f"Initializing new chat session for chatid: {chatid} (userid: {userid})")
            persist_path = f'{PERSIST_DIRECTORY}/{chatid}'
            retriever_chain, chat_history = await create_specific_chain(gu_id, vectorstore,persist_path)
            utils.chat_sessions[userid][chatid] = {
                    "retriever_chain":retriever_chain ,
                    "chat_history":chat_history
                }
            
            db.commit()

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "File uploaded successfully",
                    "error": False,
                    "data": {"chatid": chatid, "gu_id": str(gu_id), "file_path": file_path}
                }
            )

        # If file not embedded, upload the file to sharepoint.
        else:
            if not file.filename.lower().endswith(".pdf"):
                logging.warning(f"File upload rejected: {file.filename} is not a PDF")
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={
                        "message": "Only PDF files are allowed",
                        "error": True,
                        "data": []
                    }
                )
            chat_type="file-assistant-upload"
            response = await upload_file_to_sharepoint(file, userid, chat_type, db=db)# HTTPException handled in function
            db.commit()
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "PDF file uploaded to sharepoint",
                    "error": False,
                    "data": response
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
        db.rollback()
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error in : {error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred while Uploading file",
                "error": True,
                "data": []
            }
        )


@router.post("/embed")
async def embed_pdf(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    authorization: dict = Depends(auth_info.get_auth_token_user),
    # userid: UUID4 = None,
    chatid: UUID4 = None,
    gu_id: UUID4 = None,
    db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Endpoint to embed a PDF file into a vector database. Create chain
   
    Parameters:
        valid_api_key (bool): If validation of API key is success or not
        authorization (dict): Payload of the autorised user.
        chatid (UUID4): Unique identifier of the chat.
        gu_id (UUID4): Unique identifier of the file.
    
    Returns:
        (JSONResponse): contains http status code and content with output data.
    """
    try:
        userid = str(authorization.get("user_id"))

        if userid == None or chatid == None:
            logging.error("ChatID, UserID is required")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "ChatID, UserID is required",
                    "error": True,
                    "data": []

                }
            )
        elif gu_id == None:
            logging.error("FileID is not passed, removing data from database.")
            try:
                embed_failure_cleaning(db=db, chatid=UUID4(chatid), userid=UUID4(userid))
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

        chatid = str(chatid)
        gu_id = str(gu_id)

        if chatid not in utils.chat_sessions[userid]:
   
            # Embedd file to vectorstore
            logging.info(f"Embedding PDF for chatid: {chatid} (userid: {userid} with fileID {gu_id})")
            vectorstore = await embed_pdf_in_vectorstore(userid, chatid, gu_id)
 
            # Creare chain
            logging.info(f"Initializing new chat session for chatid: {chatid} (userid: {userid})")
            retriever_chain, chat_history = create_chain(vectorstore)
            utils.chat_sessions[userid][chatid] = {
                    "retriever_chain":retriever_chain ,
                    "chat_history":chat_history
                }
            logging.info(f"Specific retriever chain created for chatid : {chatid}")
 
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
            embed_failure_cleaning(db=db, chatid=UUID4(chatid), userid=UUID4(userid))
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


@router.post("/chat")
async def specific_chat(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    authorization: dict = Depends(auth_info.get_auth_token_user),
    db: Session = Depends(get_db),
    request: QueryInfo = None
) -> JSONResponse:
    """
    Handles specific chat queries by susing specific.

    Parameters:
        valid_api_key (bool): If validation of API key is success or not
        authorization (dict): Payload of the autorised user.
        db (Session): Postgresql session.
        request (QueryInfo): User input.
    
    Returns:
        (JSONResponse): contains http status code and content with output data.
    """

    try:
        userid = str(authorization.get("user_id"))

        if request == None:
            logging.error("Invalid input")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid input",
                    "error": True,
                    "data": []

                }
            )
        if not db.query(UserInfo).filter(UserInfo.user_id == userid).first():
            return JSONResponse(
                status_code =  status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": "User is not autherized or does not exist",
                    "error":True,
                    "data":[]
                }
            )

        chatid= str(request.chatid)

        # Validate query
        if not request.query:
            logging.error("Missing query in request")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Query is required",
                    "error": True,
                    "data": []
                }
            )
        
        #userid
        logging.info(f"Received chat request from user_id: {userid}")

        chat_record = db.query(ChatInfo).filter_by(user_id=userid, chat_id=chatid).first()
        if not chat_record:
        #Ensure the chatid belongs to this user
            logging.warning(f"Unauthorized access attempt to chatid: {chatid} by userid: {userid}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": "Invalid or unauthorized chat ID.",
                    "error": True,
                    "data": []
                }
            )

        heartbeat(userid, chatid)

        # Check if session needs to be rebuilt (likely due to restart)
        if str(userid) not in utils.chat_sessions or str(chatid) not in utils.chat_sessions[str(userid)]:

            logging.info(f"Session not found in memory. Likely system restart — reconstructing session for user {userid} with chatID {chatid}.")
            chat_log = json.loads(chat_record.chat)

            # Reconstruct chat_history for LLM
            chat_history = [
                HumanMessage(content=msg["text"]) if msg["sender"] == "user"
                else AIMessage(content=msg["text"])
                for msg in chat_log
            ]
            # Get file info from UploadFileInfo to recreate retriever_chain
            file_info = db.query(UploadFileInfo).filter_by(user_id=userid, chat_id=chatid).first()
            if not file_info:
                return JSONResponse(
                    status_code=status.HTTP_404_NOT_FOUND,
                    content={"message": "No uploaded file info found to recreate chain", "error": True, "data": []}
                )

            vectorstore_path = f'{PERSIST_DIRECTORY}/{chatid}'
            if os.path.exists(vectorstore_path):
                vectorstore=FAISS_DB(embedding_function=EMBEDDINGS,persist_directory=vectorstore_path)
                vectorstore.load()
                logging.info(f"The given file is found in vectorstore with chatid:{chatid}")
            else:
                logging.error("Unable to determine vectorstore path for the uploaded folder")
                raise InternalError("Unable to determine vectorstore path for the uploaded folder")
            retriever_chain, _ = create_chain(vectorstore=vectorstore,chat_history=chat_history)

            # Re-register session in memory
            utils.chat_sessions.setdefault(str(userid), {})[str(chatid)] = {
                "retriever_chain": retriever_chain,
                "chat_history": chat_history,
            }            


        #Fetch chat session
        # session = utils.chat_sessions[userid][chatid]
        session = utils.chat_sessions.get(userid, {}).get(chatid)
        if not session:
            logging.error("Session reconstruction failed unexpectedly")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "message": "Session not found after reconstruction",
                    "error": True,
                    "data": []
                }
            )
        retriever_chain = session["retriever_chain"]
        chat_history = session["chat_history"]

        #generating response
        chat_history, result = await get_response(chain = retriever_chain, chat_history = chat_history, question = request.query)
        logging.info("Response generated successfully")

        # Store updated history
        session["chat_history"] = chat_history

        #Applying output source correction
        final_out = output_source_correction(result=result)

        chat_log = json.loads(chat_record.chat)
        # Append latest interaction
        chat_log.append({"sender": "user", "text": request.query})
        chat_log.append({"sender": "bot", "text": final_out})

        # Update DB
        chat_record.chat = json.dumps(chat_log)
        chat_record.access_date = datetime.now(timezone.utc)
        db.commit()

        #returning the final response
        logging.info("Returning final response")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Response generated successfully",
                "error": False,
                "data": {
                    "userid": str(userid),
                    "chatid": str(chatid),
                    "response": final_out
                }
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
        db.rollback()
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error in Specific chat: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred while starting Specific chat",
                "error": True,
                "data": []
            }
        )
