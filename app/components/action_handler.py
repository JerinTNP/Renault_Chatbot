"""
Action Handler Module
Actions - Generic, Specific, New Proposal
"""
# Import modules
import sys,os,shutil
import re
from typing import List, Dict, Any
from pydantic import UUID4
from fastapi import Depends
from langchain_core.runnables import RunnableSerializable
from langchain_core.messages.base import BaseMessage
from langchain.docstore.document import Document
from langchain_core.messages import HumanMessage,AIMessage
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_openai.chat_models.base import BaseChatOpenAI
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph, START
from langgraph.graph.state import CompiledStateGraph

from app import utils
from app.info.db_info import FileInfo,get_db,ChatInfo,UploadFileInfo
from app.models.vectorstore import FAISS_DB
from app.models.prompts import HISTORY_PROMPT, CONTEXT_PROMPT, ROUTE_PROMPT, NOT_ANSWERABLE_PROMPT																   
from app.info.sharepoint_info import SP_RENAULT, SP_LIBRARY_TITLE_UP
from app.info.agent_info import GraphState, RouteQuery
from app.logger import logging 
from app.exception import InternalError,get_error_message_detail
from app.components.file_handler import get_sharepoint_context


SP_UPLOADS_BASE_PATH = f"{SP_LIBRARY_TITLE_UP}/{SP_RENAULT}"


##################################### COMMON ########################################

def combine_docs(
        docs: List[Document]
        ) -> str:
    """
    Combines retrived documents with information about the source, to feed it into LLM.
 
    Parameters:
        docs (list): list of retrieved documents in langchain Document format.
   
    Returns:
        (str): A large string containing page_content and metadata of all the documents.
    """
    try:
        logging.info("Combining retrieved chunks.")
        # Initialize combined_chunks as empty string
        combined_chunks = ""

        # Loop through each document
        for doc in docs:
           
            text = doc.page_content
            source = doc.metadata['source']
            LinkingUri = doc.metadata['LinkingUri']

            # For pdf linking_uri will be empty. In that case convert the source path into link.
            if LinkingUri == "":
                file_link = source.replace(' ',"%20")
            else:
                file_link = LinkingUri
            
            # For ppt or pptx, use 'slide number', for other docs use 'page number' 
            if source.endswith(".ppt") or source.endswith(".pptx"):
                page_number = f"slide number : {doc.metadata['page']}"
            else:
                page_number = f"page number : {doc.metadata['page']}"

            # Add data from the documents to the combined_chunks.
            combined_chunks += f"\n Chunk Start \n{text}\n The above context if from the file: {file_link}, {page_number}\n Chunk end \n"
       
        return combined_chunks
    
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while combining retrieved chunks : " + str(e))


async def get_response(
        chain: RunnableSerializable[Any, BaseMessage],
        chat_history: List[BaseMessage],
        question: str
        ) -> tuple[list, str]:
    """
    Gets response from the previously created async chain.
 
    Parameters:
        chain (RunnableSerializable): Langchain chain object
        chat_history (list): List of chat history.
        question (str): User query
   
    Returns:
        (list, str): Updated chat history, answer to the query.
    """
    try:
        # Gets response by invoking the chain
        response = await chain.ainvoke(
            {"chat_history": chat_history, "input": question}
        )
        logging.info("Response generated successfully")

        # Append respose to chat history
        chat_history.append(HumanMessage(content = question))
        chat_history.append(AIMessage(content=response.content))
        logging.info("Response added to chat history.")

        # Get text result
        result = response.content
        print(f"result :\n{result}")

        # return chat history and result
        return chat_history, result
    
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while getting response from the LLM: " + str(e))


###############  from generic ###########

