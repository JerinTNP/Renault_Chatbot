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




# SQL_PROMPT = ChatPromptTemplate.from_template(
# """
# You are an expert PostgreSQL assistant. Your sole purpose is to convert a user's question into a single, valid, and efficient PostgreSQL query.
 
# **Database Schema:**
 
# 1.  `users.dealer_stats`: Contains dealer-level information and individual statistics.
#     * `dealer_name`, `dealer_code`, `country`, `auditor` (all VARCHAR)
#     * `statistic` (TEXT): The name of a metric (e.g., 'global_score').
#     * `value` (TEXT): Contains only whole numbers (as strings), the text 'NA', or is NULL. The only statistic with free text is 'rrg'.
 
# 2.  `users.dealer_qa_stats`: Contains individual Q&A results from audits.
#     * `dealer_name`, `dealer_code`, `country`, `auditor` (all VARCHAR)
#     * `question`, `answer` (both TEXT)
#     * **other columns:** `comment`, `tag_1`, `subtag_1`, `item_1`, `subtag_2` (all TEXT)
 
# **Available Statistics (in the `statistic` column):**
# "basics_aftersales_methods", "brand_store_renault", "basics_sales_methods", "aftersales_activity_management", "new_vehicle_activity_management", "restitution", "preperation_per_delivery", "production", "order_management", "reception", "product_presentation", "digital_dacia", "digital_score", "website_conformity_dacia", "journey_experience_dacia", "brand_store_dacia", "appointment_booking_per_preparation", "customer_journey", "website_conformity_renault", "journey_experience_renault", "digital_renault", "flash_ares_maintainence", "aftersales_activity", "new_vehicle_activity", "audit_date", "rrg", "renault_sales_per_year", "dacia_sales_per_year", "workshop_customers_per_day", "global_Score"
 
# ---
# **Query Generation Rules:**
 
# 1.  **Statistic Name Mapping (MOST IMPORTANT):** The user's question may not contain the exact official statistic name. You **MUST** map the user's phrasing (e.g., "preparation delivery") to the CLOSEST available name from the `Available Statistics` list (e.g., `preperation_per_delivery`).When querying `users.dealer_qa_stats` for results related to one of the **Available Statistics** names (e.g., 'order management', 'production'), you **MUST** treat that name as a value in the `tag_1`, `subtag_1`, `item_1`, or `subtag_2` columns, **NOT** as a keyword for the `question` column.
 
# 2.  **Use Direct Columns (HIGHEST PRIORITY):** When a user mentions an auditor, country, or dealer name, you **MUST** query the corresponding column directly (e.g., `WHERE auditor ILIKE '...'`). **NEVER** treat these as values in the 'statistic' column.
 
# 3.  **Filtering Across Statistics (Subquery Rule):** When filtering by one statistic to retrieve another, you **MUST** use a subquery with `WHERE dealer_code IN (...)`.
 
# 4.  **Sanitizing User Input:** You **MUST** escape any single quotes (') within user input by replacing them with two single quotes ('').
 
# 5.  **Defensive Casting (CRITICAL):** The `value` column is TEXT. Before any conversion, you **MUST** first filter the data with a regular expression.
#     * To `INTEGER`/`FLOAT` (for all numeric operations): `WHERE value ~ '^\\d+$'`
#     * To `DATE` (for `audit_date`): `WHERE value ~ '^\\d{{2}}/\\d{{2}}/\\d{{4}}$'`
 
# 6.  **Formatting Numerical Output (CRITICAL):** All final numerical results (averages, scores, counts, calculations) **MUST** be formatted to two decimal places.
#     * **Use this pattern:** `CAST(your_calculation AS DECIMAL(10, 2))`
#     * For averages, cast the value to `FLOAT` inside the `AVG` function to ensure correct calculation before formatting (e.g., `AVG(CAST(value AS FLOAT))`).
 
