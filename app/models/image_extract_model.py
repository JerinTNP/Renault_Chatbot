"""
This module handles data extraction from images using openai model.
"""

import sys
import asyncio
from io import BytesIO
import base64
from functools import partial
from typing import Any

from langchain_core.messages import HumanMessage
from langchain.docstore.document import Document
from langchain_core.runnables import RunnablePassthrough, RunnableLambda, RunnableSerializable
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from PIL import Image

from app.utils import (
    CHAT_MODEL
)
from app.models.prompts import OCR_PROMPT
from app.logger import logging
from app.exception import get_error_message_detail, InternalError

class IMAGE_EXTRACTION():
    def __init__(self)-> None:
        pass

    def text_prompt_function(
            self,
            base64str: str,
            ocr_prompt: ChatPromptTemplate = OCR_PROMPT
            ) -> list[HumanMessage]:
       
        """
        Combining base64 image string and prompt for extracting data from it.
 
        Args:
            base64str(str): base64-encoded images.
       
        Returns:
            (list): list containing the data and prompt wrapped with HumanMessage object.
        """
        try:
            messages = []
 
            # Adding image(s) to the messages if present
            image_message = {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64str}"
                },
            }
            messages.append(image_message)
 
            # Adding the text message for analysis
            text_message = ocr_prompt
            messages.append(text_message)
 
            return [HumanMessage(content=messages)]
       
        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error("An error occurred while creating prompt function: "+ error_message)
            raise InternalError("An error occurred while creating prompt function: " + str(e))


    def image_extraction_chain(
            self
            )-> RunnableSerializable[Any, str]:
        """
        Creates a chain for extracting data from images.
 
        Returns:
            (chain) : langchain chain object which extracts data from image base64 strings.
        """
        try:
            image_text_extraction_chain = (
                RunnablePassthrough()
                | RunnableLambda(self.text_prompt_function)
                | CHAT_MODEL
                | StrOutputParser()
            )
 
            return image_text_extraction_chain
 
        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error("An error occurred while creating image extraction chain : " + error_message)
            raise InternalError("An error occurred while creating image extraction chain : " + str(e))



    async def img_to_base64(
            self,
            image: Image
            )-> tuple[str, BytesIO]:
        """
        Asynchronously resizes an image and converts it to a base64-encoded PNG.

        Args:
            image (PIL.Image): The image to process.

        Returns:
            tuple: A tuple containing:
                - str: The base64-encoded string of the resized image.
                - BytesIO: The buffer containing the image data.
        """
        try:
            max_size = (800, 800)
            loop = asyncio.get_event_loop()

            # Resize image in executor
            image = await loop.run_in_executor(None, image.resize, max_size, Image.LANCZOS)

            buffered = BytesIO()

            # Correct way to pass keyword arguments
            save_func = partial(image.save, buffered, "PNG", quality=85)
            await loop.run_in_executor(None, save_func)

            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return img_str, buffered

        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error("An error occurred while converting image to base64 string : " + error_message)
            raise InternalError("An error occurred while converting image to base64 string : " + str(e))


    async def process_image(
            self,
            args: tuple[int, Image.Image, str, str, str, str]
            )-> Document:
        """
        Asynchronously processes an image by converting it to base64, extracting text using a prompt function,
        and packaging the result into a Document object with metadata.
 
        Args:
            args (tuple): A tuple containing:
                - i (int): Page number or index.
                - image (PIL.Image): The image to process.
                - file_path (str): File path of the image source.
                - linking_uri (str): A URI for linking or referencing the source.
                - modified_date (str): Last modified date of the image.
                - gu_id (str): A unique identifier for the document.
 
        Returns:
            (Document): A Document object containing extracted text and metadata.
 
        Logs:
            Info logs for success and failure cases.
        """
        try:
            i, image, file_path, linking_uri, modified_date, gu_id = args
            logging.info(f"Processing image :: {file_path} : {i+1}")
 
            img_str, buffered = await self.img_to_base64(image)
            print(f"{file_path} : {i+1}")
 
            texts = await self.image_extraction_chain().ainvoke(img_str)
           
            text_with_date = f"{texts}\n Modified date : {modified_date}.\n"
            doc = Document(page_content = text_with_date, metadata = {"source" : file_path, "page": i+1, "LinkingUri": linking_uri , "date": modified_date, "gu_id": gu_id})
            logging.info(f"Data extracted for {file_path} : {i+1}")
 
            buffered.close()
            return doc
               
        except Exception as e:
            error_message = get_error_message_detail(e, sys)
            logging.error(f"Text extraction failed for {file_path}, page {i+1} with ERROR : {error_message}")
            raise InternalError("Text extraction failed")
            