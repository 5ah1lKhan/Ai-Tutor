# frontend/app.py

import streamlit as st
from langchain_core.messages import HumanMessage,AIMessage
import os
import uuid
import json
from untracked_threads import save_thread_id


if not os.getenv('GEMINI_API_KEY'):
    st.warning("Please set your GEMINI API key in the sidebar.")
    with st.sidebar:
        st.title("Ai Tutor")
        api = st.text_input("API Key", type="password", placeholder="Enter your GEMINI API key")
        if api.startswith('"') and api.endswith('"'):
            api = api[1:-1]
        if api:
            st.info(f"API key set successfully!")
            st.session_state['api_key'] = api
            os.environ['GEMINI_API_KEY'] = api
            os.environ['GOOGLE_API_KEY'] = api
            st.rerun()
    


else:
    from graph_database import react_graph , retrieve_all_threads
    #********************* utility functions *********************
    def get_thread_id():
        """Generate a unique thread ID for the conversation."""
        thread_id  = uuid.uuid4()
        # st.session_state['chat_name'][thread_id] = 'Current Chat'
        return thread_id

    def add_thread(thread_id):
        if thread_id not in st.session_state['chat_threads']:
            st.session_state['chat_threads'].append(thread_id)

    def reset_chat():
        # st.session_state['chat_name'][st.session_state['thread_id']] = st.session_state['message_history'][0]['content'][0:15] if st.session_state['message_history'] else "old Chat"
        thread_id = get_thread_id()
        st.session_state['message_history'] = []
        st.session_state['thread_id'] = thread_id
        add_thread(thread_id)
        st.session_state['image_name'] = ""
        st.session_state['image_path'] = ""
        st.rerun()

    def load_conversation(thread_id):
        return react_graph.get_state(config = {'configurable': {'thread_id': thread_id}}).values['messages']

    #********************* Session State *********************
    if 'message_history' not in st.session_state:
        st.session_state['message_history'] = []
    if 'image_name' not in st.session_state:
        st.session_state['image_name'] = ""
        st.session_state['image_path'] = ""
    if 'chat_threads' not in st.session_state:
        st.session_state['chat_threads'] = retrieve_all_threads()
        st.session_state['thread_id'] = st.session_state['chat_threads'][-1] if st.session_state['chat_threads'] else get_thread_id()
    # if 'chat_name' not in st.session_state:
    #     st.session_state['chat_name'] = {}
    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = get_thread_id()
    add_thread(st.session_state['thread_id'])


    CONFIG = {'configurable': {'thread_id': st.session_state['thread_id']}}
    # loading the conversation history
    for message in st.session_state['message_history']:
        if message['role'] == 'image':
            # Display image
            image_path = message['content']
            if os.path.exists(image_path):
                st.image(image_path, caption="Uploaded Image")
        else:
            with st.chat_message(message['role']):
                # st.text(message['content'])
                st.markdown(message['content'])  # Use markdown to render the content properly



    with st.sidebar:
        st.title("Ai Tutor")
        # api = st.text_input("API Key", type="password", placeholder="Enter your GEMINI API key")
        # if api.startswith('"') and api.endswith('"'):
        #     api = api[1:-1]
        # if api:
        #     st.info(f"API key set successfully!")
        #     st.session_state['api_key'] = api
        #     os.environ['GEMINI_API_KEY'] = api
        #     os.environ['GOOGLE_API_KEY'] = api
        
        st.header("Upload an Image")
        uploaded_file = st.file_uploader(
            "Choose an image...",
            label_visibility="collapsed", # Hides the "Choose an image..." label
            type=["jpg", "jpeg", "png"],
            key='image_uploader', # Unique key to avoid conflicts with other widgets
        )
        if uploaded_file:
            if uploaded_file.name != st.session_state['image_name']:
                st.image(uploaded_file)
                st.info(f"File `{uploaded_file.name}` uploaded successfully!")
                image_path = os.path.join("images", uploaded_file.name)
                with open(image_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                st.session_state['image_name'] = uploaded_file.name
                st.session_state['image_path'] = image_path
                st.session_state['message_history'].append({'role': 'image', 'content': image_path})
        if st.button('New Chat'):
            reset_chat()
        st.sidebar.header('Conversations')
        for thread_id in st.session_state['chat_threads'][::-1]:
            # if st.sidebar.button(st.session_state['chat_name'][thread_id] , key=str(thread_id)):
            if st.sidebar.button(str(thread_id)):
                st.session_state['thread_id'] = thread_id
                messages = load_conversation(thread_id)

                temp_messages =[]
                for message in messages:
                    if isinstance(message, HumanMessage):
                        temp_messages.append({'role': 'user', 'content': message.content})
                    elif isinstance(message, AIMessage):
                        temp_messages.append({'role': 'assistant', 'content': message.content})
                st.session_state['message_history'] = temp_messages


    # if not os.getenv('GEMINI_API_KEY'):
    #     st.warning("Please set your GEMINI API key in the sidebar.")
    # else:
    
    user_input = st.chat_input('Type here')
    if user_input:
        save_thread_id(st.session_state['thread_id'])
        # first add the message to message_history
        st.session_state['message_history'].append({'role': 'user', 'content': user_input})
        with st.chat_message('user'):
            st.text(user_input)

        # first add the message to message_history
        with st.chat_message('assistant'):
            ai_message = st.write_stream(
                message_chunk[0].content for message_chunk in react_graph.stream(
                    {"messages": [HumanMessage(content=f"user_input: {user_input}")], "image_path": st.session_state['image_path']},
                    config=CONFIG,
                    stream_mode='messages'
                ) if message_chunk[1].get('langgraph_node') == 'assistant'
            )
        
        st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})