import ast
import streamlit as st
import requests
import uuid
import pandas as pd
import json
import os
 
 
# --- Configuration ---
API_BASE_URL = "http://127.0.0.1:8000"
API_KEY = "a8861fce-c6e4-489e-9426-a8b12eca8c70"
 
 
# --- API Helper Functions ---
def call_api(endpoint, method="post", files=None, data=None, json_payload=None):
    """A generalized function to handle all API calls."""
    headers = {'access-token': API_KEY}
    url = f"{API_BASE_URL}/{endpoint}"
 
    try:
        if method.lower() == "post":
            response = requests.post(url, headers=headers, files=files, data=data, json=json_payload)
 
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
 
        # Handle cases where the response might be empty
        if response.status_code == 204:  # No Content
            return {}
 
        # Handle specific status codes from your API if necessary
        if response.status_code == 208:  # Already Reported (as in your original code)
            st.info("Tables were already generated for this document.")
            return {"status": "already_generated"}
 
        return response.json()
 
    except requests.exceptions.RequestException as e:
        st.error(f"API Error at endpoint '{endpoint}': {e}")
        return None
 
 
# --- UI and Response Handling Functions ---
def display_response(data):
    """
    Intelligently displays a response from the backend (text, data, or chart)
    and stores it in session state.
    """
    content_to_store = ""
 
    # 1. Check for a single key-value pair in a list, e.g., [{'total_revenue': 50000}]
    is_single_value = (
        isinstance(data, list) and len(data) == 1 and
        isinstance(data[0], dict) and len(data[0]) == 1
    )
 
    if is_single_value:
        key, value = list(data[0].items())[0]
        label = key.replace("_", " ").title()
        # Format numbers nicely
        if isinstance(value, (int, float)):
            formatted_value = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
        else:
            formatted_value = value
 
        sentence = f"The **{label}** is **{formatted_value}**."
        st.markdown(sentence)
        content_to_store = sentence
 
    # 2. Check for a chart specification (Vega-Lite/Altair or custom chart format)
    is_vega_lite = isinstance(data, dict) and ('$schema' in data or 'mark' in data)
    is_custom_chart = isinstance(data, dict) and 'chart_type' in data and 'data' in data and 'encoding' in data or 'layer' in data
 
    if is_vega_lite or is_custom_chart:
        chart_summary = data.pop('chart_summary', None)                                          
        chart_spec = data
        if is_custom_chart:
            # Convert custom format into a standard Vega-Lite spec
            chart_spec = {
                "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                # Vega-Lite expects inline data to be under the 'values' key
                "data": {"values": data["data"]},
               
               
            }
            # Check if it is a layered chart
            is_layered = data.get("chart_type") == "layer" or "layer" in data
            if is_layered:
                # For layered charts, use the 'layer' array as the primary composition method
                if 'layer' in data:
                    chart_spec['layer'] = data['layer']
            else:
                # For single-mark charts, use 'mark' and 'encoding'
                chart_spec["mark"] = data.get("chart_type", "bar")
                if 'encoding' in data:
                    chart_spec["encoding"] = data["encoding"]
                                                 
            if 'transform' in data:
                chart_spec['transform'] = data['transform']                      
            # Optional: Add title if provided
            if 'title' in data:
                chart_spec['title'] = data['title']
 
        try:
            if chart_summary:
                st.info(f"**Key Findings:** {chart_summary}")
            # Use st.vega_lite_chart to render the chart visually
            st.vega_lite_chart(chart_spec, use_container_width=True)
            st.success("Chart successfully generated!")
            # Store the final Vega-Lite JSON for history
            content_to_store =  f"{chart_summary}\nChart generated successfully.```json\n{json.dumps(chart_spec, indent=2)}\n```" if chart_summary else f"Chart generated successfully. JSON:\n{json.dumps(chart_spec, indent=2)}"                                                                                                                                                                                                                      
            # content_to_store = f"```json\n{json.dumps(chart_spec, indent=2)}\n```"
        except Exception as e:
            st.error(f"Failed to render chart: {e}. Displaying raw JSON instead.")
            st.json(data)
            content_to_store = f"```json\n{json.dumps(data, indent=2)}\n```"
 
    # 3. Handle plain string/markdown response
    elif isinstance(data, str):
        st.markdown(data)
        content_to_store = data
 
    # 4. Handle list of dictionaries (tabular data)
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        if not data:
            message = "I couldn't find any results that match your criteria. 🤷"
            st.markdown(message)
            content_to_store = message
        else:
            df = pd.DataFrame(data)
            st.dataframe(df)
            content_to_store = df.to_markdown(index=False)
 
    # 5. Fallback for general JSON objects or lists (if not a chart spec)
    elif isinstance(data, (dict, list)):
        st.json(data)
        content_to_store = f"```json\n{json.dumps(data, indent=2)}\n```"
 
    else:
        st.write(data)  # Fallback for any other data type
        content_to_store = str(data)
 
    # Append the assistant's message to the chat history
    st.session_state.messages.append({"role": "assistant", "content": content_to_store})
 
 
