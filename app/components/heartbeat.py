"""
This module defines background chat session cleanup and heartbeat functionality.
 
It provides:
- A scheduled asynchronous cleanup function to remove inactive user chat sessions.
- A heartbeat function to keep track of user activity and session validity.
"""
 
import os,sys
import shutil
import asyncio
from datetime import datetime, timedelta,timezone
from sqlalchemy.orm import Session
from fastapi import FastAPI, BackgroundTasks,APIRouter
import time
from app.info.db_info import ChatInfo, UploadFileInfo, FileInfo,SessionLocal
from app.components.file_handler import get_sharepoint_context
from app.logger import logging
from app.info.sharepoint_info import SP_RENAULT, SP_LIBRARY_TITLE_UP
from app import utils
from app.exception import InternalError,get_error_message_detail

 
stop_event = asyncio.Event()

 
SP_UPLOADS_BASE_PATH = f"{SP_LIBRARY_TITLE_UP}/{SP_RENAULT}"
SESSION_TIMEOUT = 7200  # Timeout period - seconds 3600


# Cleanup function to remove inactive chat sessions
async def cleanup_inactive_sessions() -> None:
    """
    Periodically scans all chat sessions and removes those that have been inactive for longer than SESSION_TIMEOUT.    
    This is designed to be run as a background task and it frees up memory.
    """
    try:
        while True:  # Keep running in a loop
            current_time = time.time()
            inactive_chats = []

            # Find inactive chat sessions
            for chatid, last_time in list(utils.last_seen.items()):
                if current_time - last_time > SESSION_TIMEOUT:
                    inactive_chats.append(chatid)

            # Remove inactive chat sessions
            for chatid in inactive_chats:
                if chatid in utils.chat_sessions:
                    del utils.chat_sessions[chatid]  # Remove only this chat session
                if chatid in utils.last_seen:
                    del utils.last_seen[chatid]  # Remove last_seen entry
                logging.info(f"Cleared chat session {chatid}")
                print(f"Cleared chat session {chatid}")

            await asyncio.sleep(1800)  # Run cleanup every 30 minutes
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error during cleanup of old chat data : {error_message}")



# Heartbeat function
def heartbeat(chatid: str) -> dict[str, str]:
    """
    Updates the last seen timestamp for a given chat session.

    Parameters:
        chatid (str): The ID of the chat session.

    Returns:
        dict: A message indicating whether the heartbeat was processed or the session was not found.
    """
    # Defensive check to ensure the chat session still exists
    if chatid not in utils.chat_sessions:
        return {"message": "Chat session not found or already ended"}

    # Update last_seen timestamp
    utils.last_seen[chatid] = time.time()
    return {"message": "Heartbeat received"}


 
async def cleanup_old_chat_data(db: Session) -> None:
    """
    Cleans up chat records, SharePoint folders, and local vectorstore data older than 7 days.
   
    Parameters:
        db (Session): SQLAlchemy session instance.
    """
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7) # timedelta(minutes=10)
        old_chats = db.query(ChatInfo).filter(ChatInfo.access_date < cutoff_date).all()
 
        if not old_chats:
            logging.info("No old chats to clean up.")
            return
 
        ctx = get_sharepoint_context()
 
        for chat in old_chats:
            chat_id = str(chat.chat_id)
 
            try:
                chat_meta = db.query(UploadFileInfo).filter(UploadFileInfo.chat_id == chat_id).first()
 
                logging.info(f"Cleaning up data for chat_id: {chat_id}")
 
                condition = not (chat.chat_type == "generic")
                condition1 = not (chat.chat_type == "generic") and not (chat_meta.istext_flag)
 
                # 1. Delete from SharePoint
                if condition1:
                    folder_path = f"{SP_UPLOADS_BASE_PATH}/{chat_id}"
                    folder = ctx.web.get_folder_by_server_relative_url(folder_path)
                    folder.delete_object()
                    ctx.execute_query()
                    logging.info(f"Deleted SharePoint folder: {folder_path}")
 
                # 2. Delete local vectorstore folder PERSIST_DIRECTORY
                if condition1:
                    local_path = os.path.join(utils.PERSIST_DIRECTORY, chat_id)
                    if os.path.exists(local_path):
                        shutil.rmtree(local_path)
                        logging.info(f"Deleted local vectorstore folder: {local_path}")
 
                # 3. Delete from FileInfo
                if condition1:
                    deleted_count = db.query(FileInfo).filter(FileInfo.gu_id.in_(
                        db.query(UploadFileInfo.file_id).filter(UploadFileInfo.chat_id == chat_id)
                        )).filter(FileInfo.source == "uploaded").delete(synchronize_session=False)
                    logging.info(f"Deleted {deleted_count} record(s) from FileInfo table with chatID {chat_id}")

                # 4. Delete from UploadFileInfo
                if condition:
                    deleted_count = db.query(UploadFileInfo).filter(UploadFileInfo.chat_id == chat_id).delete(synchronize_session=False)
                    logging.info(f"Deleted {deleted_count} record(s) from UploadFileInfo table with chatID {chat_id}")
 
                # 5. Delete from ChatInfo
                db.delete(chat)
                logging.info(f"Deleted record(s) from ChatInfo table with chatID {chat_id}")
 
                # 6. Remove from chat_sessions and last_seen
                if condition:
                    if chat_id in utils.chat_sessions:
                        del utils.chat_sessions[chat_id]
                        logging.info(f"Removed chat_id {chat_id} from chat_sessions")

 
            except Exception as e:
                logging.warning(f"Aborted cleanup for chat_id {chat_id} due to error: {e}")
                continue
 
        db.commit()
        logging.info("Old chat data cleanup completed.")
 
    except Exception as e:
        db.rollback()
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error during cleanup of old chat data : {error_message}")
        raise InternalError("Error during cleanup of old chat data : " + str(e))
 
 
# async def periodic_cleanup_old_data():
#     """
#     Background task to run cleanup_old_chat_data once every 24 hours.
#     """
#     while True:
#         db = SessionLocal()
#         try:
#             await cleanup_old_chat_data(db)
#         except Exception as e:
#             logging.error(f"Error while periodic cleaning of old chat data: {e}")
#         finally:
#             db.close()
 
#         await asyncio.sleep(86400)  # Sleep for 24 hours
 
 
 
async def periodic_cleanup_old_data():
    """
    Background task to run cleanup_old_chat_data() once every 24 hours.
    """
    while not stop_event.is_set():
        db = SessionLocal()
        try:
            await cleanup_old_chat_data(db)
        except Exception as e:
            logging.error(f"Error while periodic cleaning of old chat data: {e}")
        finally:
            db.close()
 
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=86400)  # 24 hours
        except asyncio.TimeoutError:
            continue