def create_chain(
        vectorstore: FAISS_DB,
        chat_history: list = None,
        chat_model: BaseChatOpenAI = utils.CHAT_MODEL,
        history_prompt: ChatPromptTemplate = HISTORY_PROMPT,
        context_prompt: ChatPromptTemplate = CONTEXT_PROMPT
        ) -> tuple[RunnableSerializable[Any, BaseMessage], list]:
    """
    Creates an async chain which modifies question using chat history, retrieves relevant documents, and gets a response for the query.
 
    Parameters:
        vectorstore (FAISS_BD): The vectorstore.
        chat_history (list): Chat history.
        chat_model (BaseChatOpenAI): OpenAI chat model that is used to create the chain.
        history_prompt (ChatPromptTemplate): The prompt used to change the question using chat history.
        context_prompt (ChatPromptTemplate): The prompt used to get answer to the question based on the retrieved context.
 
    Returns:
        (chain, list): Langchain chain which retrieves documents and gives responses, A list of chat history.
    """
    try:
        logging.info(f"Creating chain")

        # If chat history is not passed, create chat history
        if chat_history is None:
            chat_history = [HumanMessage(content="Hi"), AIMessage(content="Hi, How can I assist you")]

        # Define retriever
        retriever = vectorstore.vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 10})
 
        # Get text from gpt response
        def get_content_from_response(response):
            return response.content
 
        # Print the restructured query
        def print_restructured_qn(qn):
            print(f"Restructured_qn : {qn}")
            return qn
 
        # Define history chain for changing user query by using chat history
        chat_history_chain = (
            RunnablePassthrough()
            | history_prompt
            | chat_model
            | RunnableLambda(get_content_from_response)
        )
 
        # Define retrieval chain for retrieving data from vectorstore and geting answer to the query.
        retrieval_chain = (
            {
                "context": retriever | RunnableLambda(combine_docs),
                "input": RunnablePassthrough()
            }
            | context_prompt
            | chat_model
        )
 
        # Final chain combining chat_history_chain and retrieval_chain.
        # This chain first modifies question using chat history,
        # then get answer by retrieving data from vectorstore using the modified question.
        custom_chain = (
            chat_history_chain
            | RunnableLambda(print_restructured_qn)
            | retrieval_chain
        )
        logging.info(f"Chain created with vectorstore : {vectorstore.persist_directory}")
 
        return custom_chain, chat_history
    
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while creating history-aware retriever chain: " + str(e))
   

##################################### SPECIFIC ########################################