# --- Page Rendering Functions ---
def render_sidebar():
    """Renders the sidebar with a 'New Chat' button."""
    logo_path = "streamlit_app/renault_logo.png"
    with st.sidebar:
        col_logo, col_title = st.columns([1, 3])
        with col_logo:
            # Display the logo in the first column
                st.image(logo_path, width=100)            
        with col_title:
            st.markdown("## Audit Analyser", unsafe_allow_html=True)
        # st.title(" Audit Analyser ")
        # st.info("Query existing audit reports or upload a new document and start chat")
        st.info("Query existing audit reports")

        st.title("")
 
        if st.button("➕ New Chat"):
            # Reset the session state to go back to the home page
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
 
 
def render_home_page():
    """Renders the initial welcome page with two main options."""
    st.title("Your Intelligent Report Assistant!")
    st.markdown("")
    st.markdown("")
    st.markdown("")
    st.markdown("")
 
    col1, col2 = st.columns(2)
 
    if col1.button("💬 Start a New Chat", use_container_width=True):
        st.session_state.app_mode = "chat"
        st.rerun()
 
    # if col2.button("⬆️ Upload a New Report", use_container_width=True):
    #     st.session_state.app_mode = "upload"
    #     st.rerun()
 
 
def render_upload_page():
    """Renders the page for uploading and processing a file."""
    st.header("Upload and Analyze a Report")
    uploaded_file = st.file_uploader("Select a PDF file to analyze", type="pdf")
 
    if st.button("Analyze Document", disabled=(uploaded_file is None), use_container_width=True):
        with st.status("Analyzing your document...", expanded=True) as status:
            try:
                # Step 1: Upload
                status.write("➡️ Step 1 of 3: Uploading file...")
                files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                upload_response = call_api("report/upload", files=files)
 
                if not upload_response or "data" not in upload_response:
                    raise Exception("File upload failed or returned invalid data.")
 
                chat_id = upload_response["data"].get("chatid")
                gu_id = upload_response["data"].get("gu_id")
 
                if not chat_id or not gu_id:
                    raise Exception("Upload response was missing a chat_id or gu_id.")
 
                # Step 2: Embed
                status.write("➡️ Step 2 of 3: Embedding document...")
                embed_response = call_api("report/embed", data={"chatid": chat_id, "gu_id": gu_id})
 
                if embed_response is None:
                    raise Exception("Document embedding failed.")
 
                # Step 3: Generate Tables
                status.write("➡️ Step 3 of 3: Generating tables...")
                tables_response = call_api("report/generate-tables", data={"chatid": chat_id, "gu_id": gu_id})
 
                if tables_response is None:
                    raise Exception("Table generation failed.")
 
                # If all steps succeed, update the status and session
                status.update(label="✅ Analysis Complete!", state="complete")
                st.session_state.chat_id = chat_id
                st.session_state.analysis_complete = True
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": f"I've finished analyzing **{uploaded_file.name}**. What would you like to know?"
                }]
 
            except Exception as e:
                # If any step fails, show an error
                status.update(label=f"❌ Analysis Failed", state="error")
                st.error(e)
 
    # After analysis is complete, prompt the user to start chatting
    if st.session_state.get("analysis_complete"):
        st.success("Your document is ready!")
        if st.button("Start Chatting", use_container_width=True):
            st.session_state.app_mode = "chat"
            st.rerun()
 
 
