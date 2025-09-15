"""
Action Handler Module
Actions - Generic, Specific, New Proposal
"""
# Import modules
import sys,os,shutil
import re
import json
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
from app.info import db_info
from sqlalchemy import text

from app import utils
from app.info.db_info import FileInfo,get_db,ChatInfo,UploadFileInfo
from app.models.vectorstore import FAISS_DB
from app.models.prompts import HISTORY_PROMPT, CONTEXT_PROMPT, ROUTE_PROMPT_RENAULT, NOT_ANSWERABLE_PROMPT, SQL_PROMPT																   
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
        logging.info(f"New vectorstore created at : {persist_path}")

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
    


def embed_failure_cleaning(db: Session,chatid:UUID4 = None) -> None:
    """
    Remove saved data from DB if embedding fails.
    Parameters:
        db (Session)    : SQLAlchemy database session used to query the FileInfo table.
        chatid (UUID4)  : The chat ID
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
    if chatid in utils.chat_sessions:
        del utils.chat_sessions[chatid]
        logging.info(f"Removed chat_id {chatid} from chat_sessions")




################# RENAULT SPECIFIC ##############

########################################
# DB Query Executor
########################################
def run_sql_query(query: str):
    """Executes the generated SQL query on PostgreSQL and returns the result."""
    logging.info(f"Executing SQL: {query}")
    try:
        with db_info.SessionLocal() as db:
            result = db.execute(query).mappings().all()
            return [dict(row) for row in result] if result else []
    except Exception as e:
        logging.error(f"SQL Execution Error: {e}")
        return {"error": str(e)}


########################################
# Postgres Chain Creator
########################################
from sqlalchemy import text  # <-- add this at the top

def create_postgres_chain(
    chat_history: list = None,
    chat_model: BaseChatOpenAI = utils.CHAT_MODEL,
    sql_prompt: ChatPromptTemplate = SQL_PROMPT
) -> tuple[Any, list]:
    """
    Creates a chain that:
    1. Reformulates question based on chat history.
    2. Generates SQL using LLM.
    3. Executes SQL on PostgreSQL.
    4. Returns the database result.
    """
    try:
        logging.info("Creating Postgres chain")

        if chat_history is None:
            chat_history = []

        def get_content_from_response(response):
            return response.content.strip()

        def clean_sql(sql: str) -> str:
            """Remove markdown code fences and optional 'sql' tag."""
            sql = sql.strip()
            if sql.startswith("```"):
                sql = sql.strip("`")  # remove all backticks
                if sql.lower().startswith("sql"):
                    sql = sql[3:]
            sql = sql.strip()
            return sql


        def execute_sql(sql: str):
            logging.info(f"Executing SQL: {sql}")
            try:
                sql = clean_sql(sql)  # Remove ```sql fences etc.
                with db_info.get_db_context() as db:
                    result = db.execute(text(sql))
                    #  Convert RowMapping to dict
                    rows = [dict(row) for row in result.mappings().all()]
                    return AIMessage(content=json.dumps(rows, indent=2, default=str))
            except Exception as e:
                logging.error(f"SQL execution error: {e}")
                return AIMessage(content=f"Error executing SQL: {e}")


        sql_chain = (
            RunnablePassthrough()
            | sql_prompt
            | chat_model
            | RunnableLambda(get_content_from_response)
        )

        retrieval_chain = sql_chain | RunnableLambda(execute_sql)

        logging.info("Postgres chain created successfully")
        return retrieval_chain, chat_history

    except Exception as e:
        logging.error(f"Error creating Postgres chain: {e}")
        raise


########################################
# Agent Creator
########################################
async def create_renault_agent(
    existing_file_db: Any = None,
    gu_id: UUID4 = None,
    persist_path: str = None,
    chat_history: list = None,
    chat_model: BaseChatOpenAI = utils.CHAT_MODEL,
    not_answerable_prompt: ChatPromptTemplate = NOT_ANSWERABLE_PROMPT,
    route_prompt: ChatPromptTemplate = ROUTE_PROMPT_RENAULT,
) -> tuple[CompiledStateGraph, list]:
    """
    Creates Renault chatbot agent for routing between:
    - vectorstore (file-specific) if available
    - Postgres (aggregate queries)
    - not_answerable (fallback)
    """
    try:
        # Init chat history if empty
        if chat_history is None:
            chat_history = [
                HumanMessage(content="Hi"),
                AIMessage(content="Hi, how can I assist you?")
            ]

        # If we have a vectorstore, ensure it's loaded
        if existing_file_db and gu_id and persist_path:
            logging.info(f"Creating new vectorstore at {persist_path}")
            local_faiss = existing_file_db.__class__(
                embedding_function=utils.EMBEDDINGS,
                persist_directory=persist_path
            )
            local_faiss.load()
            local_faiss = await single_file_loader_embedding(
                gu_id, existing_file_db, local_faiss
            )
            local_faiss.save_local()
            existing_file_db = local_faiss
        elif existing_file_db:
            logging.info("Using provided vectorstore")

        # --- Create chains ---
        file_specific_chain = None
        if existing_file_db:
            logging.info("Creating file-specific retrieval chain")
            file_specific_chain, chat_history = await create_specific_chain(
                gu_id, existing_file_db, persist_path
            )

        postgres_chain, _ = create_postgres_chain(chat_history)
        not_answerable_chain = not_answerable_prompt | chat_model

        # Router model
        structured_model_router = chat_model.with_structured_output(RouteQuery)
        question_router = route_prompt | structured_model_router

        # --- Retrieval functions ---
        async def file_vector_retrieve(state: GraphState) -> GraphState:
            logging.info("---RETRIEVE FILE VECTOR---")
            question = state["question"]
            chat_history = state["chat_history"]
            chat_history, response = await get_response(
                chain=file_specific_chain,
                chat_history=chat_history,
                question=question
            )
            return GraphState(chat_history=chat_history, response=response)

        async def postgres_retrieve(state: GraphState) -> GraphState:
            logging.info("---RETRIEVE FROM POSTGRES---")
            question = state["question"]
            chat_history = state["chat_history"]
            chat_history, results = await get_response(
                chain=postgres_chain,
                chat_history=chat_history,
                question=question
            )
            return GraphState(chat_history=chat_history, response=str(results))

        async def not_answerable_generate(state: GraphState) -> GraphState:
            logging.info("---NOT ANSWERABLE---")
            question = state["question"]
            chat_history = state["chat_history"]
            chat_history, response = await get_response(
                chain=not_answerable_chain,
                chat_history=chat_history,
                question=question
            )
            return GraphState(chat_history=chat_history, response=response)

        # --- Router ---
        async def route_question(state: GraphState) -> str:
            try:
                logging.info("---ROUTE QUESTION---")

                ################# TEST ############
                logging.info("---FORCE ROUTE TO POSTGRES FOR TESTING---")
                return "postgres_retrieve"
                ##################################

                question = state["question"]

                # Route based on whether file data is available
                if existing_file_db:
                    valid_routes = ["postgres_retrieve", "file_vector_retrieve"]
                else:
                    valid_routes = ["postgres_retrieve"]

                source = await question_router.ainvoke({"question": question})

                if source.datasource in valid_routes:
                    return source.datasource
                else:
                    return "not_answerable"

            except Exception as e:
                logging.error(get_error_message_detail(e))
                raise InternalError(f"Routing error: {e}")

        # --- Build Graph ---
        workflow = StateGraph(GraphState)

        workflow.add_node("postgres_retrieve", postgres_retrieve)
        workflow.add_node("not_answerable", not_answerable_generate)

        if existing_file_db:
            workflow.add_node("file_vector_retrieve", file_vector_retrieve)

        # Conditional edges
        edge_map = {
            "postgres_retrieve": "postgres_retrieve",
            "not_answerable": "not_answerable"
        }
        if existing_file_db:
            edge_map["file_vector_retrieve"] = "file_vector_retrieve"

        workflow.add_conditional_edges(START, route_question, edge_map)

        # End edges
        workflow.add_edge("postgres_retrieve", END)
        workflow.add_edge("not_answerable", END)
        if existing_file_db:
            workflow.add_edge("file_vector_retrieve", END)

        graph = workflow.compile()
        return graph, chat_history

    except Exception as e:
        logging.error(get_error_message_detail(e, sys))
        raise InternalError(f"Error creating Renault agent: {e}")



########################################
# Agent Response
########################################
# async def get_agent_response(
#     graph: CompiledStateGraph,
#     chat_history: list,
#     query: str
# ) -> tuple[CompiledStateGraph, str]:
#     """Get agent response for a query."""
#     try:
#         result = await graph.ainvoke({
#             "question": query,
#             "chat_history": chat_history
#         })
#         return graph, result["response"]
#     except Exception as e:
#         logging.error(get_error_message_detail(e))
#         raise InternalError(f"Error getting agent response: {e}")

async def get_agent_response(
    graph: CompiledStateGraph,
    chat_history: list,
    query: str
) -> tuple[CompiledStateGraph, str]:
    """Get agent response for a query."""
    try:
        result = await graph.ainvoke({
            "question": query,
            "chat_history": chat_history
        })

        response = result.get("response", "")
        if not response:
            logging.warning("Agent returned no response.")

        return graph, response

    except Exception as e:
        logging.error(get_error_message_detail(e, sys))
        raise InternalError(f"Error getting agent response: {e}")
