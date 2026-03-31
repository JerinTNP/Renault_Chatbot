from typing import Literal, TypedDict
from pydantic import BaseModel, Field

class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        question: user question
        chat_history: list of previous chats
        response: LLM response
        chat_mode: mode of chat (e.g., "database", "chart", etc.)
    """
    question: str = ""
    chat_history: list = []
    response: str = ""
    chat_mode: str = "database"  

# class RouteQuery(BaseModel):
#     """Route a user question to the appropriate data source."""

#     datasource: Literal[
#         "postgres_retrieve",
#         "file_vector_retrieve",
#         "not_answerable",
#         "chart_retrieve"
#     ] = Field(
#         ...,
#         description="Select the best data source for the user's question. "
#                     "Choose 'chart_retrieve' **ONLY IF** the user explicitly asks for a visualization (e.g., 'create a chart', 'draw a graph', 'show a barchart', 'plot the trends'). "
#                     "**DO NOT** choose 'chart_retrieve' for simple fact-finding questions that result in a single value, list, or table (e.g., 'Which dealer has the highest score?', 'List top 5 products'). "
#                     "Use 'postgres_retrieve' for all direct data retrieval questions."
#     )