def render_chat_page():
    """Renders the main chat interface."""
    st.header("Ask anything about reports")
 
    # Display the entire chat history
    for message in st.session_state.messages:
        # print(st.markdown(message["content"]))
        chart_rendered_successfully = False
        with st.chat_message(message["role"]):
            content = message["content"]
                                                                               
            json_block_start = content.find("```json")
            json_block_end = content.rfind("```")
            if json_block_start != -1 and json_block_end > json_block_start:
                # 1. Strip the surrounding Markdown fences and 'json' label
                summary = content[:json_block_start].strip()
 
                # 1. Extract and display the prose part (Summary, success message, etc.)
                if summary:
                    # Render the summary/prose first
                    st.markdown(summary)
               
                # 2. Extract and parse the JSON part
                json_string = content[json_block_start + 7:json_block_end].strip()
                                                                                 
                try:
                    # 2. Safely load the inner JSON string
                    chart_data = json.loads(json_string)
 
                    # 3. Check if it's a valid Vega-Lite spec (or one of your custom specs)
                    is_vega_lite = "$schema" in chart_data and "vega-lite" in chart_data["$schema"]
                    is_custom_chart = 'mark' in chart_data or 'chart_type' in chart_data or 'layer' in chart_data
 
                    if is_vega_lite or is_custom_chart:
                        try:
                            st.vega_lite_chart(chart_data, use_container_width=True)
                            chart_rendered_successfully = True
                        except Exception as e:
                            # If rendering fails (e.g., first run for complex layered charts),
                            # we catch it and suppress the visual chart, allowing the raw markdown to display below.
                            st.error(f"Error rendering chart from history: {e}")
                            pass    
                        # 4. Render the chart visually using Streamlit's native component
                        #st.vega_lite_chart(chart_data, use_container_width=True)
                        #continue  # Skip st.markdown for this message
 
                    # If it was a JSON code block but didn't match the chart criteria,
                    # it falls through to be rendered as a regular code block below.
 
                except json.JSONDecodeError:
                    # If the JSON is invalid, treat it as regular markdown/text
                    pass
                   
            if not chart_rendered_successfully:
                st.markdown(message["content"])
 
            #st.markdown(message["content"])
           
    current_mode = "file" if st.session_state.app_mode == "upload" else "database"
 
    # Handle new user input
    if prompt := st.chat_input("Ask a question about the report..."):
        # Add user's message to history and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.rerun()
 
    # Generate a response if the last message is from the user
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_prompt = st.session_state.messages[-1]["content"]
 
        # If it's a new chat without an upload, create a new chat_id
        if not st.session_state.chat_id:
            st.session_state.chat_id = str(uuid.uuid4())
 
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
 
                # --- TIMING SECTION START (Easy to remove) ---
                import time
                start_time = time.time()
                # --------------------------------------------
               
                response_data = call_api(
                    "report/chat",
                    json_payload={"chatid": st.session_state.chat_id, "query": user_prompt,"chat_mode": current_mode}
                )
 
                # --- TIMING SECTION END (Easy to remove) ---
                end_time = time.time()
                elapsed_time = end_time - start_time
                st.caption(f"⏱️ Answered in {elapsed_time:.2f} seconds")
                # ------------------------------------------
 
 
 
                if response_data and "data" in response_data:
                    response_string = response_data["data"].get("response", "Sorry, I couldn't find an answer.")
                    try:
                        # The API might return a JSON string inside the 'response' field
                        final_data = json.loads(response_string)
 
                    except json.JSONDecodeError:
                        # Or it might just be a plain string
                        try:
                            # Fallback for Python-style list string
                            final_data = ast.literal_eval(response_string)
                        except Exception:
                            final_data = response_string
                               
 
                    display_response(final_data)
                else:
                    st.error("Failed to get a valid response from the API.")
 
 
# --- Main App Logic ---
# Initialize session state variables
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "home"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None
 
# Always render the sidebar
render_sidebar()
 
# Main router to display the correct page
if st.session_state.app_mode == "home":
    render_home_page()
# elif st.session_state.app_mode == "upload":
#     render_upload_page()
elif st.session_state.app_mode == "chat":
    render_chat_page()








