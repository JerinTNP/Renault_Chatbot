


"""
Data Extraction Module
The module is for data extraction operations
this module will extract texts from pdf,documents and powerpoint files , embedd them and store in vector database
"""


import os
import sys
import shutil
from io import BytesIO
from datetime import datetime
import asyncio
import aiofiles
import uuid

from pdf2image import convert_from_path

from app.info import db_info
from app.models.image_extract_model import IMAGE_EXTRACTION
from app.models.vectorstore import FAISS_DB

from app.logger import logging
from app.exception import get_error_message_detail

from app.exception import InternalError,BadRequestError

# SHAREPOINT Specific functions  
class DATA_LOADER_SP():
    """
    A data loader class to handle downloading files from SharePoint using client credentials.

    This class initializes a connection to a SharePoint site using provided credentials.

    Attributes:
        client_id (str): Azure AD client ID used for authentication.
        client_secret (str): Azure AD client secret used for authentication.
        site_url (str): URL of the SharePoint site.
        sharepoint_url (str): Full SharePoint URL used to resolve file paths.
        ctx: SharePoint client context initialized via `connect_sp`.
    """
    def __init__(self, client_id, client_secret, site_url, sharepoint_url):

        from app.components.storage_handler import connect_sp

        self.client_id = client_id
        self.client_secret = client_secret
        self.site_url = site_url
        self.sharepoint_url = sharepoint_url

        self.ctx = connect_sp(client_id=self.client_id, client_secret=self.client_secret, site_url=self.site_url)
        pass
        
    async def download_file_to_temp(
            self,
            file_path: str, 
            temporary_directory: str
            ) -> str:
        """
        Downloads a file from SharePoint to a local temporary directory asynchronously.

        Args:
            file_path (str): The full URL or relative path to the file on SharePoint.
            temporary_directory (str): Path of local directory where the file should be saved temporarily.

        Returns:
            (str) : Full path to the downloaded temporary file.
        """
        try:
            file_name = file_path.replace("\\", "/").split("/")[-1]
            doc_stream = BytesIO()
            server_relative_url = file_path.replace(self.sharepoint_url, "")

            # Download the PDF file content into the stream (run in executor to avoid blocking)
            await asyncio.to_thread(
                self.ctx.web.get_file_by_server_relative_url(server_relative_url).download(doc_stream).execute_query
            )

            # Reset the stream position to the beginning for reading
            doc_stream.seek(0)

            # Save the in-memory PDF to a temporary file asynchronously using aiofiles
            temp_file_path = os.path.join(temporary_directory, file_name)
            async with aiofiles.open(temp_file_path, "wb") as temp_file:
                await temp_file.write(doc_stream.getvalue())  # aiofiles handles writing asynchronously

            logging.info(f"{file_path} downloaded to {temp_file_path}")

            return temp_file_path

        except Exception as e:
            error_message = get_error_message_detail(e,sys)
            logging.error(error_message)
            raise InternalError("An error occured while downloading a file from sharepoint to temp : " + str(e))


    
    async def convert_to_pdf(
            self,
            doc_path: str,
            PDF_folder_path: str
            ) -> (str | None):
        """
        Asynchronously converts a .doc or .docx file to a .pdf using LibreOffice.

        This function runs LibreOffice in headless mode to convert the document to PDF 
        without opening the GUI. It executes the conversion as an asynchronous subprocess.

        Args:
            doc_path (str): The full path of the .doc or .docx file to be converted.
            PDF_folder_path (str): The directory where the converted PDF will be saved.

        Returns:
            (str): The path to the converted PDF file if successful, otherwise None.
        """
        try:
            if doc_path.lower().endswith(".pdf"):
                return doc_path
            
            filename = os.path.splitext(os.path.basename(doc_path))[0]
            pdf_path = os.path.join(PDF_folder_path, f"{filename}.pdf")

            libreoffice_path = '/usr/bin/soffice'
            
            # Run LibreOffice conversion asynchronously
            process = await asyncio.create_subprocess_exec(
                libreoffice_path, '--headless', '--convert-to', 'pdf', doc_path, '--outdir', PDF_folder_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            _, stderr = await process.communicate()

            if process.returncode == 0:
                logging.info(f'Converted {doc_path} to {pdf_path}')
                return pdf_path
            else:
                logging.error(f"Error converting {doc_path} to pdf : {stderr.decode().strip()}")
                return None

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(f"Error converting {doc_path} to pdf : {error_message}")
            return None



    async def convert_pdf_to_text(
            self,
            pdf_path: str,
            file_path: str,
            linking_uri: str,
            file_modified_date: str,
            gu_id: str
            ):
        """
        Asynchronously converts a PDF to text by processing each page as an image.
        Converts the PDF into images using `pdf2image.convert_from_path` (in a background thread).
        Processes each image to extract text asynchronously.
        Collects the results and checks if all pages were successfully processed.

        Args:
            pdf_path (str): Local path to the PDF file.
            file_path (str): Original SharePoint file path.
            linking_uri (str): URI to link the extracted data.
            file_modified_date (str): The file's last modified date, passed for metadata tracking.
            gu_id (str): A unique identifier used to trace the file through processing.

        Returns:
                (list, bool): A list of processed document objects or text data extracted from the PDF, bool to return True if all pages were successfully embedded; False otherwise.
        """
        try:
            documents = []
            embed_flag = False
            time1 = datetime.now()
            logging.info(f"convert_from_path starting : {pdf_path}")
            print(f"convert_from_path starting : {pdf_path}")

            # Convert PDF to images (blocking call moved to thread pool)
            images = await asyncio.to_thread(convert_from_path, pdf_path)

            logging.info(f"time taken to convert pdf to img : {datetime.now() - time1}")

            print(f"file_path : {file_path}")

            args_list = [(i, img, file_path, linking_uri, file_modified_date, gu_id) for i, img in enumerate(images)]

            if args_list:
                # Run process_image asynchronously for all images
                results = await asyncio.gather(*(IMAGE_EXTRACTION().process_image(args) for args in args_list))
                documents.extend(results)
            
            if len(documents) == len(images):
                embed_flag = True
                logging.info(f"{file_path} : Text extraction completed. Extracted page count = {len(documents)}")
            else:
                embed_flag = False
                logging.error(f"{file_path} : All pages are not extracted. Extracted page count = {len(documents)}")

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(f"An internal server error occurred while converting pdf to text : {error_message}")
								
            documents = []
            embed_flag = False
																							   
        finally:
            return documents, embed_flag

    
    # Creating a function for fetching all the documents from the parent folder to every folders.
    def list_all_files_in_folder_sp(
            self,
            sp_library_title: str,
            sp_folder_relative_path: str
            ) -> tuple[list, list, list, list]:
        """
        Recursively lists all files within a SharePoint folder and its subfolders.

        This method connects to a specified SharePoint document library and navigates through the
        folder structure to retrieve File names, Full URLs to the files, Last modified dates, Linking URIs (if available)

        Args:
            sp_library_title (str): The title of the SharePoint document library (e.g., "Documents").
            sp_folder_relative_path (str): The relative path to the folder within the library (e.g., "Shared Documents/Reports").

        Returns:
               (list of str, list of str, list of str, list of str): Names of the files found, Full SharePoint URLs to each file, Last modified dates of each file in "YYYY/MM/DD" format, Linking URIs for each file (empty string if not available).
        """
        try:
            file_path_list=[]
            file_list = []
            modified_date_list=[]
            linking_uri_list = []
            
            library_title = sp_library_title
            document_library = self.ctx.web.lists.get_by_title(library_title)
            root_folder = document_library.root_folder

            # Function to recursively list files in folders
            def list_files_in_folder(folder):
                folder_files = folder.files.get().execute_query()  # Get all files in the folder
                folder_folders = folder.folders.get().execute_query()  # Get all subfolders in the folder

                # Print all files in the current folder
                for file in folder_files:
                    file_name = file.properties["Name"]
                    server_relative_url = file.properties["ServerRelativeUrl"]
                    modified = file.properties['TimeLastModified']
                    year, month, day = modified.year, modified.month, modified.day
                    modified_date = f"{year}/{month}/{day}"

                    modified_date_list.append(modified_date)
                    # Construct the full URL
                    full_path = f"{self.sharepoint_url}{server_relative_url}"  # Complete URL to the file
                    file_list.append(file_name)
                    file_path_list.append(full_path)
                    linkuri = file.properties["LinkingUri"]
                    if linkuri == None:
                        linkuri=""
                    linking_uri_list.append(linkuri)

                # Recursively go through each subfolder
                for subfolder in folder_folders:
                    list_files_in_folder(subfolder)

            folders = sp_folder_relative_path.split("/")

            for folder in folders:
                root_folder = root_folder.folders.get_by_url(folder).execute_query()

            list_files_in_folder(root_folder)
        
            return file_list,file_path_list,modified_date_list,linking_uri_list

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            raise InternalError("An error occurred while listing all files in a given folder : " + str(e))

    async def load_and_split_documents_sp(
            self, 
            file_path: str,
            linking_uri: str,
            modified_date: str,
            vectorstore: FAISS_DB,
            source: str,
            gu_id: str = None,
            user_id:str = None,
            fileinfo: db_info.FileInfo = None
            ) -> None:
        """
        Asynchronously loads a SharePoint document, processes it, and stores its embeddings into a vectorstore.

        Args:
            file_path (str): The full SharePoint URL to the document.
            linking_uri (str): A URI used for referencing the document in metadata.
            modified_date (str): The last modified date of the document.
            vectorstore (FAISS_DB): An instance of a FAISS vectorstore class.
            source (str): A string denoting the source system or context for the document.
            gu_id (str, optional): A unique identifier for the document. If not provided, one is generated.
            user_id (str, optional): The user ID associated with the file upload.

        Returns:
            None
        """
        try:
            with db_info.get_db_context() as db: 
                temporary_directory = "temp_dir"
                if not os.path.exists(temporary_directory):
                    os.mkdir(temporary_directory)
    
                if file_path.lower().endswith((".doc", ".docx", ".ppt", ".pptx", ".pdf")):
                    file_name = file_path.replace("\\", "/").split("/")[-1]
                    if not gu_id:
                        gu_id = uuid.uuid4()
        
                    if not fileinfo:
                        fileinfo = db_info.FileInfo(
                            file_name= file_name,
                            file_path= file_path,
                            link_uri= linking_uri,
                            upload_date = modified_date,
                            gu_id = gu_id,
                            embed_done = False,
                            source = source,
                            user_id = user_id
                        )
                    
                        db.add(fileinfo)
                        db.commit()
                        db.refresh(fileinfo)
    
                    try:
                        # Downloading files to temporary directory
                        print("Downloading file to temp")
                        temp_file_path = await self.download_file_to_temp(file_path, temporary_directory)
    
                        # Convert other files to pdf
                        if file_path.lower().endswith(".pdf"):
                            pdf_path = temp_file_path
                        else:
                            print("Converting to pdf")
                            pdf_path = await self.convert_to_pdf(temp_file_path, temporary_directory)
    
                        # Extract text from data and convert to Document format.
                        if pdf_path:
                            print("Extracting text")
                            documents, embedded_flag = await self.convert_pdf_to_text(pdf_path, file_path, linking_uri, modified_date, gu_id)
                        
                        else:
                            logging.error("Conversion to PDF failed.")
                            raise InternalError("Conversion to PDF failed.")
    
                        if documents and embedded_flag:
                            # Add documents to vactorstore
                            await vectorstore.aadd_documents(documents)
                            vectorstore.save_local()
                            logging.info(f"{file_path} added to vectorstore")
                            print(f"{file_path} added to vectorstore")
        
                            # fileinfo = db.query(db_info.FileInfo).filter(db_info.FileInfo.gu_id == gu_id).first()
        
                            if fileinfo:
                                fileinfo.embed_done = embedded_flag  # Update done status
                                db.commit()
                                db.refresh(fileinfo)
                            
                            else:
                                logging.error(f"db_info.FileInfo not found for : {file_path}")

                        else:
                            logging.error(f"An error occurred while embedding a file {file_path} and adding it to the vectorstore.")
                            raise InternalError(f"An error occurred while embedding a file {file_path} and adding it to the vectorstore.")
                    
                    except Exception as e:
                        # fileinfo = db.query(db_info.db_info.FileInfo).filter(db_info.db_info.FileInfo.gu_id == gu_id).first()
    
                        # if fileinfo:
                        #     db.delete(fileinfo)
                        #     db.commit()

                        error_message = get_error_message_detail(e, sys)
                        logging.error(error_message)
                        raise InternalError(f"An error occurred while embedding a file {file_path} and adding it to the vectorstore: {str(e)}")
        
                else:
                    raise BadRequestError(f"Unsupported file format: {file_path}")

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            raise InternalError(f"An error occurred while loading a file {file_path} and adding it to the DB: {str(e)}")
 
        finally:
            # Ensure the temp directory is deleted
            if os.path.exists(temporary_directory):
                await asyncio.to_thread(shutil.rmtree, temporary_directory)
                

    async def data_to_db_sp(
            self,
            sp_library_title: str,
            sp_folder_relative_path: str,
            vectorstore: FAISS_DB,
            source: str,
            gu_id: str = None,
            user_id: str = None):
        """
        Asynchronously processes and adds up to 10 SharePoint files from a specified folder into a vectorstore.

        Args:
            sp_library_title (str): The title of the SharePoint document library (e.g., "Documents").
            sp_folder_relative_path (str): The relative path within the library to search for files.
            vectorstore (FAISS_DB): An instance of a FAISS vectorstore class.
            source (str): Identifier for the origin or context of the files.
            gu_id (str, optional): Global unique identifier.
            user_id (str, optional): ID of the user who initiated the upload or process.

        Returns:
            None
        """
        try:
            with db_info.get_db_context() as db:
 
                _,file_path_list,modified_date_list,linking_uri_list = self.list_all_files_in_folder_sp(sp_library_title=sp_library_title,
                                                                                                        sp_folder_relative_path=sp_folder_relative_path
                                                                                                        )

                files_in_db, _ = await vectorstore.get_files_in_vectorstore()
    
                for i in range(len(file_path_list)):

                    file_path = file_path_list[i]
                    fileinfo = db.query(db_info.FileInfo).filter(db_info.FileInfo.file_path == file_path).first()
                    if fileinfo:
                        if fileinfo.embed_done:
                            if file_path in files_in_db:
                                logging.info(f"{file_path} already embedded.")
                                continue
                            
                            else:
                                logging.error(f"{file_path} marked as embedded but not found in vectorstore.")
                                raise InternalError(f"{file_path} marked as embedded but not found in vectorstore.") 
                            
                        elif not fileinfo.embed_done:
                            if file_path in files_in_db:
                                logging.error(f"{file_path} : Already exist in vectorstore, but embedding flag not updated.")
                                raise InternalError(f"{file_path} : Already exist in vectorstore, but embedding flag not updated.")

                            else:
                                file_info = fileinfo

                    else:
                        file_info = None

                    logging.info(f"Embedding file : {file_path}")
                    print(f"Embedding file : {file_path}")
                    await self.load_and_split_documents_sp(file_path=file_path,
                                                    linking_uri=linking_uri_list[i],
                                                    modified_date=modified_date_list[i],
                                                    vectorstore=vectorstore,
                                                    source=source,
                                                    gu_id=gu_id,
                                                    user_id = user_id,
                                                    fileinfo=file_info
                                                    )

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(error_message)
            raise InternalError("An error occurred while adding the dataset to the vectorstore : " + str(e))
