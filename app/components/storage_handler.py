"""
This module establishes Sharepoint connection.
"""
# Sharepoint Connection
import sys

from office365.sharepoint.client_context import ClientContext
from office365.runtime.auth.client_credential import ClientCredential


from app.logger import logging
from app.exception import get_error_message_detail, CustomException

from fastapi import status,HTTPException
from fastapi.responses import JSONResponse
from app.exception import InternalError
def connect_sp(client_id, client_secret, site_url):
    """
    Establishes a connection to a SharePoint site using client credentials.

    Args:
        client_id (str): The client ID of the registered Azure AD application.
        client_secret (str): The client secret associated with the Azure AD application.
        site_url (str): The URL of the SharePoint site to connect to.

    Returns:
        ClientContext: An authenticated SharePoint client context object.
    """
    try:
        credentials = ClientCredential(client_id, client_secret)
        ctx = ClientContext(site_url).with_credentials(credentials)

        return ctx
    
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error while establishing sharepoint connection " + str(e))