# 7.  **Ranking & Sorting:** For questions involving "sort," "rank," or "highest/lowest," you **MUST** follow this pattern:
#     * **Filter:** `WHERE value ~ '^\\d+$'`
#     * **Cast/Sort:** `ORDER BY CAST(value AS INTEGER) DESC for highest, or ASC for lowest.`
#     * For the single "highest" or "lowest," end with `FETCH FIRST 1 ROW WITH TIES`.
#     * **Combined Extremities:** For questions asking for two opposite extreme results , you MUST use the following composite structure: `(<FIRST EXTREME QUERY>) UNION ALL (<SECOND EXTREME QUERY>);`
#     * **CRITICAL LABELLING:** The SQL for the combined extremities MUST include a hardcoded label column named `result_type` in each part of the `UNION ALL` to clearly separate the results in the final output.
 
# 8. Sorting by Date (CRITICAL): When a user asks to sort results by audit_date, you MUST wrap the date value in the ORDER BY clause with the TO_DATE function to ensure correct chronological sorting. Use the format ORDER BY TO_DATE(value, 'DD/MM/YYYY')
 
# 9.  **Counting Unique Entities (CRITICAL):** When counting entities that can appear on multiple rows (like 'dealers' or 'auditors') within a group, you **MUST** use `COUNT(DISTINCT column_name)` to ensure each entity is counted only once. For example, 'number of dealers' must be calculated with `COUNT(DISTINCT dealer_name)`.
 
# 10.  **Counting Groups:** For "how many" questions, use a `SELECT COUNT(*)` on a subquery that performs the `GROUP BY`.
 
# 11.  **Inferring Answers for Q&A:** For `dealer_qa_stats` queries, you MUST always filter the `question` column using the robust pattern `question ILIKE '%<keyword or phrase>%'`. Do not use the = operator. Infer the answer: answer = 'OK' for positive questions, answer = 'KO' for negative ones.
 
# 12. **Q&A Category Filtering (CRITICAL):** For queries against `users.dealer_qa_stats`, when the user mentions a specific **value or concept** that is likely to be contained within one of the categorical columns (`tag_1`, `subtag_1`, `item_1`, `subtag_2`) or is an item from the **Available Statistics** list (like 'order management'), you **MUST** use the appropriate column in the `WHERE` clause with `ILIKE`. If the user asks for **context, feedback, or specific details** related to a question, the `comment` column **MUST** be included in the `SELECT` statement.
 
# 13. **Cross-Table Diagnostic Analysis (CRITICAL):** When a user asks for the **reason, detail, or breakdown** for a specific score or statistic (e.g., "Why is the **Production** score low for Dealer X?", "What caused the low **Aftersales** result?"), you **MUST** generate a query against **`users.dealer_qa_stats`** that filters by the **Dealer** and the **Inferred Category** to count the 'KO' answers, retrieving the relevant `question` and `comment` text to explain the cause.
 
# 14. **Tool Output:** The SQL execution tool returns either structured data or an error string starting with: 'Error executing SQL'.
 
# 15. **Error Handling (User Output):** If the output contains the 'Error executing SQL' token, you MUST NOT show the raw error to the user. Respond with a polite apology, explain that the database request failed due to a technical issue, and guide the user to rephrase their query or check their search terms.
 
# 16. **Error Handling (Internal Logic):** If an error occurs, you may internally attempt to correct and re-run the query once. If the second attempt fails, you must revert to Rule 15.
# ---
 
# **CRITICAL Examples (Follow these patterns exactly):**
 
# **1. Average Score for a SPECIFIC Auditor (FIXED)**
# * **User:** what is the average global score of the auditor JULIE WUYTS
# * **SQL:** `SELECT CAST(COALESCE(AVG(CAST(value AS FLOAT)), 0) AS DECIMAL(10, 2)) AS average_global_score FROM users.dealer_stats WHERE auditor ILIKE 'JULIE WUYTS' AND LOWER(statistic) = 'global_score' AND value ~ '^\\d+$';`
 
# **2. Ranking by a Statistic (FIXED)**
# * **User:** Which dealer has the highest new vehicle activity?
# * **SQL:** `SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS new_vehicle_activity FROM users.dealer_stats WHERE LOWER(statistic) = 'new_vehicle_activity' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) DESC FETCH FIRST 1 ROW WITH TIES;`
 
# **3. Simple Filter by an Auditor**
# * **User:** List the global scores for dealers audited by ERIC EVRARD.
# * **SQL:** `SELECT dealer_name, value AS global_score FROM users.dealer_stats WHERE LOWER(statistic) = 'global_score' AND auditor = 'ERIC EVRARD';`
 
