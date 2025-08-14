"""This module handles FAISS vectorstore operations"""

import sys

from langchain_community.vectorstores import FAISS
from faiss import IndexFlatL2
from langchain_community.docstore.in_memory import InMemoryDocstore

from app.logger import logging
from app.exception import get_error_message_detail, InternalError

# Class for FAISS DB operations
class FAISS_DB():
    """
    A wrapper class for managing a FAISS vector database.

    This class provides functionality to create, load, and update a FAISS-based 
    vector store using a given embedding function. It allows document storage and 
    retrieval using vector similarity search.

    Attributes:
        embedding_function: The embedding function used to generate vector embeddings.
        persist_directory (str): Directory where the FAISS index is stored.
        vectorstore: The FAISS vector store instance.
    """

    def __init__(self, embedding_function, persist_directory = None) -> None:
        """
        Initializes the FAISS_DB class.

        Args:
            embedding_function: A function to convert text into vector embeddings.
            persist_directory (str): Directory path to save or load the FAISS index.
        """
        self.embedding_function = embedding_function
        self.persist_directory = persist_directory



    def load(self) -> FAISS:
        """
        Loads an existing FAISS vector store from disk.

        If loading fails (e.g., if the stored FAISS index does not exist or is corrupted), 
        a new FAISS vector store is created and saved locally.

        Returns:
            FAISS: The loaded or newly created FAISS vector store.
        """
        try:
            try:
                vectorstore = FAISS.load_local(
                    folder_path=self.persist_directory,
                    embeddings=self.embedding_function,
                    allow_dangerous_deserialization=True
                )
                self.vectorstore = vectorstore
                logging.info(f"Vectrostore loaded from {self.persist_directory} successfully")
                return self.vectorstore

            except:
                dimensions: int = len(self.embedding_function.embed_query(""))

                vectorstore = FAISS(
                    embedding_function=self.embedding_function,
                    index=IndexFlatL2(dimensions),
                    docstore=InMemoryDocstore(),
                    index_to_docstore_id={},
                    normalize_L2=False
                )
                logging.info("Vectrostore created successfully")
                if self.persist_directory:
                    vectorstore.save_local(self.persist_directory)
                    logging.info(f"Vectrostore saved to {self.persist_directory} successfully")
                self.vectorstore = vectorstore
                return self.vectorstore

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error("An error occurred while loading vectorstore : " + error_message)
            raise InternalError("An error occurred while loading vectorstore : " + str(e))


    def save_local(self) -> None:
        """
        Saves the current FAISS vector store to the specified directory.
        """
        self.vectorstore.save_local(folder_path=self.persist_directory)

    def add_documents(self, documents) -> None:
        """
        Adds a list of documents to the FAISS vector store.

        Args:
            documents (list): A list of document objects to be indexed.
        """
        self.vectorstore.add_documents(documents=documents)

    async def aadd_documents(self, documents) -> None:
        """
        Asynchronously adds a list of documents to the FAISS vector store.

        Args:
            documents (list): A list of document objects to be indexed.
        """
        await self.vectorstore.aadd_documents(documents=documents)

    async def get_files_in_vectorstore(self) -> tuple[set, set]:
        """
        Get a list of files stored in vectorstore

        Returns:
            (list, list) : A list of filenames stored in vectorstore, A list of file gu_ids stored in vectorstore
        """
        try:
            file_paths = set()
            gu_id_list = set()

            if self.vectorstore.index.ntotal != 0:

                all_docs = await self.vectorstore.asimilarity_search("", k=self.vectorstore.index.ntotal)  # Empty query fetches all

                # Print stored documents
                for _, doc in enumerate(all_docs):
                    file_paths.add(doc.metadata['source'])
                    gu_id_list.add(doc.metadata['gu_id'])

            return file_paths, gu_id_list

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            return set(), set()



    async def get(self) -> (dict[str, list] | dict):
        """
        Get a list of files stored in vectorstore

        Returns:
            (dict) : A dictionary containing all documents and metadata stored in the vectorstore.
        """
        try:
            documents = []
            metadatas = []

            all_docs = await self.vectorstore.asimilarity_search("", k=self.vectorstore.index.ntotal)  # Empty query fetches all

            for _, doc in enumerate(all_docs):
                documents.append(doc.page_content)
                metadatas.append(doc.metadata)
            
            all_docs_dict = {"documents" : documents,
                             "metadatas" : metadatas}

            return all_docs_dict

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            return {}


    async def delete(self, gu_id) -> None:
        """
        Delete data of a file from the vectorstore

        Args:
            gu_id (str): gu_id of the file

        """
        try:
            data_dict = self.vectorstore.docstore.__dict__

            ids_to_delete = []
            for _,data in data_dict.items():
                for key, value in data.items():
                    if str(value.metadata["gu_id"]) == str(gu_id):
                        ids_to_delete.append(key)
            
            if ids_to_delete:
                self.vectorstore.delete(ids=ids_to_delete)
                self.vectorstore.save_local(self.persist_directory)
            
            else:
                print("Nothing to delete")
						
        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error("An error occurred while deleting data from vectorstore : " + error_message)
            raise InternalError("An error occurred while deleting data from vectorstore : " + str(e))


    async def get_embeddings_and_ids(self, gu_id) -> tuple[list, list, list]:
        """
        Get embeddings, metadata and ids of a file from the vectorstore.

        Args:
            gu_id (str): gu_id of the file

        Returns:
            (Iterable[Tuple[str, List[float]]], List[dict], List[str]) : list of embeddings with texts, List of metadatas, List of ids
            
        """
        try:
            # Get all docs
            docs = self.vectorstore.docstore._dict

            # Get all embeddings
            faiss_index = self.vectorstore.index
            all_embeddings = faiss_index.reconstruct_n(0, faiss_index.ntotal)

            # Initialize variables
            embeddings = []
            metadatas = []
            ids = []

            # Get all embeddings, metadatas and ids of the corresponding file.
            for i, (doc_id, document) in enumerate(docs.items()):
                if str(document.metadata['gu_id']) == str(gu_id):
                    embeddings.append((document.page_content, all_embeddings[i]))
                    metadatas.append(document.metadata)
                    ids.append(doc_id)
                    
            return embeddings, metadatas, ids
        
        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            raise InternalError("An error occurred while taking embeddings, metadata and ids of a file from the vectorstore: " + str(e))