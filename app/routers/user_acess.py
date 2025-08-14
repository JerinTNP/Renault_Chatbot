"""
This module handles user authentication in the FastAPI application.
"""
import sys
import jwt
import datetime
import secrets
from jwt import ExpiredSignatureError, InvalidTokenError

from app.logger import logging
from app.info.login_info import LoginInfo
from app.info import db_info,auth_info
from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.responses import JSONResponse

from fastapi import Header
# from starlette import status
# from starlette.responses import JSONResponse

from sqlalchemy.orm import Session
from app.exception import get_error_message_detail,InternalError
from pydantic import UUID4
router = APIRouter()


## Secret key to sign the token
# SECRET_KEY = secrets.token_urlsafe(32)
SECRET_KEY = "fS-El>*SXZ|cDTD"
ALGORITHM = "HS256"
TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours 


async def generate_jwt(
    user_id: str,
    username: str,
    name: str,
    db: Session,
    expires_in: int = TOKEN_EXPIRY
) -> str:
    """Generate JWT token for the logged-in user."""
    try:
        userinfo = db.query(db_info.UserInfo).filter(db_info.UserInfo.user_id == user_id).first()
        roleinfo = db.query(db_info.RoleInfo).filter(db_info.RoleInfo.role_id == userinfo.role_id).first()
        departmentinfo = db.query(db_info.DepartmentInfo).filter(db_info.DepartmentInfo.department_id == userinfo.department_id).first()

        payload = {
            "user_id": str(user_id),
            "username": username,
            "name": name,
            "role": roleinfo.role_name,
            "department_id": str(departmentinfo.department_id),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=expires_in),
            "iat": datetime.datetime.now(datetime.timezone.utc)
        }

        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token

    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Error in generate_jwt: {error_message}")
        raise InternalError("An error occurred while generating JWT: " + str(error_message))


@router.post("/signin")
async def login_user( 
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    db: Session = Depends(db_info.get_db), 
    logininfo: LoginInfo = None
):
    """Handles user login, validates credentials, and issues JWT token.

    Args:
        valid_api_key (bool): API key validation dependency.
        db (Session): Database session dependency.
        logininfo (LoginInfo): Login request containing username and password.

    Returns:
        JSONResponse: Returns success or failure message with JWT token.
    """

    errmsg = "Invalid username or password."

    try:
        if logininfo == None:
            logging.error("Invalid input")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "message": "Invalid input",
                    "error": True,
                    "data": []

                }
            )

        # Fetch user info from the database
        userinfo = db.query(db_info.UserInfo).filter(db_info.UserInfo.email == logininfo.username).first()


        if not userinfo:
            logging.error(f"Login failed. {errmsg} - User not found.")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": errmsg,   
                    "error": True,
                    "data": []
                }
            )

        # Check user role
        user_role_info = db.query(db_info.RoleInfo).filter(
            (db_info.RoleInfo.role_id == userinfo.role_id), (db_info.RoleInfo.status == True)
            ).first()
       
        # Check if the user is an admin
        if not user_role_info or user_role_info.role_name.lower() != "user":
            logging.error(f"Login failed - User is an Admin")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "message": "Login failed - User is an Admin",  
                    "error": True,
                    "data": []
                }
            )

        # Check if hashed passwords match
        if logininfo.password == userinfo.pwd:
            # generate jwt
            jwt_token = await generate_jwt(
                user_id=userinfo.user_id,
                username=userinfo.user_name,
                name=userinfo.name,
                db=db
            )

            # insert a new signin record
            signininfo = db_info.SigninInfo(
                user_id=userinfo.user_id,
                user_name=userinfo.user_name,
                token=jwt_token
            )
 
            db.add(signininfo)
            db.commit()
            db.refresh(signininfo)

            ret_content = {
                "user": userinfo.user_name,
                "firstname": userinfo.fname,
                "lastname": userinfo.lname,
                "name": f"{userinfo.fname or ''} {userinfo.lname or ''}".strip(),
                "organization": userinfo.organization,
                "email": userinfo.email,
                "token": jwt_token
            }

            logging.info(f"Login Success. Details: {ret_content}")
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Signin success",   
                    "error": False,
                    "data": ret_content
                }
            )
        else:
            logging.error(f"Login failed. {errmsg}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": errmsg,   
                    "error": True,
                    "data": []
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

    except Exception as exp:
        error_message = get_error_message_detail(exp, sys)
        logging.error("Exception occurred in signin. Error Message: " + error_message)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred",
                "error": True,
                "data": []
            }
        )


@router.post("/signout")
async def logout_user(
    valid_api_key: bool = Depends(auth_info.validate_api_key),
    authorization: str = Depends(auth_info.get_auth_token), 
    db: Session = Depends(db_info.get_db)
):
    """
    Logs out a user by invalidating their JWT token.

    This endpoint removes the user's session information from the database,
    effectively logging them out.

    Args:
    - valid_api_key (bool): Validated API key dependency.
    - authorization (str): JWT token extracted from the Authorization header.
    - db (Session): Database session dependency.

    Returns:
    - 200 OK: If logout is successful.
    - 400 Bad Request: If the JWT token is invalid or no active session is found.
    - 403 Forbidden: If an invalid API key is provided.
    """
    try:

        try:
								 
            payload = jwt.decode(authorization, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
            user_id = payload.get("user_id")
        except (ExpiredSignatureError, InvalidTokenError) as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(f"Invalid JWT token during logout: {error_message}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "message": "Invalid JWT token",
                    "error": True,
                    "data": []
                }
            )
        						   
        signin_info = db.query(db_info.SigninInfo).filter(db_info.SigninInfo.token == authorization).first()


        if signin_info:
            db.delete(signin_info)
            db.commit()
 
            logging.info(f"User with userid {user_id} logged out successfully from this session")

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Logout success",
                    "error": False,
                    "data": []
                }
            )

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "message": "This user has not logged in.",
                "error": True,
                "data": []
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

    except Exception as exp:
        error_message = get_error_message_detail(exp, sys)
        logging.error(f"Exception occurred in signout user. Error Msg: {error_message}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "An internal server error occurred",
                "error": True,
                "data": []
            }
        )
