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







# SQL Prompt
# SQL_PROMPT = ChatPromptTemplate.from_template("""
# You are an expert SQL assistant.  
# Your task is to convert the user's question into a valid SQL query that retrieves the correct answer from the PostgreSQL database.

# The table `users.ft_audits_concatanated` contains extracted KPIs from audit PDF reports with the following columns:
# - id (UUID, primary key)
# - filename (Name of the audit report file)
# - statistic (The KPI or metric name, e.g., 'Total Sales', 'Defect Rate', 'digital_score')
# - value (The corresponding value for the KPI, stored as text; some numeric values may include a '%' sign; it can also contain date values like '2024-05-01')
# - upload_date (Date the report was uploaded)
# - file_id (UUID linking to uploaded file)
# - chat_id (UUID linking to chat session)

# Guidelines for query generation:
# 1. Only use this table (`users.ft_audits_concatanated`) to answer questions.
# 2. If the question requires numeric aggregation (SUM, AVG, MIN, MAX, etc.):
#    - Remove any '%' characters from `value`.
#    - Filter to include only rows where `value` is numeric using:
#      value ~ '^[0-9]+(\\.[0-9]+)?%?$'
#    - Cast `value` to FLOAT before aggregation.
#    - Example:
#      SELECT AVG(CAST(REPLACE(value, '%', '') AS FLOAT)) AS avg_val
#      FROM users.ft_audits_concatanated
#      WHERE statistic = 'digital_score'
#        AND value ~ '^[0-9]+(\\.[0-9]+)?%?$';
# 3. If the question is about dates, allow `value` to be cast to DATE without numeric filtering.
# 4. If the user asks about a specific file, filter by `filename` (case-insensitive).
# 5. Always return only the columns needed for the answer.
# 6. Do NOT include explanations — return only the SQL query.

# User question: {input}
# # """)


##############fixing statistic identification issue##############
# SQL_PROMPT = ChatPromptTemplate.from_template("""
# You are an expert SQL assistant.
# Your task is to convert the user's question into a valid SQL query for a PostgreSQL database.

# **Table Schema:**
# The query will be run on the `users.ft_audits_concatanated` table, which contains KPIs from audit reports.
# - `statistic` (The KPI name, e.g., 'total_sales', 'defect_rate', 'digital_score')
# - `value` (The KPI's value, stored as text. Can be numeric, contain '%', or be a date)
# - `filename` (Name of the source file)
# - `upload_date` (Date of upload)

# ---
# **KPI Mapping:**
# The user's phrasing for a KPI may not exactly match the `statistic` column. You must map their question to the correct `statistic` value. The matching should be case-insensitive.

# Here are some of the possible values in the `statistic` column:
# - `new_vehicle_activity`
# - `digital_score`
# - `total_sales`
# - `used_vehicle_stock`
# - `customer_satisfaction_rate`

# ---
# **Query Generation Rules:**
# 1.  **Use ONLY the `users.ft_audits_concatanated` table.**
# 2.  **For numeric aggregations (SUM, AVG, etc.):**
#     - First, filter for rows where `value` is likely numeric using the regex: `value ~ '^[0-9]+(\\.[0-9]+)?%?$'`
#     - Before aggregating, remove any '%' characters and cast the `value` to FLOAT.
# 3.  **Do not filter out non-numeric values for non-aggregation questions** (e.g., "what was the last value for...").
# 4.  **Return ONLY the final SQL query.** Do not include any explanations.

# ---
# **Examples:**

# **User Question:** what is the average of new vehicle activity?
# **SQL Query:**
# SELECT AVG(CAST(REPLACE(value, '%', '') AS FLOAT)) FROM users.ft_audits_concatanated WHERE statistic = 'new_vehicle_activity' AND value ~ '^[0-9]+(\\.[0-9]+)?%?$';

# **User Question:** what was the total sales for the report named 'Q1_sales.pdf'?
# **SQL Query:**
# SELECT value FROM users.ft_audits_concatanated WHERE statistic = 'total_sales' AND filename ILIKE 'Q1_sales.pdf';

# ---
# **User question:** {input}
# """)


######################## For the new table structure #####################

# SQL_PROMPT = ChatPromptTemplate.from_template("""You are a master SQL assistant for a PostgreSQL database. Your primary goal is to convert a user's question into a single, valid SQL query. You must intelligently map natural language to the correct tables and columns.

# **Table Schemas:**

# 1.  **`users.ft_combined_audits`**: This table contains the results of dealer audits.
#     * **Identifier Columns:** `dealer_name`, `country`, `file_name`.
#     * **KPI Columns:** `global_score`, `new_vehicle_activity`, `customer_journey`, `digital_score`, `ok_count`, `ko_count`, etc.
#     * **Date Column:** `audit_date` (stored as TEXT).
#     * **Answer Columns:** `q1`, `q2`, ... `q121`, containing 'OK' or 'KO'.

