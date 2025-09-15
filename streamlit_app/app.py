
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

        response.raise_for_status() # Raises an HTTPError for bad responses (4XX or 5XX)
        # Handle cases where the response might be empty
        if response.status_code == 204: # No Content
             return {}
        # Handle specific status codes from your API if necessary
        if response.status_code == 208: # Already Reported (as in your original code)
             st.info("Tables were already generated for this document.")
             return {"status": "already_generated"}
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"API Error at endpoint '{endpoint}': {e}")
        return None


# --- UI and Response Handling Functions ---
def display_response(data):
    """Intelligently displays a response from the backend and stores it in session state."""
    content_to_store = ""

    # Check for a single key-value pair in a list, e.g., [{'total_revenue': 50000}]
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

    # Handle other data types
    elif isinstance(data, str):
        st.markdown(data)
        content_to_store = data
    elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
        df = pd.DataFrame(data)
        st.dataframe(df)
        content_to_store = df.to_markdown(index=False)
    elif isinstance(data, (dict, list)):
        st.json(data)
        content_to_store = f"```json\n{json.dumps(data, indent=2)}\n```"
    else:
        st.write(data) # Fallback for any other data type
        content_to_store = str(data)
    
    # Append the assistant's message to the chat history
    st.session_state.messages.append({"role": "assistant", "content": content_to_store})


# --- Page Rendering Functions ---
def render_sidebar():
    """Renders the sidebar with a 'New Chat' button."""
    with st.sidebar:
        st.title("֎ Renault Chat ")
        st.info("Query existing audit reports or upload a new document and start chat")
        st.title("")

        if st.button("➕ New Chat"):
            # Reset the session state to go back to the home page
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

def render_home_page():
    """Renders the initial welcome page with two main options."""
    st.title("Your Intelligent Report Assistant!֎")
    st.markdown("")
    st.markdown("")
    st.markdown("")
    st.markdown("")

    col1, col2 = st.columns(2)
    
    if col1.button("💬 Start a New Chat", use_container_width=True):
        st.session_state.app_mode = "chat"
        st.rerun()
        
    if col2.button("⬆️ Upload a New Report", use_container_width=True):
        st.session_state.app_mode = "upload"
        st.rerun()

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
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

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
                response_data = call_api(
                    "report/chat", 
                    json_payload={"chatid": st.session_state.chat_id, "query": user_prompt}
                )
                
                if response_data and "data" in response_data:
                    response_string = response_data["data"].get("response", "Sorry, I couldn't find an answer.")
                    try:
                        # The API might return a JSON string inside the 'response' field
                        final_data = json.loads(response_string)
                    except (json.JSONDecodeError, TypeError):
                        # Or it might just be a plain string
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
elif st.session_state.app_mode == "upload":
    render_upload_page()
elif st.session_state.app_mode == "chat":
    render_chat_page()


