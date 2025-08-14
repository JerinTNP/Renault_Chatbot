"""
Pydantic model for user login information.

This model defines the structure for user login data, ensuring that 
username and password inputs are stripped of any leading or trailing whitespace.

"""

from pydantic import BaseModel, StringConstraints, EmailStr, UUID4
from typing_extensions import Annotated
from typing import Optional

class LoginInfo(BaseModel):
    """
    Data model representing user login credentials.

    Attributes:
        username (str): The user's username. Leading and trailing whitespace will be stripped.
        password (str): The user's password. Leading and trailing whitespace will be stripped.
    """
    username: Annotated[str, StringConstraints(strip_whitespace=True)]
    password: Annotated[str, StringConstraints(strip_whitespace=True)]
    
class AddUserRequest(BaseModel):
    """
    Data model used to add a new user.

    Attributes:
        username (str): Unique username for the user.
        pwd (str): Hashed password for secure authentication.
        fname (str): First name of the user.
        lname (str): Last name of the user.
        name (str): Full name or display name of the user.
        email (EmailStr): Valid email address of the user.
        organization (str): Name of the organization the user belongs to.
        department_id (UUID4): Unique identifier of the department the user is assigned to.
        role (str): Role or designation of the user within the system (e.g., 'admin', 'user').
    """
    username: str
    pwd: str  
    fname: str
    lname: str
    name: str
    email: EmailStr
    organization: str
    department_id: UUID4  
    role: str

class EditUserRequest(BaseModel):
    """
    Data model to update an existing user's information.

    Attributes:
        user_id (UUID4): Unique identifier of the user to be updated. (Required)
        pwd (Optional[str]): New hashed password for the user. If not provided, password remains unchanged.
        fname (Optional[str]): Updated first name of the user. Optional.
        lname (Optional[str]): Updated last name of the user. Optional.
        name (Optional[str]): Updated full/display name of the user. Optional.
        department_id (UUID4): Updated department ID. If not provided, department remains unchanged.
    """
    user_id: UUID4  
    pwd: Optional[str] = None
    fname: Optional[str] = None
    lname: Optional[str] = None
    name: Optional[str] = None
    department_id: UUID4 = None 
