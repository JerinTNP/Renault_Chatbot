
"""
Pydantic model for query information.
"""
 
from pydantic import BaseModel, UUID4, StringConstraints
from typing_extensions import Annotated
from typing import Union, Literal
 
class QueryInfo(BaseModel):
    """
    This model defines the structure for extracting query data from browser requests.
    """
    query: Annotated[str, StringConstraints(strip_whitespace=True)]
    chatid: UUID4

class QueryInfoGeneric(BaseModel):
    """
    This model defines the structure for extracting query data from browser requests specifically for generic chat.
    """
    query: Annotated[str, StringConstraints(strip_whitespace=True)]
    chatid: Union[UUID4, Literal[""]]

# Pydantic model for response
class FileResponse(BaseModel):
    """
    Pydantic model defining the structure of the API response.
    """
    file_name: Annotated[str, StringConstraints(strip_whitespace=True)]
    gu_id: str
    link_uri: str   # Link of the file

class SearchRequest(BaseModel):
    """
    This model defines the structure of input data for search file.
    """
    keyword: Annotated[str, StringConstraints(strip_whitespace=True)] 


class RequirementRequest(BaseModel):
    """
    This model defines the structure of input data for requirement as text input.
    """
    requirement: Annotated[str, StringConstraints(strip_whitespace=True)] # Requirements for the proposal.