import os
import sys
import re
from dotenv import load_dotenv

from langchain_openai.embeddings.azure import AzureOpenAIEmbeddings
from langchain_openai import AzureChatOpenAI

from app.models.vectorstore import FAISS_DB
from app.logger import logging
from app.exception import get_error_message_detail, InternalError

chat_sessions = {}  # Store active chat sessions
last_seen = {} # Track last activity timestamps for each chatid

# load .env file data
try:
   
    #Loading the credentials
    load_dotenv()

    DATABASE_URL = os.getenv('DATABASE_URL')
    API_KEY = os.getenv("API_KEY")

    OPENAI_API_TYPE = os.getenv("OPENAI_API_TYPE")
    OPENAI_API_VERSION = os.getenv("OPENAI_API_VERSION")
    OPENAI_API_BASE = os.getenv("AZURE_OPENAI_ENDPOINT")
    OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
    DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")

    EMBEDDING_API_VERSION = os.getenv("EMBEDDING_API_VERSION")
    EMBEDDING_OPENAI_API_KEY = os.getenv("EMBEDDING_OPENAI_API_KEY")
    EMBDDDING_ENDPOINT = os.getenv("EMBDDDING_ENDPOINT")
    EMBEDDINGS_DEPLOYMENT_NAME = os.getenv("EMBEDDINGS_DEPLOYMENT_NAME")

    SITE_URL = os.getenv("SITE_URL")
    SHAREPOINT_URL = os.getenv("SHAREPOINT_URL")

    # FAISS Storage directory
    PERSIST_DIRECTORY = os.getenv("PERSIST_DIRECTORY")

except Exception as error:
    error_message = get_error_message_detail(error, sys)
    logging.error(f"Error while getting .env data: {error_message}")
    raise InternalError("An error occurred while getting .env data: " + str(error))


#Creating embedding model function with AzureOpenAIEmbeddings() with Azure credentials
EMBEDDINGS = AzureOpenAIEmbeddings(
    azure_endpoint=EMBDDDING_ENDPOINT,
    api_version=EMBEDDING_API_VERSION,
    api_key=EMBEDDING_OPENAI_API_KEY,
    openai_api_type = OPENAI_API_TYPE,
    model=EMBEDDINGS_DEPLOYMENT_NAME
)

#Creating model (LLM)
CHAT_MODEL = AzureChatOpenAI(
    azure_endpoint=OPENAI_API_BASE,
    api_key=OPENAI_API_KEY,
    api_version=OPENAI_API_VERSION,
    openai_api_type=OPENAI_API_TYPE,
    azure_deployment=DEPLOYMENT_NAME,
    temperature=0
)

try:
    RENAULT_DB = FAISS_DB(embedding_function=EMBEDDINGS, persist_directory=PERSIST_DIRECTORY)
    RENAULT_DB.load()
    
except Exception as e:
    error_message = get_error_message_detail(e, sys)
    logging.error(error_message)
    raise InternalError(f"Error while loading vectorstore : {str(error_message)}")

 
def output_source_correction(
        result:str
        ) -> str:
    """
    Corrects the link of sources provided in the response.

    Parameters:
        result (str): Response from the chat model.
    
    Returns:
        (str): Respone with corrected source link.
    """
    try:
        pattern1 = fr"\[{SITE_URL}.*\]\({SITE_URL}.*\)"
        pattern2 = fr"\[[^]]+\]\({SITE_URL}.*\)"
        # pattern = fr"\[.*?\]\({SITE_URL}.*?\)"
    
        # Check if the pattern is present in any part of the string
        match1 = re.search(pattern1, result)
        match2 = re.search(pattern2, result)
    
        if match1:
            print("Pattern found!")
            final_out = result
    
            match_obj = match1.group()
            linking_uri = match_obj.split("]")[0].split("[")[-1]
            file_name = linking_uri.split("/")[-1]
    
            replacement_word = f"[{file_name}]({linking_uri}) :"
    
            final_out = final_out.replace(match_obj, replacement_word, 1)
    
        elif match2:
            print("Pattern found!")
            final_out = result
    
        else:
            lines = result.splitlines()
            final_lines = []
    
            for line in lines:
                splits = line.split()
                new_splits = []
            
                for split in splits:
                    if SHAREPOINT_URL in split:
                        # Remove any commas from the URL and extract the filename
                        if split.endswith(","):
                            split = split.rstrip(',')
                        if split.endswith(":"):
                            split = split.rstrip(':')
                    
                        if "?" in split:
                            # Extract the filename before the query string
                            filename = split.split("?")[0].split("/")[-1]
                        else:
                            filename = split.split("/")[-1]
    
                        # Clean up the filename for Markdown formatting
                        filename = filename.replace("%20", "_").replace(" ", "_")
                    
                        # Format the Markdown link correctly
                        new_split = f"[{filename}]({split}) :"
                        new_splits.append(new_split)
            
                    else:
                        new_splits.append(split)
            
                # Join the processed splits back into a single line
                line_out = " ".join(new_splits)
                final_lines.append(line_out)
        
            # Combine all lines into the final output
            final_out = "\n".join(final_lines)
    
        return final_out

    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(f"Output source correction faild : {error_message}")
        return result

 