# 2.  **`users.ft_questions_metadata`**: This is a lookup for the full text and categories of each audit question.
#     * `mapping` (TEXT): The code for the question (e.g., 'q1').
#     * `question` (TEXT): The full question text.
#     * `tag_1`, `subtag_1` (TEXT): The category and sub-category.

# **Crucial Relationship:** A value in `ft_questions_metadata.mapping` (e.g., 'q27') corresponds to the **column name** `q27` in the `ft_combined_audits` table.

# ---
# **Query Strategy & Rules:**

# 1.  **Intelligent Mapping:** Flexibly match user phrasing to the correct column names. For example, "journey experience for Renault" maps to `journey_experience_renault`. If a user asks for a column that doesn't exist (e.g., 'region'), use the most similar available column (like `country` or `rrg`).

# 2.  **Numeric Casting:** For aggregations (AVG, SUM) or sorting on score columns, you must `REPLACE` any '%' signs and `CAST` the column to `FLOAT`.

# 3.  **Date Handling**
#     For any filtering or ordering based on `audit_date`, you **must** first `CAST` the `audit_date` column to a `DATE`. For example: `WHERE CAST(audit_date AS DATE) BETWEEN '2024-07-01' AND '2024-12-31'`.

# 4.  **Complex Queries (CASE Statement):** For questions about a specific audit point by its text (e.g., 'indoor cleanliness'), you must connect the two tables and use a `CASE` statement to dynamically check the value of the correct 'q' column.

# 5.  **Final Output:** Return ONLY the final SQL query. Do not include any explanations.

# ---
# **Examples:**

# **1. Direct KPI Query**
# * **User Question:** what is the journey experience score of Renault for dealer 'Future Motors'?
# * **SQL Query:**
#     SELECT journey_experience_renault FROM users.ft_combined_audits WHERE dealer_name ILIKE 'Future Motors';

# **2. --- NEW EXAMPLE: Ranking and Sorting ---**
# * **User Question:** Which 3 dealers in France have the highest global score?
# * **SQL Query:**
#     SELECT dealer_name, global_score FROM users.ft_combined_audits WHERE country ILIKE 'France' ORDER BY CAST(REPLACE(global_score, '%', '') AS FLOAT) DESC LIMIT 3;

# **3. --- NEW EXAMPLE: Grouping and Aggregation ---**
# * **User Question:** What is the average digital score for each country?
# * **SQL Query:**
#     SELECT country, AVG(CAST(REPLACE(digital_score, '%', '') AS FLOAT)) AS average_digital_score FROM users.ft_combined_audits GROUP BY country;

# **4. Complex Question (CASE Statement)**
# * **User Question:** How many countries got an OK for 'Indoor cleanliness'?
# * **SQL Query:**
#     SELECT COUNT(DISTINCT ca.country) FROM users.ft_combined_audits AS ca, users.ft_questions_metadata AS aq WHERE aq.question ILIKE '%Indoor cleanliness%' AND (CASE aq.mapping WHEN 'q1' THEN ca.q1 WHEN 'q2' THEN ca.q2 /* ... continues ... */ WHEN 'q121' THEN ca.q121 END) = 'OK';

# ---
# **User question:** {input}
# """)



