""" 
This module defines variables for establishing sharepoint connection.
"""

import os
import sys
from os.path import join, dirname
from dotenv import load_dotenv

from app.logger import logging
from app.exception import get_error_message_detail, BadRequestError

dotenv_path = join(dirname(__file__), '.env')

try:
    # Loading the credentials
    load_dotenv(dotenv_path)

    SITE_URL = os.getenv("SITE_URL")
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    SHAREPOINT_URL = os.getenv("SHAREPOINT_URL")

    # Sharepoint folders
    SP_LIBRARY_TITLE = os.getenv("SP_LIBRARY_TITLE")
    SP_LIBRARY_TITLE_UP = os.getenv("SP_LIBRARY_TITLE_UP")

    SP_RENAULT = os.getenv("SP_RENAULT")
    

    if not SITE_URL or not CLIENT_ID or not CLIENT_SECRET or not SHAREPOINT_URL:
        logging.error("One or more environment variables are missing at SharePoint")
        raise BadRequestError("One or more environment variables are missing")

    logging.info("SharePoint credentials loaded successfully")


except Exception as e:
    error_message = get_error_message_detail(e, sys)
    logging.error(error_message)
    raise BadRequestError("Error while loading SharePoint credentials: " + str(e))