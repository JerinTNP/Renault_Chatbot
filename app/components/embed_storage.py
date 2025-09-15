import sys
import asyncio

from app.models.vectorstore import FAISS_DB
from app.components.embedder import DATA_LOADER_SP
from app.info.sharepoint_info import (
    CLIENT_ID, CLIENT_SECRET, SITE_URL, SHAREPOINT_URL, SP_LIBRARY_TITLE, SP_RENAULT
    )
from app.utils import (
    RENAULT_DB
)

from app.logger import logging
from app.exception import get_error_message_detail



data_loader = DATA_LOADER_SP(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    site_url=SITE_URL,
    sharepoint_url=SHAREPOINT_URL
    )

asyncio.run(data_loader.data_to_db_sp(
    sp_library_title=SP_LIBRARY_TITLE,
    sp_folder_relative_path=SP_RENAULT,
    vectorstore=RENAULT_DB,
    source="sharepoint"
))


