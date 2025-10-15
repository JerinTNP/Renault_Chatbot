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
from app.info.db_info import get_db,ChatInfo,UploadFileInfo,FileInfo, CombinedAudit
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
        existing = db.query(CombinedAudit).filter_by(file_id=gu_id).first()
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
        print("Starting Process the file")
        dealer_stats_df =  generate_table.start_automation()
        print("start automation ran succesfully")
        rows_inserted = 0


        for _, row in dealer_stats_df.iterrows():
            # Create a new record using the updated CombinedAudit model
            record = CombinedAudit(
                # --- Pre-defined values ---
                upload_date=datetime.now(timezone.utc),
                file_id=gu_id,
                chat_id=chatid,

                # --- Columns mapped from the DataFrame row ---
                file_name=row.get('file_name'),
                country=row.get('country'),
                dealer_name=row.get('dealer_name'),
                dealer_code=row.get('dealer_code'),
                address_full=row.get('address_full'),
                rrg=row.get('rrg'),
                renault_sales_per_year=row.get('renault_sales_per_year'), # Renamed from renault_sales_by_year
                dacia_sales_per_year=row.get('dacia_sales_per_year'),     # New column
                workshop_customers_per_day=row.get('workshop_customers_per_day'), # Renamed from workshop_customer_per_day
                global_score=row.get('global_score'),
                auditor=row.get('auditor'),
                audit_date=row.get('audit_date'),
                new_vehicle_activity=row.get('new_vehicle_activity'),
                aftersales_activity=row.get('aftersales_activity'), # Renamed from after_sales_activity
                appointment_booking_per_preparation=row.get('appointment_booking_per_preparation'), # Renamed from appointment_booking
                customer_journey=row.get('customer_journey'),
                product_presentation=row.get('product_presentation'), # New column
                reception=row.get('reception'),                     # New column
                order_management=row.get('order_management'),
                production=row.get('production'),
                preperation_per_delivery=row.get('preperation_per_delivery'), # New column
                restitution=row.get('restitution'),
                new_vehicle_activity_management=row.get('new_vehicle_activity_management'), # Mapped from old 'management1'
                aftersales_activity_management=row.get('aftersales_activity_management'),  # Mapped from old 'management2'
                basics_sales_methods=row.get('basics_sales_methods'), # Renamed from basics_sales_method
                brand_store_renault=row.get('brand_store_renault'),
                basics_aftersales_methods=row.get('basics_aftersales_methods'),
                flash_ares_maintainence=row.get('flash_ares_maintainence'),
                digital_renault=row.get('digital_renault'),
                journey_experience_renault=row.get('journey_experience_renault'),
                website_conformity_renault=row.get('website_conformity_renault'),
                brand_store_dacia=row.get('brand_store_dacia'),
                digital_dacia=row.get('digital_dacia'),
                journey_experience_dacia=row.get('journey_experience_dacia'),
                website_conformity_dacia=row.get('website_conformity_dacia'),
                digital_score=row.get('digital_score'), # New column
                
                # --- Question columns ---
                q1=row.get('q1'), q2=row.get('q2'), q3=row.get('q3'), q4=row.get('q4'), 
                q5=row.get('q5'), q6=row.get('q6'), q7=row.get('q7'), q8=row.get('q8'), 
                q9=row.get('q9'), q10=row.get('q10'), q11=row.get('q11'), q12=row.get('q12'), 
                q13=row.get('q13'), q14=row.get('q14'), q15=row.get('q15'), q16=row.get('q16'), 
                q17=row.get('q17'), q18=row.get('q18'), q19=row.get('q19'), q20=row.get('q20'), 
                q21=row.get('q21'), q22=row.get('q22'), q23=row.get('q23'), q24=row.get('q24'), 
                q25=row.get('q25'), q26=row.get('q26'), q27=row.get('q27'), q28=row.get('q28'), 
                q29=row.get('q29'), q30=row.get('q30'), q31=row.get('q31'), q32=row.get('q32'), 
                q33=row.get('q33'), q34=row.get('q34'), q35=row.get('q35'), q36=row.get('q36'), 
                q37=row.get('q37'), q38=row.get('q38'), q39=row.get('q39'), q40=row.get('q40'), 
                q41=row.get('q41'), q42=row.get('q42'), q43=row.get('q43'), q44=row.get('q44'), 
                q45=row.get('q45'), q46=row.get('q46'), q47=row.get('q47'), q48=row.get('q48'), 
                q49=row.get('q49'), q50=row.get('q50'), q51=row.get('q51'), q52=row.get('q52'), 
                q53=row.get('q53'), q54=row.get('q54'), q55=row.get('q55'), q56=row.get('q56'), 
                q57=row.get('q57'), q58=row.get('q58'), q59=row.get('q59'), q60=row.get('q60'), 
                q61=row.get('q61'), q62=row.get('q62'), q63=row.get('q63'), q64=row.get('q64'), 
                q65=row.get('q65'), q66=row.get('q66'), q67=row.get('q67'), q68=row.get('q68'), 
                q69=row.get('q69'), q70=row.get('q70'), q71=row.get('q71'), q72=row.get('q72'), 
                q73=row.get('q73'), q74=row.get('q74'), q75=row.get('q75'), q76=row.get('q76'), 
                q77=row.get('q77'), q78=row.get('q78'), q79=row.get('q79'), q80=row.get('q80'), 
                q81=row.get('q81'), q82=row.get('q82'), q83=row.get('q83'), q84=row.get('q84'), 
                q85=row.get('q85'), q86=row.get('q86'), q87=row.get('q87'), q88=row.get('q88'), 
                q89=row.get('q89'), q90=row.get('q90'), q91=row.get('q91'), q92=row.get('q92'), 
                q93=row.get('q93'), q94=row.get('q94'), q95=row.get('q95'), q96=row.get('q96'), 
                q97=row.get('q97'), q98=row.get('q98'), q99=row.get('q99'), q100=row.get('q100'), 
                q101=row.get('q101'), q102=row.get('q102'), q103=row.get('q103'), q104=row.get('q104'), 
                q105=row.get('q105'), q106=row.get('q106'), q107=row.get('q107'), q108=row.get('q108'), 
                q109=row.get('q109'), q110=row.get('q110'), q111=row.get('q111'), q112=row.get('q112'), 
                q113=row.get('q113'), q114=row.get('q114'), q115=row.get('q115'), q116=row.get('q116'), 
                q117=row.get('q117'), q118=row.get('q118'), q119=row.get('q119'), q120=row.get('q120'), 
                q121=row.get('q121'),

                # --- Count columns ---
                ok_count=row.get('ok_count'),
                ko_count=row.get('ko_count')
            )
            db.add(record)
            rows_inserted += 1

        # Commit all the new records to the database at once
        db.commit()

        print(f"✅ Successfully inserted {rows_inserted} rows.")


        # Cleanup input file
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info("input file deleted from temporary folder")

        # output_dir = "app/components/generate_tables/data/output"
        # outputfilepath = os.path.join(output_dir, 'audits_concatenated.xlsx')

        # # Cleanup output file
        # if os.path.exists(outputfilepath):
        #     os.remove(outputfilepath)
        #     logging.info("output excel deleted from temporary folder")

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
