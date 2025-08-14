from app.utils import API_KEY
from fastapi import Security
from app.exception import ValidationAPIException
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="access-token", 
                              auto_error=False, 
                              scheme_name = "API Key")

async def validate_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY:
        return True
    else:
        raise ValidationAPIException("Invalid API Key")
