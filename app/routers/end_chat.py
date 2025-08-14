"""
This module handles end chat api
"""
from fastapi import APIRouter, HTTPException, Query, status, Depends
from fastapi.responses import JSONResponse
from pydantic import UUID4
import sys

from app.info import auth_info
from app.logger import logging
import app.utils
from app.exception import get_error_message_detail



router = APIRouter()

@router.post("/clear_chat")
async def end_chat(valid_api_key: str = Depends(auth_info.validate_api_key),
    authorization: str = Depends(auth_info.get_auth_token_user),
    userid: UUID4 = Query(..., description="User ID as UUID"),  
    chatid: UUID4 = Query(..., description="Chat ID as UUID")
    
):
    """
    Ends the chat session by clearing history and resetting the retriever chain.
    
    """
    try:

        if not userid or not chatid:
            logging.error("Either user id or chat id is missing")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Both userid and chatid are required to end the chat",
                    "error": True,
                    "data": []
                }
            )
        
        userid = str(userid)
        chatid = str(chatid)
        # Validate inputs

        logging.info(f"Ending chat session for userid: {userid}, chatid: {chatid}")

        # Ensure the user exists in the chat_sessions
        if userid not in app.utils.chat_sessions:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "User has no active chat sessions",
                    "error": True,
                    "data": []
                }
            )

        # Check if the chatid exists for the user
        if chatid not in app.utils.chat_sessions[userid]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "message": "Chat ID not found for this user",
                    "error": True,
                    "data": []
                }
            )

        # Remove the specific chat session
        del app.utils.chat_sessions[userid][chatid]
        logging.info(f"Chat session {chatid} for userid {userid} has been cleared.")

        # If the user has no more active chats, remove them from chat_sessions
        if not app.utils.chat_sessions[userid]:
            del app.utils.chat_sessions[userid]
            logging.info(f"User {userid} has no more active chat sessions and was removed.")

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Chat session ended successfully",
                "error": False,
                "data": {"status": "TRUE"}
            }
        )

    except HTTPException as http_ex:
        error_message = get_error_message_detail(http_ex, sys)
        logging.error(f"Error in end_chat: {error_message}")        
        return JSONResponse(
        status_code=http_ex.status_code,
            content={
                "message": http_ex.detail if isinstance(http_ex.detail, str) else str(http_ex.detail),
                "error": True,
                "data": []
            }
        ) 

    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error in end_chat: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred ",
                "error": True,
                "data": []
            }
        )