# ########## no file upload ##########
# import ast
# import streamlit as st
# import requests
# import uuid
# import pandas as pd
# import json
# import os
# import time
 
# # --- Configuration ---
# API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
# API_KEY = "a8861fce-c6e4-489e-9426-a8b12eca8c70"
 
# # --- API Helper Functions ---
# def call_api(endpoint, method="post", files=None, data=None, json_payload=None):
#     """A generalized function to handle all API calls."""
#     headers = {'access-token': API_KEY}
#     url = f"{API_BASE_URL}/{endpoint}"
 
#     try:
#         if method.lower() == "post":
#             response = requests.post(url, headers=headers, files=files, data=data, json=json_payload)
 
#         response.raise_for_status()
 
#         # Handle cases where the response might be empty
#         if response.status_code == 204:  # No Content
#             return {}
 
#         # Handle specific status codes from your API if necessary
#         if response.status_code == 208:  # Already Reported
#             st.info("Tables were already generated for this document.")
#             return {"status": "already_generated"}
 
#         return response.json()
 
#     except requests.exceptions.RequestException as e:
#         st.error(f"API Error at endpoint '{endpoint}': {e}")
#         return None
 
 
# # --- UI and Response Handling Functions ---
# def display_response(data):
#     """
#     Intelligently displays a response from the backend (text, data, or chart)
#     and stores it in session state.
#     """
#     content_to_store = ""
 
#     # 1. Check for a single key-value pair in a list
#     is_single_value = (
#         isinstance(data, list) and len(data) == 1 and
#         isinstance(data[0], dict) and len(data[0]) == 1
#     )
 
#     if is_single_value:
#         key, value = list(data[0].items())[0]
#         label = key.replace("_", " ").title()
#         # Format numbers nicely
#         if isinstance(value, (int, float)):
#             formatted_value = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"
#         else:
#             formatted_value = value
 
#         sentence = f"The **{label}** is **{formatted_value}**."
#         st.markdown(sentence)
#         content_to_store = sentence
 
#     # 2. Check for a chart specification (Vega-Lite/Altair or custom chart format)
#     is_vega_lite = isinstance(data, dict) and ('$schema' in data or 'mark' in data)
#     is_custom_chart = isinstance(data, dict) and ('chart_type' in data and 'data' in data and 'encoding' in data or 'layer' in data)
 
#     if is_vega_lite or is_custom_chart:
#         chart_summary = data.pop('chart_summary', None)                                  
#         chart_spec = data
#         if is_custom_chart:
#             # Convert custom format into a standard Vega-Lite spec
#             chart_spec = {
#                 "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
#                 # Vega-Lite expects inline data to be under the 'values' key
#                 "data": {"values": data["data"]},
#             }
#             # Check if it is a layered chart
#             is_layered = data.get("chart_type") == "layer" or "layer" in data
#             if is_layered:
#                 if 'layer' in data:
#                     chart_spec['layer'] = data['layer']
#             else:
#                 chart_spec["mark"] = data.get("chart_type", "bar")
#                 if 'encoding' in data:
#                     chart_spec["encoding"] = data["encoding"]
                                          
#             if 'transform' in data:
#                 chart_spec['transform'] = data['transform']                      
#             # Optional: Add title if provided
#             if 'title' in data:
#                 chart_spec['title'] = data['title']
 
#         try:
#             if chart_summary:
#                 st.info(f"**Key Findings:** {chart_summary}")
            
#             # Render the chart visually
#             st.vega_lite_chart(chart_spec, use_container_width=True)
            
#             st.success("Chart successfully generated!")
#             # Store the final Vega-Lite JSON for history
#             content_to_store =  f"{chart_summary}\nChart generated successfully.```json\n{json.dumps(chart_spec, indent=2)}\n```" if chart_summary else f"Chart generated successfully. JSON:\n{json.dumps(chart_spec, indent=2)}"                                                                                   
 
#         except Exception as e:
#             st.error(f"Failed to render chart: {e}. Displaying raw JSON instead.")
#             st.json(data)
#             content_to_store = f"```json\n{json.dumps(data, indent=2)}\n```"
 
#     # 3. Handle plain string/markdown response
#     elif isinstance(data, str):
#         st.markdown(data)
#         content_to_store = data
 
