"""
Logger Module

- Creates log for each run of the program
- Filenames based on current time stamp
- Log line in the format of datetime - filename - function - message 
"""

import logging
import os
from datetime import datetime

LOG_FILE=f"{datetime.now().strftime('%d_%m_%Y_%H_%M_%S')}.log"
logs_path=os.path.join(os.getcwd(),"logs")
os.makedirs(logs_path,exist_ok=True)
LOG_FILE_PATH=os.path.join(logs_path,LOG_FILE)

logging.basicConfig(
    filename=LOG_FILE_PATH,
    format="[ %(asctime)s ] - %(filename)s - %(funcName)s - %(message)s",
    level=logging.INFO
)