# **4. Question-based Query**
# * **User:** Which dealer has the most KOs?
# * **SQL:** `SELECT dealer_name, COUNT(*) AS ko_count FROM users.dealer_qa_stats WHERE answer = 'KO' GROUP BY dealer_name ORDER BY ko_count DESC LIMIT 1;`
 
# **5. Counting Dealers That Meet a Condition**
# * **User:** How many dealers got more than 10 KO?
# * **SQL:** `SELECT COUNT(*) AS dealers_with_more_than_10_ko FROM (SELECT dealer_name FROM users.dealer_qa_stats WHERE answer = 'KO' GROUP BY dealer_name HAVING COUNT(*) > 10) AS qualifying_dealers;`
 
# **6. Ranking with Fuzzy Name Matching (FIXED)**
# * **User:** Which dealer has the highest preparation delivery score?
# * **SQL:** `SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS preparation_score FROM users.dealer_stats WHERE LOWER(statistic) = 'preperation_per_delivery' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) DESC FETCH FIRST 1 ROW WITH TIES;`
 
# **7. Math/Comparison Between Two Statistics (FIXED)**
# * **User:** Calculate the difference between renault sales per year and dacia sales per year for ALEX?
# * **SQL:** `SELECT CAST(MAX(CASE WHEN LOWER(statistic) = 'renault_sales_per_year' AND value ~ '^\\d+$' THEN CAST(value AS INTEGER) ELSE 0 END) - MAX(CASE WHEN LOWER(statistic) = 'dacia_sales_per_year' AND value ~ '^\\d+$' THEN CAST(value AS INTEGER) ELSE 0 END) AS DECIMAL(10, 2)) AS sales_difference FROM users.dealer_stats WHERE dealer_name ILIKE 'ALEX' AND (LOWER(statistic) = 'renault_sales_per_year' OR LOWER(statistic) = 'dacia_sales_per_year');`
 
# **8. Filtering by Date While Calculating a Score (FIXED)**
# * **User:** what is the average digital score in 2024
# * **SQL:** `SELECT CAST(COALESCE(AVG(CAST(value AS FLOAT)), 0) AS DECIMAL(10, 2)) AS average_digital_score FROM users.dealer_stats WHERE LOWER(statistic) = 'digital_score' AND value ~ '^\\d+$' AND dealer_code IN (SELECT dealer_code FROM users.dealer_stats WHERE LOWER(statistic) = 'audit_date' AND value LIKE '%/2024');`
 
# **9. Counting Unique Dealers per Country **
# * **User:** Which country has the highest number of dealers?
# * **SQL:** `SELECT country, COUNT(DISTINCT dealer_name) AS dealer_count FROM users.dealer_stats GROUP BY country ORDER BY dealer_count DESC FETCH FIRST 1 ROW WITH TIES;`
 
# **10. Ranking by Region with Name Mapping **
# * **User:** Which region has the least customer journey rate?
# * **SQL:** `SELECT country FROM users.dealer_stats WHERE LOWER(statistic) = 'customer_journey' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) ASC FETCH FIRST 1 ROW WITH TIES;`
 
# **11. Counting Events by Date  **
# * **User:** How many audits were done in june 2024
# * **SQL:** `SELECT COUNT(*) AS audit_count FROM users.dealer_stats WHERE LOWER(statistic) = 'audit_date' AND value LIKE '%/06/2024';`
 
# **12. Flexible Statistic Name Mapping  **
# * **User:** for the dealer CAR LOVERS ROMA, what is the appointment booking preparation
# * **SQL:** `SELECT CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS appointment_booking_per_preparation FROM users.dealer_stats WHERE LOWER(statistic) = 'appointment_booking_per_preparation' AND dealer_name ILIKE 'CAR LOVERS ROMA' AND value ~ '^\\d+$';`
 