#     # 4. Handle list of dictionaries (tabular data)
#     elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
#         if not data:
#             message = "I couldn't find any results that match your criteria. 🤷"
#             st.markdown(message)
#             content_to_store = message
#         else:
#             df = pd.DataFrame(data)
#             st.dataframe(df)
#             content_to_store = df.to_markdown(index=False)
 
#     # 5. Fallback for general JSON objects or lists
#     elif isinstance(data, (dict, list)):
#         st.json(data)
#         content_to_store = f"```json\n{json.dumps(data, indent=2)}\n```"
 
#     else:
#         st.write(data)  # Fallback for any other data type
#         content_to_store = str(data)
    
#     # Append the assistant's message to the chat history
#     st.session_state.messages.append({"role": "assistant", "content": content_to_store})
 
# def load_custom_css():
#     st.markdown(
#         """
#         <style>
#             /* 1. Sidebar Background -> Black */
#             [data-testid="stSidebar"] {
#                 background-color: #000000;
#             }

#             /* 2. Global Text in Sidebar -> White */
#             /* This makes all general text white */
#             [data-testid="stSidebar"] * {
#                 color: #FFFFFF !important;
#             }

#             /* 3. Style the st.info Box */
#             [data-testid="stSidebar"] .stAlert {
#                 background-color: #1E1E1E;
#                 border: 1px solid #333;
#             }
#             /* Override text color inside the info box to Grey */
#             [data-testid="stSidebar"] .stAlert p, 
#             [data-testid="stSidebar"] .stAlert div,
#             [data-testid="stSidebar"] .stAlert span {
#                 color: #D3D3D3 !important; 
#             }

#             /* 4. CUSTOM "NEW CHAT" BUTTON STYLING */
#             [data-testid="stSidebar"] button {
#                 background-color: #FFFFFF !important; /* White Background */
#                 border: none !important;
#                 border-radius: 8px !important;
#                 font-weight: bold !important;
#                 padding-top: 0.5rem !important;
#                 padding-bottom: 0.5rem !important;
#                 transition: all 0.2s ease-in-out !important;
#             }

#             /* --- THE FIX: Force ALL text inside the button to be Black --- */
#             [data-testid="stSidebar"] button, 
#             [data-testid="stSidebar"] button p, 
#             [data-testid="stSidebar"] button div, 
#             [data-testid="stSidebar"] button span {
#                 color: #000000 !important;
#             }

#             /* Hover Effect for the Button */
#             [data-testid="stSidebar"] button:hover {
#                 background-color: #FCD535 !important; /* Renault Yellow on Hover */
#                 transform: scale(1.02);              
#                 box-shadow: 0 0 10px rgba(252, 213, 53, 0.5);
#             }
            
#             /* Ensure text stays black on hover too */
#             [data-testid="stSidebar"] button:hover * {
#                 color: #000000 !important;
#             }
            
#             /* Remove the default red border Streamlit adds sometimes */
#             [data-testid="stSidebar"] button:active, 
#             [data-testid="stSidebar"] button:focus {
#                 border: none !important;
#                 outline: none !important;
#             }
#         </style>
#         """,
#         unsafe_allow_html=True
#     )


# # --- Page Rendering Functions ---
# def render_sidebar():
#     """Renders the sidebar with a 'New Chat' button."""
#     logo_path = "streamlit_app/renault_logo.png"
#     with st.sidebar:
#         # 1. Use vertical_alignment="center" to align items vertically
#         col_logo, col_title = st.columns([1.2, 2.8], vertical_alignment="center") 
        
#         with col_logo:
#             if os.path.exists(logo_path):
#                 st.image(logo_path, width=180)            
        
#         with col_title:
#             # 2. Use HTML to remove default margins so it centers perfectly
#             st.markdown(
#                 "<h1 style='margin: 0; padding: 0; font-size: 24px;'>Audit Analyser</h1>", 
#                 unsafe_allow_html=True
#             )
        
#         # --- Description ---
#         st.info("Unlock the full potential of your dealer audit reports.")
#         st.title("")
 
