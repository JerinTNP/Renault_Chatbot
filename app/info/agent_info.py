from typing import Literal, TypedDict
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: question
        chat_history: list of previous chats
        response: LLM response
    """
    question: str = ""
    chat_history: list = []
    response: str = ""

# Data model
class RouteQuery(BaseModel):
    """
    Route a user query to the most relevant vector store.
    """
    datasource: Literal["generic_retrieve", "rfp_specific_retrieve", "not_answerable"] = Field(
        ...,
        description="Given a user question choose to route it to the relevant chain or say it is not answerable.",
    )