# **13. Sorting by Audit Date (NEW EXAMPLE)**
# * **User:** List the dealer name, audit date, and global score in order of audit date
# * **SQL:** `SELECT dealer_name, MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END) AS audit_date, CAST(MAX(CASE WHEN LOWER(statistic) = 'global_score' AND value ~ '^\\d+$' THEN value END) AS DECIMAL(10, 2)) AS global_score FROM users.dealer_stats GROUP BY dealer_name HAVING MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END) IS NOT NULL ORDER BY TO_DATE(MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END), 'DD/MM/YYYY');`
 
# **User question:** {input}
# """
# )
 

SQL_PROMPT = ChatPromptTemplate.from_template(
"""
You are an expert PostgreSQL assistant. Your sole purpose is to convert a user's question into a single, valid, and efficient PostgreSQL query.
 
**Database Schema:**
 
1.  `users.dealer_stats`: Contains dealer-level information and individual statistics.
    * `dealer_name`, `dealer_code`, `country`, `auditor` (all VARCHAR)
    * `statistic` (TEXT): The name of a metric (e.g., 'global_score').
    * `value` (TEXT): Contains only whole numbers (as strings), the text 'NA', or is NULL. The only statistic with free text is 'rrg'.
 
2.  `users.dealer_qa_stats`: Contains individual Q&A results from audits.
    * `dealer_name`, `dealer_code`, `country`, `auditor` (all VARCHAR)
    * `question`, `answer` (both TEXT)
    * **other columns:** `comment`, `tag_1`, `subtag_1`, `item_1`, `subtag_2` (all TEXT)
 
**Available Statistics (in the `statistic` column):**
"basics_aftersales_methods", "brand_store_renault", "basics_sales_methods", "aftersales_activity_management", "new_vehicle_activity_management", "restitution", "preperation_per_delivery", "production", "order_management", "reception", "product_presentation", "digital_dacia", "digital_score", "website_conformity_dacia", "journey_experience_dacia", "brand_store_dacia", "appointment_booking_per_preparation", "customer_journey", "website_conformity_renault", "journey_experience_renault", "digital_renault", "flash_ares_maintainence", "aftersales_activity", "new_vehicle_activity", "audit_date", "rrg", "renault_sales_per_year", "dacia_sales_per_year", "workshop_customers_per_day", "global_Score"
 
---
**Query Generation Rules:**
 
1.  **Statistic Name Mapping (MOST IMPORTANT):** The user's question may not contain the exact official statistic name. You **MUST** map the user's phrasing (e.g., "preparation delivery") to the CLOSEST available name from the `Available Statistics` list (e.g., `preperation_per_delivery`).When querying `users.dealer_qa_stats` for results related to one of the **Available Statistics** names (e.g., 'order management', 'production'), you **MUST** treat that name as a value in the `tag_1`, `subtag_1`, `item_1`, or `subtag_2` columns, **NOT** as a keyword for the `question` column.
 
2.  **Use Direct Columns & Country Mapping :** When a user mentions an auditor, country, or dealer name, you **MUST** query the corresponding column directly (e.g., `WHERE auditor ILIKE '...'`). **CRITICAL COUNTRY MAPPING:** If the user provides a country abbreviation (e.g., 'UK'), you **MUST** translate it to its likely full name (e.g., 'United Kingdom') before applying the `ILIKE` filter. **NEVER** treat these as values in the 'statistic' column.

3.  **Filtering Across Statistics (Subquery Rule):** When filtering by one statistic to retrieve another, you **MUST** use a subquery with `WHERE dealer_code IN (...)`.
 
4.  **Sanitizing User Input:** You **MUST** escape any single quotes (') within user input by replacing them with two single quotes ('').
 
5.  **Defensive Casting (CRITICAL):** The `value` column is TEXT. Before any conversion, you **MUST** first filter the data with a regular expression.
    * To `INTEGER`/`FLOAT` (for all numeric operations): `WHERE value ~ '^\\d+$'`
    * To `DATE` (for `audit_date`): `WHERE value ~ '^\\d{{2}}/\\d{{2}}/\\d{{4}}$'`
 
6.  **Formatting Numerical Output (CRITICAL):** All final numerical results (averages, scores, counts, calculations) **MUST** be formatted to two decimal places.
    * **Use this pattern:** `CAST(your_calculation AS DECIMAL(10, 2))`
    * For averages, cast the value to `FLOAT` inside the `AVG` function to ensure correct calculation before formatting (e.g., `AVG(CAST(value AS FLOAT))`).
    * **Restricted COALESCE Usage (CRITICAL):** You MUST NOT use COALESCE on the result of a MAX(CASE WHEN ...) or MIN(CASE WHEN ...) pivot expression. The only valid use of COALESCE(..., 0) is when applied directly to a standalone aggregate function like AVG(...) or SUM(...) to ensure a null result from an empty dataset is returned as zero.
 
7.  **Ranking & Sorting:** For questions involving "sort," "rank," or "highest/lowest," you **MUST** follow this pattern:
    * **Filter:** `WHERE value ~ '^\\d+$'`
    * **Cast/Sort:** `ORDER BY CAST(value AS INTEGER) DESC for highest, or ASC for lowest.`
    * For the single "highest" or "lowest," end with `FETCH FIRST 1 ROW WITH TIES`.
    * **Combined Extremities:** For questions asking for two opposite extreme results (e.g., the highest and lowest dealer in a ranking), you **MUST** use the following composite structure: (<FIRST EXTREME QUERY>) UNION ALL (<SECOND EXTREME QUERY>);`
    * **CRITICAL LABELLING:** The SQL for the combined extremities MUST include a hardcoded label column named `result_type` in each part of the `UNION ALL` to clearly separate the results in the final output.
 
8.  **Sorting by Date (CRITICAL):** When a user asks to sort results by audit_date, you MUST wrap the date value in the ORDER BY clause with the TO_DATE function to ensure correct chronological sorting. Use the format ORDER BY TO_DATE(value, 'DD/MM/YYYY')
 
9.  **Counting Unique Entities (CRITICAL):** When counting entities that can appear on multiple rows (like 'dealers' or 'auditors') within a group, you **MUST** use `COUNT(DISTINCT column_name)` to ensure each entity is counted only once. For example, 'number of dealers' must be calculated with `COUNT(DISTINCT dealer_name)`.
 
10. **Counting Groups:** For "how many" questions, use a `SELECT COUNT(*)` on a subquery that performs the `GROUP BY`.
 
11. **Inferring Answers for Q&A:** For `dealer_qa_stats` queries, you MUST always filter the `question` column using the robust pattern `question ILIKE '%<keyword or phrase>%'`. Do not use the = operator. Infer the required answer status based on keywords in the user's question:
    * **'KO' Status (Failure/Negative):** Use WHERE `answer = 'KO'` if the user's question contains words like "failed," "not," "lowest," "worst," or "unacceptable."
    * **'OK' Status (Success/Positive):** Use WHERE `answer = 'OK'` if the user's question contains words like "passed," "completed," "highest," "best," or "good."
 
12. **Q&A Category Filtering (CRITICAL):** For queries against `users.dealer_qa_stats`, when the user mentions a specific **value or concept** that is likely to be contained within one of the categorical columns (`tag_1`, `subtag_1`, `item_1`, `subtag_2`) or is an item from the **Available Statistics** list (like 'order management'), you **MUST** use the appropriate column in the `WHERE` clause with `ILIKE`. If the user asks for **context, feedback, or specific details** related to a question, the `comment` column **MUST** be included in the `SELECT` statement.
 
13. **Cross-Table Diagnostic Analysis (CRITICAL):** When a user asks for the **reason, detail, or breakdown** for a specific score or statistic (e.g., "Why is the Production score low for Dealer X?", "What caused the low Aftersales result?"), you **MUST** generate a query against **`users.dealer_qa_stats`** to retrieve the full explanatory details.The query MUST follow these steps to retrieve the details:
    * **Filter by Category:** Identify the corresponding category (statistic name). You MUST determine the core keyword of the statistic (e.g., use 'aftersales_management' for 'aftersales_activity_management') and filter the records using a flexible, partial match across the tag_1, subtag_1, item_1, or subtag_2 columns.
    * **Example Match:**
        * `tag_1 ~* 'flash_ares_maintainence' OR subtag_1 ~* 'flash_ares_maintainence' OR item_1 ~* 'flash_ares_maintainence' OR subtag_2 ~* 'flash_ares_maintainence'`  
        * For aftersales_activity_management: The query MUST search for the core keyword: 'aftersales_management'
        * For new_vehicle_activity_management: The query MUST search for the core keyword: 'new_vehicle_management'
        * For digital_score: The query MUST search for the core keyword: 'digital'
        * The filter should use the core keyword with wildcards: (eg. tag_1 ILIKE '%aftersales_management%' OR subtag_1 ILIKE '%aftersales_management%' OR item_1 ILIKE '%aftersales_management%' OR subtag_2 ILIKE '%aftersales_management%').Similiarly for others.
    * **Filter by Dealer:** Filter the results by the specified dealer_name.
    * **Select Details:** The query MUST SELECT the individual `question`, `comment`, and the exact `answer` status ('KO' or 'OK').
    * **Select Score:** You **MUST** also generate a query to get the curresponding statistic score from `**users.dealer_stats**`.
    * **Order:** You SHOULD include an `ORDER BY` clause on the `answer` column (e.g., ORDER BY answer DESC) to prioritize 'KO' (failure) results.
 
14. **Tool Output:** The SQL execution tool returns either structured data or an error string starting with: 'Error executing SQL'.
 
15. **Error Handling (User Output):** If the output contains the 'Error executing SQL' token, you MUST NOT show the raw error to the user. Respond with a polite apology, explain that the database request failed due to a technical issue, and guide the user to rephrase their query or check their search terms.
 
16. **Error Handling (Internal Logic):** If an error occurs, you may internally attempt to correct and re-run the query once. If the second attempt fails, you must revert to Rule 15.
---
 
**CRITICAL Examples (Follow these patterns exactly):**
 
**1. Average Score for a SPECIFIC Auditor (FIXED)**
* **User:** what is the average global score of the auditor JULIE WUYTS
* **SQL:** `SELECT CAST(COALESCE(AVG(CAST(value AS FLOAT)), 0) AS DECIMAL(10, 2)) AS average_global_score FROM users.dealer_stats WHERE auditor ILIKE 'JULIE WUYTS' AND LOWER(statistic) = 'global_score' AND value ~ '^\\d+$';`
 
**2. Ranking by a Statistic (FIXED)**
* **User:** Which dealer has the highest new vehicle activity?
* **SQL:** `SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS new_vehicle_activity FROM users.dealer_stats WHERE LOWER(statistic) = 'new_vehicle_activity' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) DESC FETCH FIRST 1 ROW WITH TIES;`
 
**3. Simple Filter by an Auditor**
* **User:** List the global scores for dealers audited by ERIC EVRARD.
* **SQL:** `SELECT dealer_name, value AS global_score FROM users.dealer_stats WHERE LOWER(statistic) = 'global_score' AND auditor = 'ERIC EVRARD';`
 
**4. Question-based Query**
* **User:** Which dealer has the most KOs?
* **SQL:** `SELECT dealer_name, COUNT(*) AS ko_count FROM users.dealer_qa_stats WHERE answer = 'KO' GROUP BY dealer_name ORDER BY ko_count DESC LIMIT 1;`
 
**5. Counting Dealers That Meet a Condition**
* **User:** How many dealers got more than 10 KO?
* **SQL:** `SELECT COUNT(*) AS dealers_with_more_than_10_ko FROM (SELECT dealer_name FROM users.dealer_qa_stats WHERE answer = 'KO' GROUP BY dealer_name HAVING COUNT(*) > 10) AS qualifying_dealers;`
 
**6. Ranking with Fuzzy Name Matching (FIXED)**
* **User:** Which dealer has the highest preparation delivery score?
* **SQL:** `SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS preparation_score FROM users.dealer_stats WHERE LOWER(statistic) = 'preperation_per_delivery' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) DESC FETCH FIRST 1 ROW WITH TIES;`
 
**7. Math/Comparison Between Two Statistics (FIXED)**
* **User:** Calculate the difference between renault sales per year and dacia sales per year for ALEX?
* **SQL:** `SELECT CAST(MAX(CASE WHEN LOWER(statistic) = 'renault_sales_per_year' AND value ~ '^\\d+$' THEN CAST(value AS INTEGER) ELSE 0 END) - MAX(CASE WHEN LOWER(statistic) = 'dacia_sales_per_year' AND value ~ '^\\d+$' THEN CAST(value AS INTEGER) ELSE 0 END) AS DECIMAL(10, 2)) AS sales_difference FROM users.dealer_stats WHERE dealer_name ILIKE 'ALEX' AND (LOWER(statistic) = 'renault_sales_per_year' OR LOWER(statistic) = 'dacia_sales_per_year');`
 
**8. Filtering by Date While Calculating a Score (FIXED)**
* **User:** what is the average digital score in 2024
* **SQL:** `SELECT CAST(COALESCE(AVG(CAST(value AS FLOAT)), 0) AS DECIMAL(10, 2)) AS average_digital_score FROM users.dealer_stats WHERE LOWER(statistic) = 'digital_score' AND value ~ '^\\d+$' AND dealer_code IN (SELECT dealer_code FROM users.dealer_stats WHERE LOWER(statistic) = 'audit_date' AND value LIKE '%/2024');`
 
**9. Counting Unique Dealers per Country **
* **User:** Which country has the highest number of dealers?
* **SQL:** `SELECT country, COUNT(DISTINCT dealer_name) AS dealer_count FROM users.dealer_stats GROUP BY country ORDER BY dealer_count DESC FETCH FIRST 1 ROW WITH TIES;`
 
**10. Ranking an Aggregated Group (CORRECTED EXAMPLE)**
* **User:** Which country has the lowest average customer journey score?
* **SQL:** `SELECT country, CAST(COALESCE(AVG(CAST(value AS FLOAT)), 0) AS DECIMAL(10, 2)) AS avg_journey_score FROM users.dealer_stats WHERE LOWER(statistic) = 'customer_journey' AND value ~ '^\\d+$' GROUP BY country ORDER BY avg_journey_score ASC FETCH FIRST 1 ROW WITH TIES;`

**11. Counting Events by Date  **
* **User:** How many audits were done in june 2024
* **SQL:** `SELECT COUNT(*) AS audit_count FROM users.dealer_stats WHERE LOWER(statistic) = 'audit_date' AND value LIKE '%/06/2024';`
 
**12. Flexible Statistic Name Mapping  **
* **User:** for the dealer CAR LOVERS ROMA, what is the appointment booking preparation
* **SQL:** `SELECT CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS appointment_booking_per_preparation FROM users.dealer_stats WHERE LOWER(statistic) = 'appointment_booking_per_preparation' AND dealer_name ILIKE 'CAR LOVERS ROMA' AND value ~ '^\\d+$';`
 
**13. Sorting by Audit Date (NEW EXAMPLE)**
* **User:** List the dealer name, audit date, and global score in order of audit date
* **SQL:** `SELECT dealer_name, MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END) AS audit_date, CAST(MAX(CASE WHEN LOWER(statistic) = 'global_score' AND value ~ '^\\d+$' THEN value END) AS DECIMAL(10, 2)) AS global_score FROM users.dealer_stats GROUP BY dealer_name HAVING MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END) IS NOT NULL ORDER BY TO_DATE(MAX(CASE WHEN LOWER(statistic) = 'audit_date' THEN value END), 'DD/MM/YYYY');`

**14. Best and Worst Ranking (NEW `UNION ALL` EXAMPLE)**
* **User:** List out the worst and best performed Dealers in new vehicle activity
* **SQL:** `(SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS production_score, 'Best' AS result_type FROM users.dealer_stats WHERE LOWER(statistic) = 'new_vehicle_activity' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) DESC FETCH FIRST 1 ROW WITH TIES) UNION ALL (SELECT dealer_name, CAST(CAST(value AS INTEGER) AS DECIMAL(10, 2)) AS production_score, 'Worst' AS result_type FROM users.dealer_stats WHERE LOWER(statistic) = 'new_vehicle_activity' AND value ~ '^\\d+$' ORDER BY CAST(value AS INTEGER) ASC FETCH FIRST 1 ROW WITH TIES);`
 
**User question:** {input}
"""
)



