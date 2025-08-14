from fastapi.responses import JSONResponse
from fastapi.requests import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.exception import ValidationAPIException, UnauthorizationException, BadRequestError, InternalError, ForbidenException
from starlette import status
from app.logger import logging
#from fastapi.exceptions import RequestValidationError


class ValidationExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValidationAPIException as exc:
            logging.error(f"API Key Validation error in endpoint [{request.url.path}] with error as [{exc.errors}]")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": exc.errors,
                    "error": True,
                    "data": []
                }
            )
        
        except UnauthorizationException as exc:
            logging.error(f"Authorisation error in endpoint [{request.url.path}] with error as [{exc.errors}]")    
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": exc.errors,
                    "error": True,
                    "data": []
                }
            )
        except BadRequestError as exc :
            logging.error(f"A bad request error in endpoint [{request.url.path}] with error as [{exc.errors}]")    
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": exc.errors,
                    "error":True,
                    "data": []
                        }
                    )

        except ForbidenException as exc :
            logging.error(f"A mismatching keys error in endpoint [{request.url.path}] with error as [{exc.errors}]")    
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "message": exc.errors,
                    "error":True,
                    "data": []
                        }
                    )

        except InternalError as exc :
            logging.error(f"An internal error in endpoint [{request.url.path}] with error as [{exc.errors}]")    
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "message": "Internal error occured",
                    "error":True,
                    "data": []
                        }
                    )
