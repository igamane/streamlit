import os
import openai
import time
import streamlit as st
import json
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Function to initialize session state variables
def init():
    if 'assistant' not in st.session_state:
        st.session_state['assistant'] = None

    if 'thread' not in st.session_state:
        st.session_state['thread'] = None

    if 'conversation_state' not in st.session_state:
        st.session_state['conversation_state'] = []

    if 'last_openai_run_state' not in st.session_state:
        st.session_state['last_openai_run_state'] = None

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "run" not in st.session_state:
        st.session_state.run = None

    if "file_ids" not in st.session_state:
        st.session_state.file_ids = []

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

# Set OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# Retrieve assistant IDs from environment variables
ASSISTANT_ID_ITF_JUNIORS = os.getenv('ASSISTANT_ID_ITF_JUNIORS')
ASSISTANT_ID_UTR = os.getenv('ASSISTANT_ID_UTR')
ASSISTANT_ID_USTA_RANKING = os.getenv('ASSISTANT_ID_USTA_RANKING')
ASSISTANT_ID_USTA_GENERAL = os.getenv('ASSISTANT_ID_USTA_GENERAL')
ASSISTANT_ID_WTN = os.getenv('ASSISTANT_ID_WTN')

# Create a client instance
client = openai.Client()

# Load assistant details from JSON file
try:
    with open('assistant_details.json', 'r') as json_file:
        assistant_details = json.load(json_file)
except FileNotFoundError:
    print("Error: assistant_details.json file not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print("Error: assistant_details.json is not a valid JSON file.")
    sys.exit(1)

# Function to update starter questions based on the assistant name
def update_starter_questions(assistant_id):
    for assistant_name, details in assistant_details.items():
        if details.get("id") == assistant_id:
            return details.get("starter_questions", [])
    st.error(f"Assistant with ID '{assistant_id}' not found in assistant_details.json.")
    return []
    
# Function to wait on a run to complete
def wait_on_run(run, thread):
    attempts = 0
    max_attempts = 100  # Adjust this value as needed
    while (run.status == "queued" or run.status == "in_progress") and attempts < max_attempts:
        time.sleep(0.5)
        run = openai.Thread.retrieve_run(thread_id=thread.id, run_id=run.id)
        attempts += 1
    if attempts == max_attempts:
        st.error("Timeout waiting for run to complete.")
    return run

# Function to initialize session state variables
def init_session_state():
    if 'conversation_state' not in st.session_state:
        st.session_state['conversation_state'] = []

    if 'last_openai_run_state' not in st.session_state:
        st.session_state['last_openai_run_state'] = None

    if 'thread_state' not in st.session_state:
        st.session_state['thread_state'] = client.beta.threads.create()

    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = st.session_state['thread_state'].id

# Function to create and run a thread
def create_and_run_thread(assistant_id, user_query):
    thread_state = "thread_state"
    last_openai_run_state = "last_openai_run_state"

    current_assistant = st.session_state.get("current_assistant")

    if st.session_state.get(thread_state) is None or current_assistant != st.session_state.get("last_assistant"):
        st.session_state[thread_state] = client.beta.threads.create()
        st.session_state['thread_id'] = st.session_state['thread_state'].id
        st.session_state['last_assistant'] = current_assistant

    # Create and run a thread
    message = client.beta.threads.messages.create(thread_id=st.session_state[thread_state].id, role="user", content=user_query)
    st.session_state['conversation_state'].append({"role": "user", "content": message.content})
    run = client.beta.threads.runs.create(
        assistant_id=assistant_id,
        thread_id=st.session_state[thread_state].id,
    )
    while run.status != "completed":
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=st.session_state[thread_state].id, run_id=run.id)
    st.session_state[last_openai_run_state] = run
    messages = client.beta.threads.messages.list(thread_id=st.session_state[thread_state].id)
    process_messages()
    return messages

def format_response(response):
    # Check if msg_content is a non-empty list and if the first element (which is the last message) has the required attributes
    if isinstance(response, list) and response and hasattr(response[0], 'text') and hasattr(response[0].text, 'value'):
        # Extract the value of the 'text' attribute from the first element and assign it to formatted_response
        formatted_response = response[0].text.value
        return formatted_response  # Return the extracted value
    else:
        return None  # Return None if the conditions are not met
    
def process_messages():
    thread_state = "thread_state"
    conversation_state = "conversation_state"

    # Retrieve all the messages
    messages = client.beta.threads.messages.list(thread_id=st.session_state[thread_state].id)

    # Process messages
    for msg in messages.data:
        if msg.role == "assistant":
            formatted_response = format_response(msg.content)
            # formatted_response = msg.content[0].text.value if isinstance(msg.content, list) and msg.content and hasattr(msg.content[0], 'text') and hasattr(msg.content[0].text, 'value') else None
            st.session_state[conversation_state].append({"role": "assistant", "content": formatted_response})

def display_starter_questions(assistant_id):
    if not st.session_state.get("starter_displayed", False):
    # starter questions
        starter_questions = update_starter_questions(assistant_id)
        
        placeholder = st.empty()

        col1, col2 = placeholder.columns(2)

        clicked_question = False

        question_v = ""
        with col1:
            for idx, question in enumerate(starter_questions[:2]):
                button_key = f"btn_col1_{idx + 1}"  # Unique key for column 1 buttons
                if st.button(question, key=button_key):
                    question_v = question
                    clicked_question = True
                    # Replace user prompt with the starter question when clicked
                    break  # Exit the loop if a question is clicked

        with col2:
            for idx, question in enumerate(starter_questions[2:]):
                button_key = f"btn_col2_{idx + 1}"  # Unique key for column 2 buttons
                if st.button(question, key=button_key):
                    question_v = question
                    clicked_question = True
                    # Replace user prompt with the starter question when clicked
                    break  # Exit the loop if a question is clicked

        if clicked_question:
            placeholder.empty()
            st.session_state.messages.append({"role": "user", "content": question_v})
            with st.chat_message("user"):
                st.markdown(question_v)
            # Process the assistant's response using the starter question
            st.session_state.starter_displayed = True
            process_assistant_response(assistant_id, question_v)
            