def search_files_by_keyword(
    db: Session,
    keyword: str,
    limit: int = 10,
) -> List[Dict[str, any]]:
    """
    Searches for files in the database based on a keyword, returning exact and partial matches.
 
    Exact matches are determined by checking if the file name contains the full keyword (case-insensitive).
    Partial matches are found by splitting the keyword into parts and searching for file names containing any of those parts,
    excluding any results already found in exact matches.
 
    Parameters:
        db (Session)    : SQLAlchemy database session used to query the FileInfo table.
        keyword (str)   : The keyword used to search file names.
        limit (int)     : Optional. Maximum number of results to return (default is 10).
 
    Returns:
        (List[Dict[str, any]]) : A list of dictionaries with file details. Each dictionary contains:
                                - "file_name": Name of the file
                                - "gu_id": Unique identifier of the file (converted to string)
                                - "link_uri": Either the link URI or the local file path
    """
    try:
        logging.info(f"Searching files with matchimg keyword : {keyword}")

        # Search for exact match filenames
        sentence = keyword.split(".")[0]

        exact_matches = db.query(FileInfo.file_name, FileInfo.gu_id, FileInfo.link_uri, FileInfo.file_path).filter(
            (FileInfo.user_id == None) , FileInfo.file_path.like(f"%{SP_RENAULT}%"), FileInfo.file_name.ilike(f'%{sentence}%')
        ).all()

        logging.info(f"{len(exact_matches)} exact matches found")
 
        # Splits the sentence for partial search
        parts = [p for p in re.split(r'[\s\W]+',sentence)]
       
        # Get partially matching filenames
        partial_matches_queries = []
 
        for part in parts:
            partial_matches_queries.append(
                db.query(FileInfo.file_name, FileInfo.gu_id, FileInfo.link_uri, FileInfo.file_path).filter(
                    FileInfo.file_name.op("~*")(fr'(^|[^a-zA-Z]){part}') ,
                    FileInfo.file_path.like(f"%{SP_RENAULT}%"),
                    (FileInfo.user_id == None),
                    # Exclude exact matches to avoid duplicates
                    ~FileInfo.file_name.ilike(f'%{sentence}%')
                )
            ) 
 
        # Union all partial match queries
        partial_matches_query = partial_matches_queries[0]
        for query in partial_matches_queries[1:]:
            partial_matches_query = partial_matches_query.union(query)
		
        # Execute the query
        partial_matches = partial_matches_query.limit(limit).all()
        #print(partial_matches)
   
        logging.info(f"{len(partial_matches)} partial matches found")

        # Combine results
        results = []
   
        # Add exact matches first
        for file_name, gu_id, link_uri, file_path in exact_matches:
            if link_uri:
                results.append((file_name, gu_id, link_uri))
           
            else:
                results.append((file_name, gu_id, file_path))
 
        # Add partial matches that aren't already in results
        existing_guids = {guid for _, guid, _ in results}
        for file_name, gu_id, link_uri, file_path in partial_matches:
            if gu_id not in existing_guids:
                if link_uri:
                    results.append((file_name, gu_id, link_uri))
               
                else:
                    results.append((file_name, gu_id, file_path))
                existing_guids.add(gu_id)
   
        # Limit the total number of results
        results = results[:limit]
   
        # Format the results as a list of dictionaries
        file_responses = [
            {"file_name": file_name, "gu_id": str(gu_id), "link_uri": link_uri}
            for file_name, gu_id, link_uri in results
        ]
 
        def sort_key(d):
            """
            Sort files based on the given keyword.
            More parts = higher priority (-count_found)
            Earlier position = better (lower pos)
            """
            file_name = d['file_name'].lower()
            key = []
            count_found = 0
 
            # Loop parts in order (respects parts list order)
            for portion in parts:
                search_part = portion.lower()
                pos = file_name.find(search_part)
 
                if pos != -1:
                    count_found += 1
                    key.append(pos)
                else:
                    key.append(float('inf'))  # Penalize missing
 
            return (-count_found, *key)
 
        file_responses.sort(key=sort_key)
 
        return file_responses
 
    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while searching for similar files: " + str(e))
    


# Copying Embeddings
async def single_file_loader_embedding(
        gu_id: UUID4,
        vectorstore: FAISS_DB,
        local_faiss: FAISS_DB
        ) -> FAISS_DB:
    """
    Copies embeddings of a single file from a previously persisted vectorstore into another vectorstore.

    Parameters:
        gu_id (UUID4): The uuid of the file to load.
        vectrorstore (faiss db): The vectorstore from which file to be loaded.
        local_faiss (faiss db): Local vectorstore created for loading the selected file.

    Returns:
        (faiss db) : In memory faiss db with the specified file only.
    """
    try:
        # Get a list of gu_ids of files present inside the local_faiss
        _, gu_id_list = await local_faiss.get_files_in_vectorstore()
        
        logging.info("Files copying to new vectorstore")
        # Add embeddings of the file to local_faiss if the file does not exist in it.
        if gu_id not in gu_id_list:

            # get embeddings from the vectorstore where embeddings of the file is present.
            embeddings, metadatas, ids = await vectorstore.get_embeddings_and_ids(gu_id)
            
            # Add the data of the specified file into local_faiss vectorstore
            if embeddings and metadatas and ids:
                local_faiss.vectorstore.add_embeddings(text_embeddings=embeddings, metadatas=metadatas, ids=ids)
                logging.info(f"Files copied to the new vectorstore : {set(metadata['source'] for metadata in metadatas)}")

        return local_faiss

    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while creating an in memory vectorstore with single file : " + str(e))