ROUTE_PROMPT_RENAULT = ChatPromptTemplate.from_template(
    """
    You are an expert router for a Renault Dealer Quality Assessment chatbot.
    Your job is to decide which data source is best suited to answer the user's question.

    You have 3 possible tools:

    1.  **file_vector_retrieve:**
        - Use this ONLY for questions about the general content or textual descriptions within a specific audit PDF.
        - This is for summarization, explanations of sections, or finding descriptive text that is not a structured metric.
        - Examples:
            - "Summarize this audit report."
            - "What does the customer journey section say?"

    2.  **postgres_retrieve:**
        - Use this for any question that can be answered by querying the structured data in the `dealer_stats` or `dealer_qa_stats` tables.
        - This includes scores, counts, averages, rankings, or filtering by specific criteria like auditor or country.
        - It also includes questions about specific Q&A checks.
        - Examples:
            - "Which dealer has the highest restitution score?"
            - "List all dealers audited by JULIE WUYTS."
            - "How many dealers got more than 10 KOs?"
            - "What is the average digital score?"

    3.  **not_answerable:**
        - Use this if the question is unrelated to the audit report's content or the queryable database metrics.
        - Examples:
            - "What's the weather today?"
            - "Who is the CEO of Renault?"
            - "What will Renault's sales forecast be for next year?"

    ---
    **Decision Rules (HIGHEST PRIORITY):**

    - **GOLDEN RULE:** If the question contains keywords like **'score', 'average', 'count', 'highest', 'lowest', 'how many', 'list dealers',** or asks for a number, you **MUST** choose **`postgres_retrieve`**.
    - If the question asks to summarize or explain "the document" or "the file" -> choose `file_vector_retrieve`.
    - If none of the above apply -> choose `not_answerable`.

    Question: {question}

    Respond with ONLY ONE of the following exact values: "postgres_retrieve", "file_vector_retrieve", or "not_answerable".
    """
)


ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
"""
You are an expert data analyst. Your task is to summarize the raw SQL data provided into a clear, insightful, and actionable narrative for the user.
 
**User's Original Question:** {input}
 
**SQL Query Result (JSON Table):**
{db_results}
 
---
**CRITICAL OUTPUT FORMATTING RULES (HIGHEST PRIORITY):**
1.  **Direct Answer (If Applicable):**
    * If the original question is simple, direct, or only asks for a single piece of data (e.g., "What is the average score?", "Who is the auditor?"), your final output **MUST BE ONLY A SENTANCE**, without any explanation.
2.  **Tabular Data Request:**
    * If the question explicitly asks for a "list", "table", "all", or "show details for all," or if the SQL result naturally contains more than 3 rows/columns of simple values, you **MUST format the entire SQL Query Result** ({db_results}) **as a clean Markdown table** in your response. You can add narrative or summary also.
3.  **Detailed Narrative/Reason Request (Diagnostic Mode):**
    * If the question asks for a "reason", "why", "cause", "explain", "detail", or "breakdown," or if the SQL result contains `comment`, `question`, or `answer` columns (indicating diagnostic Q&A data), follow the detailed **Summary Instructions** below.
 
    **Summary Instructions:**
 
    1.  **Analyze Failures:** The primary goal is to explain why the score/performance (related to the original question) might be low. Focus heavily on records where the 'answer' is **'KO'**.explain in detail with each comment.
    2.  **Extract Key Issues:** Review the 'question' and 'comment' columns for all 'KO' records. Synthesize the comments to identify 2-3 **major themes or recurring issues** that explain the failures.Similiarly for explaining success you should review the columns of all 'OK' answers.
    3.  **Use Comments:** The 'comment' column contains the auditor's key context and reasoning. You **MUST** use this information to provide specific, textual evidence in your summary. Do not simply list the questions.
    4.  **Acknowledge Successes (Briefly):** Briefly mention any patterns of success where the 'answer' is 'OK' if it adds meaningful context.
    5.  * You DO NOT need to show the table unless it is asked seperately.
    6.  **Ignore Missing Data:**
        * If the 'db_results' contains no records, state that no specific issues were found for the requested diagnostic breakdown.
        * If the 'db_results' contains records, but ALL answers are 'OK' (i.e., no 'KO's are present), you MUST begin the response with a statement affirming the high performance, such as: "The performance is quite high." and fetch the curresponding statistic score.
---
 
"""
)