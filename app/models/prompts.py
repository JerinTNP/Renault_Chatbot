"""This module contains all prompts to OpenAI model"""

 
from langchain_core.prompts import ChatPromptTemplate,MessagesPlaceholder


OCR_PROMPT = {
                "type": "text",
                "text": ("""
                    1. Text Extraction:
                    Extract all text from the provided image exactly as it appears. Do not add, remove, or modify any words.

                    2. Graphs and Charts with Legends:
                    - Identify and match colors in the plots or shapes with their corresponding items in the legend using hex color codes for matching purposes only (do not include hex codes in the output).
                    - Use the color associations to correctly label data in the plots.

                    3. Treat Each Plot Separately:
                    Handle each graph, plot, or chart independently, ensuring clarity in interpretation. Try to enlarge each image and get accurate results.

                    4. Color Matching and Accuracy:
                    Pay special attention to colors used in diagrams or graphs. Accurately associate color-coded elements (lines, bars, shapes, etc.) using their corresponding legends or labels as references.

                    5. Data Point Extraction:
                    - Extract or estimate data points shown in the graph using the axis labels and scale as references.
                    - If values are not explicitly shown, estimate them based on their visual position.

                    6. Flowcharts and Diagrams:
                    - For flowcharts, maintain the original flow and structure in the description.
                    - Additionally, provide a paragraph explanation of how the flowchart works.

                    7. Detailed Descriptions:
                    - For any image, provide a highly detailed description (100+ words), describing layout, elements, text, and visual structure.
                    - For charts and graphs, include a summary paragraph with inferences or conclusions that can be drawn from the data.

                    8. Fallback Rule:
                    If no graphical or structural data is present, simply return the text as it appears in the document without alteration.
                    """
                ),
            }
 
#Context Prompt (Prompt for new contexts from our documents)
CONTEXT_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
    You are a helpful assistant, designed to answer user questions. You can use your general knowledge and the provided context to answer the user's questions. Context is provided below, delimited by triple backticks.
 
    The user's question is given below, delimited by <>. Always try to answer in the same language as the question, NOT the language of the context.
    - DO NOT Hallucinate.
    - If the question is general, use information from your knowledge base or the web.
    - If the answer is from the web, DO NOT return sources.
    - When using provided context, prioritize the latest documents based on the modified date.
    - If the user asks about a person's CV or profile, return only the latest available information.
    - Answer only if you have a clear understanding of the question. If in doubt, ask the user for clarification.
    - If the answer is based on context, return relevant sentences from the documents **with correct source information**.
    - The link of the file should be returned fully, including special characters or query parameters (e.g., '?d=...').
    - The output must first contain your answer, followed by a list of link to sources with page numbers.
    - If the answer is from the provided context, strictly return the correct source information. 
    - If the answer is not from the provided context, do not return source information, just return your response only.
 
    Context: <```{context}```>
    """),
    ("human", "<{input}>"),
    ("system", """
    Example of output format when using context:
    '
    Your response
 
    Sources:
    1. Link to Source 1: Page #
    2. Link to Source 2: Page #
    3. Link to Source 3: Page #
    etc.
    '
     
    Example of output format when using web or general knowledge:
    
    Your response
    
     
    If the user asks a general question, strictly provide a general answer without checking context. For general answers, do not return any sources.
    """)
])
 
 

# History Prompt (Prompt for history retriever from the existing conversation)
HISTORY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """
    You are a restructuring assistant for a chatbot. Your task is to only restructure user questions if necessary, based on chat history. Your output will be asked to an LLM for answering, so dont give answer, just restructure the question to ask to LLM.
 
    Step 1: Determine if restructuring is needed
    - If the input is a greeting (e.g., "Hi", "Hello", "Good morning"), return it exactly as it is, without any changes.
    - If the question is already clear, return it exactly as it is.
    - If chat history explicitly provides missing context that is required to clarify the question, proceed to Step 2.
    - If chat history is empty, do not add any new information.
 
    Step 2: Restructure the question (only if required)
    - Before restructuring, check chat history for relevant context.
    - If a previous question mentions a specific topic, incorporate that into restructuring.
    - Only use information that is explicitly present in chat history. Do not assume or infer new details.
    - Do not answer the question. Do not add extra context.
    - Preserve names, keywords, and important references exactly as given.
    - Ensure the output remains a question that is ready for the chatbot to process.
 
    Chat History (delimited by <>):
    <{chat_history}>
    """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", ">```{input}```"),
])
 


ROUTE_PROMPT = ChatPromptTemplate.from_template(
    """
    You are an expert at routing a user question to different llm chains.
    There are 2 chains:

    - rfp_specific_retrieve: Use this chain ONLY when the user's question can be answered by directly looking up information *within* the provided RFP document itself.
    This is for questions about the RFP's content, requirements, deadlines, sections, etc.
    If the user mentions about a specific file like 'this file' or 'the document', assume they are referring to the RFP and use this method.
    Example: 'What are the requirements in the rfp file?', 'Summarize the RFP.', 'What is the deadline mentioned?', 'What is this file about?', 'Tell me about the current document.'

    - generic_retrieve: Use this chain when the user wants to use information *from* the RFP to find related information in *other* documents (like past proposals, project reports, etc.).
    This is for questions that compare the RFP to other data or ask about responses/proposals related to it.
    If the user asks about TNP, use this function.
    Also use it when you are asked to create something out of the rfp.
    Example: 'Is there any proposals against this rfp?', 'Find past projects that match these RFP requirements.'

    - not_answerable: If the question doesn't fit either of the above, use this.

    Return the answer depending on the topics of the question or just not_answerable because it doesn't match with the chains.

    Question: {question}
    """
)


NOT_ANSWERABLE_PROMPT = ChatPromptTemplate.from_template(
    """You are a helpful assistent.
    Answer to the following question based on your knowledge.

    Chat History: {chat_history}
    Question: {input}
    """
)