def get_response(assistant_id):
    # Check if 'messages' key is not in session_state
    if "messages" not in st.session_state:
    # If not present, initialize 'messages' as an empty list
        st.session_state.messages = []
    # Iterate through messages in session_state
    for message in st.session_state.messages:
    # Display message content in the chat UI based on the role
        with st.chat_message(message["role"]):
            st.markdown(message["content"])    
    if not st.session_state.get("starter_displayed", False):
    # starter questions
        starter_questions = update_starter_questions(assistant_id)
        
        placeholder = st.empty()

        col1, col2 = placeholder.columns(2)

        clicked_question = False

        question_v = ""
        with col1:
            for idx, question in enumerate(starter_questions[:2]):
                button_key = f"btn_col1_{idx + 1}"  # Unique key for column 1 buttons
                if st.button(question, key=button_key):
                    question_v = question
                    clicked_question = True
                    # Replace user prompt with the starter question when clicked
                    break  # Exit the loop if a question is clicked

        with col2:
            for idx, question in enumerate(starter_questions[2:]):
                button_key = f"btn_col2_{idx + 1}"  # Unique key for column 2 buttons
                if st.button(question, key=button_key):
                    question_v = question
                    clicked_question = True
                    # Replace user prompt with the starter question when clicked
                    break  # Exit the loop if a question is clicked

        if clicked_question:
            placeholder.empty()
            st.session_state.messages.append({"role": "user", "content": question_v})
            with st.chat_message("user"):
                st.markdown(question_v)
            # Process the assistant's response using the starter question
            st.session_state.starter_displayed = True
            process_assistant_response(assistant_id, question_v)
    # Get user input from chat and proceed if a prompt is entered
    if prompt := st.chat_input("Enter your message here"):
        if not st.session_state.get("starter_displayed", False):
            placeholder.empty()
            st.session_state.starter_displayed = True
        # Add user input as a message to session_state
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Display user's message in the chat UI
        with st.chat_message("user"):
            st.markdown(prompt)
        # Process the assistant's response
        process_assistant_response(assistant_id, prompt)

def process_assistant_response(assistant_id, prompt):
    with st.spinner("Thinking..."):
        message_placeholder = st.empty()
        # Create and run a thread with the assistant using the provided assistant_id and user prompt
        message = create_and_run_thread(assistant_id, prompt)
        process_messages()
        content = ""
        # Extract the content from the assistant's response
        thread_message = message.data[0]
        if thread_message.role == 'assistant':
            last_content_text = thread_message.content[0]
            content += last_content_text.text.value + "\n"
        st.session_state.messages.append({"role": "assistant", "content": content})
        # Display the assistant's response in the chat UI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown(content)


# Initialize session state variables
def init():
    st.session_state['assistant'] = None
    st.session_state['thread'] = None
    st.session_state['conversation_state'] = []
    st.session_state['last_openai_run_state'] = None

def chat_prompt(client, assistant_option):
    if prompt := st.chat_input("Enter your message here"):
        with st.chat_message("user"):
            st.markdown(prompt)
    st.session_state.messages = st.session_state.messages.append(client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
    ))

    st.session_state.current_assistant = client.beta.assistants.update(
        st.session_state.current_assistant.id,
        instructions=st.session_state.assistant_instructions,
        name=st.session_state.current_assistant.name,
        tools = st.session_state.current_assistant.tools,
        model=st.session_state.model_option,
        file_ids=st.session_state.file_ids,
    )

    st.session_state.run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_option,
        tools = [{"type": "code_interpreter"}],

    )
        
    print(st.session_state.run)
    pending = False
    while st.session_state.run.status != "completed":
        if not pending:
            with st.chat_message("assistant"):
                st.markdown("AnalAssist is thinking...")
            pending = True
        time.sleep(3)
        st.session_state.run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=st.session_state.run.id,
        )

def get_assistant_id(assistant_name):
    assistant_id_map = {
        "ITF Juniors": ASSISTANT_ID_ITF_JUNIORS,
        "UTR": ASSISTANT_ID_UTR,
        "USTA Ranking": ASSISTANT_ID_USTA_RANKING,
        "USTA General": ASSISTANT_ID_USTA_GENERAL,
        "WTN": ASSISTANT_ID_WTN
    }
    
    return assistant_id_map.get(assistant_name)

def main():
    st.title('Tennis Oracle - AI Assistants')

    # Initialize session state variables if they don't exist
    init_session_state()

    assistant_name = st.sidebar.selectbox('Choose an assistant', ["Select Category"] + list(assistant_details.keys()))

    if assistant_name != "Select Category":
        assistant_id = get_assistant_id(assistant_name)
        # Reset the conversation & starter questions, if the assistant has been changed
        if st.session_state.get("current_assistant") != assistant_name:
            st.session_state.starter_displayed = False
            st.session_state.messages = []
            st.session_state.current_assistant = assistant_name
        get_response(assistant_id)
            

# Call the main function to run the app
if __name__ == "__main__":
    main()