#         if st.button("➕ New Chat"):
#             st.session_state.messages = []
#             st.session_state.chat_id = None
#             st.rerun()

 
# def render_home_page():
#     """Renders the simplified home page."""
#     st.title("Your Intelligent Report Assistant!")
#     st.markdown("")
#     st.info(" Welcome! Ask any question about the audit database.")
#     st.markdown("")
 
#     if st.button("💬 Start Chatting", use_container_width=True):
#         st.session_state.app_mode = "chat"
#         st.rerun()
 
 
# def render_chat_page():
#     """Renders the main chat interface."""
#     st.header("Ask anything about reports")
 
#     # Display the entire chat history
#     for message in st.session_state.messages:
#         chart_rendered_successfully = False
#         with st.chat_message(message["role"]):
#             content = message["content"]
                                                        
#             json_block_start = content.find("```json")
#             json_block_end = content.rfind("```")
            
#             if json_block_start != -1 and json_block_end > json_block_start:
#                 # 1. Strip the surrounding Markdown fences and 'json' label
#                 summary = content[:json_block_start].strip()
 
#                 # Render the summary/prose first
#                 if summary:
#                     st.markdown(summary)
                
#                 # 2. Extract and parse the JSON part
#                 json_string = content[json_block_start + 7:json_block_end].strip()
                                                  
#                 try:
#                     chart_data = json.loads(json_string)
 
#                     # 3. Check if it's a valid Vega-Lite spec
#                     is_vega_lite = "$schema" in chart_data and "vega-lite" in chart_data["$schema"]
#                     is_custom_chart = 'mark' in chart_data or 'chart_type' in chart_data or 'layer' in chart_data
 
#                     if is_vega_lite or is_custom_chart:
#                         try:
#                             st.vega_lite_chart(chart_data, use_container_width=True)
#                             chart_rendered_successfully = True
#                         except Exception as e:
#                             # If rendering fails, suppress and allow raw text fallback
#                             # st.error(f"Error rendering chart from history: {e}")
#                             pass    
 
#                 except json.JSONDecodeError:
#                     pass
                    
#             if not chart_rendered_successfully:
#                 st.markdown(message["content"])
 
#     # --- IMPORTANT: Fixed Mode ---
#     current_mode = "database"
 
#     # Handle new user input
#     if prompt := st.chat_input("Ask a question about the report..."):
#         st.session_state.messages.append({"role": "user", "content": prompt})
#         st.rerun()
 
#     # Generate a response if the last message is from the user
#     if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
#         user_prompt = st.session_state.messages[-1]["content"]
 
#         # Create a new chat_id if needed
#         if not st.session_state.chat_id:
#             st.session_state.chat_id = str(uuid.uuid4())
 
#         with st.chat_message("assistant"):
#             with st.spinner("Thinking..."):
#                 start_time = time.time()
                
#                 response_data = call_api(
#                     "report/chat", 
#                     json_payload={
#                         "chatid": st.session_state.chat_id, 
#                         "query": user_prompt,
#                         "chat_mode": current_mode
#                     }
#                 )
 
#                 end_time = time.time()
#                 elapsed_time = end_time - start_time
#                 st.caption(f"⏱️ Answered in {elapsed_time:.2f} seconds")
 
#                 if response_data and "data" in response_data:
#                     response_string = response_data["data"].get("response", "Sorry, I couldn't find an answer.")
#                     try:
#                         # Try parsing as JSON first
#                         final_data = json.loads(response_string)
 
#                     except json.JSONDecodeError:
#                         try:
#                             # Fallback for Python-style list string
#                             final_data = ast.literal_eval(response_string)
#                         except Exception:
#                             # Fallback to plain string
#                             final_data = response_string
                                
#                     display_response(final_data)
#                 else:
#                     st.error("Failed to get a valid response from the API.")
 
 
# # --- Main App Logic ---
# # Initialize session state variables
# if "app_mode" not in st.session_state:
#     st.session_state.app_mode = "home"
# if "messages" not in st.session_state:
#     st.session_state.messages = []
# if "chat_id" not in st.session_state:
#     st.session_state.chat_id = None

# # LOAD THE CSS HERE
# load_custom_css()

# # Always render the sidebar
# render_sidebar()
 
# # Main router to display the correct page
# if st.session_state.app_mode == "home":
#     render_home_page()
# elif st.session_state.app_mode == "chat":
#     render_chat_page()