async def create_specific_chain(
        gu_id: str, 
        vectorstore: FAISS_DB, 
        persist_path: str
        ) -> tuple[RunnableSerializable[Any, BaseMessage], list]:
    """
    Loads embeddings of a the specified file only into another vectorstore and creates a chain to get answer from that bd only.

    Parameters:
        gu_id (str): The guid of the file to load.
        vectrorstore (faiss db): The vectorstore from which file to be loaded.
        persist_path (str): Path to which the single file vectorstore is to be saved.

    Returns:
        (chain, list): A chain for retrieving relevent docs and answering the question, A list of chat history.
    """

    try:
        # Create new vectorstore to which the embeddings of the specified files are copied
        local_faiss = FAISS_DB(embedding_function=utils.EMBEDDINGS, persist_directory=persist_path)
        local_faiss.load()
        logging.info(f"New vectrstore created at : {persist_path}")

        # Copy embeddings of the file to the new vectorstore
        local_faiss = await single_file_loader_embedding(gu_id=gu_id, vectorstore=vectorstore, local_faiss=local_faiss)
        local_faiss.save_local()

        # Create chain using the new vectorstore
        retriever_chain,chat_history=create_chain(vectorstore=local_faiss)
        return retriever_chain, chat_history

    except Exception as e:
        error_message = get_error_message_detail(e, sys)
        logging.error(error_message)
        raise InternalError("An error occurred while creating specific method retriever chain : " + str(e))
    


def embed_failure_cleaning(db: Session,chatid:UUID4 = None, userid:UUID4 = None) -> None:
    """
    Remove saved data from DB if embedding fails.
    Parameters:
        db (Session)    : SQLAlchemy database session used to query the FileInfo table.
        chatid (UUID4)  : The chat ID
        userid (UUID4)  : The user ID
    """

    logging.info(f"Removing saved chat data for {chatid} due to embedding failure")
    # 1. Delete from SharePoint
    try:
        ctx = get_sharepoint_context()
        folder_path = f"{SP_UPLOADS_BASE_PATH}/{chatid}"
        folder = ctx.web.get_folder_by_server_relative_url(folder_path)
        folder.delete_object()
        ctx.execute_query()
        logging.info(f"Deleted SharePoint folder: {folder_path}")
    except Exception as sp_err:
        logging.warning(f"Failed to delete SharePoint folder {chatid}: {sp_err}")

    # 2. Delete local vectorstore folder
    try:
        local_path = os.path.join(utils.UPLOAD_DIRECTORY, str(chatid))
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
            logging.info(f"Deleted local vectorstore folder: {local_path}")
    except Exception as fs_err:
        logging.warning(f"Failed to delete local folder {chatid}: {fs_err}")

    # 3. Delete from FileInfo
    deleted_count = db.query(FileInfo).filter(FileInfo.gu_id.in_(
        db.query(UploadFileInfo.file_id).filter(UploadFileInfo.chat_id == chatid)
    )).filter(FileInfo.source == "uploaded").delete(synchronize_session=False)
    logging.info(f"Deleted {deleted_count} record(s) from FileInfo table for chat ID {chatid}")

    # 4. Delete from UploadFileInfo
    deleted_count = db.query(UploadFileInfo).filter(UploadFileInfo.chat_id == chatid).delete(synchronize_session=False)
    logging.info(f"Deleted {deleted_count} record(s) from UploadFileInfo table for chatID {chatid}")

    # 5. Delete from ChatInfo
    deleted_count = db.query(ChatInfo).filter(ChatInfo.chat_id == chatid).delete(synchronize_session=False)
    logging.info(f"Deleted {deleted_count} record(s) from ChatInfo table for chatID {chatid}")

    # 6. Remove from chat_sessions
    if userid in utils.chat_sessions and chatid in utils.chat_sessions[userid]:
        del utils.chat_sessions[userid][chatid]
        logging.info(f"Removed chat_id {chatid} from chat_sessions for user {userid}")

        if not utils.chat_sessions[userid]:  # Clean up empty user entry
            del utils.chat_sessions[userid]
            logging.info(f"Removed user {userid} from chat_sessions (no chats left)")