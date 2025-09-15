"""
This module handles API key authentication for the FastAPI application.
"""

from fastapi import Security,Depends
from fastapi.security.api_key import APIKeyHeader

from app.utils import API_KEY
from app.exception import ValidationAPIException,UnauthorizationException, ForbidenException
from app.logger import logging

import jwt
from jwt import ExpiredSignatureError,PyJWTError

from app.info.db_info import get_db

# Secret key to sign the token
SECRET_KEY = "fS-El>*SXZ|cDTD"
ALGORITHM = "HS256"

api_key_header = APIKeyHeader(name="access-token", 
                              auto_error=False, 
                              scheme_name = "API Key")

async def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return True
    else:
        raise ValidationAPIException("Invalid API Key")