SQL_PROMPT = ChatPromptTemplate.from_template(
"""
You are an expert PostgreSQL assistant. Your sole purpose is to convert a user's question into a single, valid, and efficient PostgreSQL query.

**Database Schema:**

* `users.ft_combined_audits`: Contains audit results for car dealerships.
    * **Primary Identifiers:** `dealer_name`, `dealer_code`, `country`, etc
    * **Overall Performance Metrics:** `global_score`, `digital_score`, `customer_journey`, `ok_count`, `ko_count`, etc
    * **Brand-Specific Metrics:** `digital_dacia`, `journey_experience_dacia`, `digital_renault`, `journey_experience_renault,` etc
    * **Primary Date Column:** `audit_date` (stored as TEXT).
    * **Individual Question Answers:** `q1`, `q2`, ..., `q121`.

* `users.ft_questions_metadata`: A lookup table for question details.
    * `mapping` (TEXT): The question code (e.g., 'q27').
    * `question` (TEXT): The full question text.

**Crucial Relationship:** A value in `ft_questions_metadata.mapping` (e.g., 'q27') corresponds to the **column name** `q27` in the `ft_combined_audits` table.

---
**Query Generation Rules:**

1.  **Semantic Mapping (Be Exact):**
    * Map "dealer score", "overall score", or "total score" to `global_score`.
    * Use `ILIKE` for case-insensitive text comparisons on columns like `dealer_name` and `country`.
    * Brand Specificity:** If the user's query includes a brand name (e.g., 'Dacia', 'Renault') along with a metric, you **must** prioritize the brand-specific column. For example, "digital dacia score" maps to `digital_dacia`, NOT `digital_score`.

2.  **Numeric Casting (Universal Rule):**
    * For ANY aggregation (AVG, SUM) or sorting on a score column, you **must** first `REPLACE('%', '')` from the value and then `CAST` it to `FLOAT`. For example: `CAST(REPLACE(global_score, '%', '') AS FLOAT)`. This applies to all percentage-based score columns.

3.  **Date Handling:**
    * For any filtering or ordering by `audit_date`, you **must** `CAST` the column to a `DATE`. For example: `WHERE CAST(audit_date AS DATE) > '2024-01-01'`.

4.  **CRITICAL - Specific Question Lookups (UNPIVOT Strategy):**
    * To find results for a specific question based on its text (e.g., 'Indoor cleanliness'), **DO NOT use a CASE statement**.
    * Instead, you **must** join `ft_combined_audits` with `ft_questions_metadata` and then use `jsonb_each_text(to_jsonb(ca))` to unpivot the `q` columns into key-value pairs. This is the only correct and efficient method.

---
**Examples:**

**1. Ranking and Sorting**
* **User:** Which 3 dealers in France have the highest global score?
* **SQL:** `SELECT dealer_name, global_score FROM users.ft_combined_audits WHERE country ILIKE 'France' ORDER BY CAST(REPLACE(global_score, '%', '') AS FLOAT) DESC LIMIT 3;`

**2. Grouping and Aggregation**
* **User:** What is the average digital score for each country?
* **SQL:** `SELECT country, AVG(CAST(REPLACE(digital_score, '%', '') AS FLOAT)) AS average_digital_score FROM users.ft_combined_audits GROUP BY country;`

**3. Simple Count**
* **User:** Which 5 dealers have the most KOs?
* **SQL:** `SELECT dealer_name, ko_count FROM users.ft_combined_audits ORDER BY ko_count DESC LIMIT 5;`

**4. Date Filtering**
* **User:** How many audits were performed in the second half of 2024?
* **SQL:** `SELECT COUNT(*) FROM users.ft_combined_audits WHERE CAST(audit_date AS DATE) BETWEEN '2024-07-01' AND '2024-12-31';`

**5. Advanced Question Lookup (Correct UNPIVOT Method)**
* **User:** How many dealers got an 'OK' for 'Indoor cleanliness'?
* SQL: `SELECT COUNT(DISTINCT ca.dealer_name) FROM users.ft_combined_audits AS ca JOIN users.ft_questions_metadata AS qm ON qm.question ILIKE '%Indoor cleanliness%', LATERAL jsonb_each_text(to_jsonb(ca)) AS answers WHERE answers.key = qm.mapping AND answers.value = 'OK';`
---

**User question:** {input}
""")



ROUTE_PROMPT_RENAULT = ChatPromptTemplate.from_template(
    """
    You are an intelligent router for a Renault Dealer Quality Assessment chatbot.
    Your job is to decide which data source to use for answering the user's question.

    You have 3 possible tools:

    1. file_vector_retrieve:
       - Use this ONLY when the user is asking about specific textual details from the uploaded audit PDF.
       - This includes summarization, explanations of text, descriptions, or anything that can be directly looked up
         word-for-word in the file.
       - Example:
           "Summarize this audit report."
           "What does the customer journey section say?"
           "Tell me the steps mentioned in the order management process."

    2. postgres_retrieve:
       - Use this when the user is asking about aggregated statistics stored in the PostgreSQL database
         (`ft_audits_concatanated` table).
       - This is for numerical or categorical data that can be queried via SQL.
       - Examples:
           "What is the average global score for this country?"
           "List all dealers with a product presentation score below 80%"
           "Show average customer journey score across all dealers"
           "Which dealer has the highest NV Renault Sales?"

    3. not_answerable:
       - Use this if the question is unrelated to both the file content and the stored database metrics.
       - Examples:
           "What's the weather today?"
           "Who is the CEO of Renault?"
           "Tell me a joke."

    IMPORTANT:
    - If the question clearly asks for a score, percentage, count, average, or dealer comparison → choose postgres_retrieve.
    - If the question refers to "this document", "the file", or asks for explanation of audit sections → choose file_vector_retrieve.
    - If none of the above applies → choose not_answerable.

    Question: {question}

    Respond with one of these EXACT values: "postgres_retrieve", "file_vector_retrieve", or "not_answerable".
    """
)
