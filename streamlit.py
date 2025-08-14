# frontend/app.py

import streamlit as st
from langchain_core.messages import HumanMessage
import os
from graph import react_graph , set_api_key
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []
if 'image_name' not in st.session_state:
    st.session_state['image_name'] = ""
    st.session_state['image_path'] = ""


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
    api = st.text_input("API Key", type="password", placeholder="Enter your GEMINI API key")
    if api:
        st.session_state['api_key'] = api
        set_api_key(api)
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

user_input = st.chat_input('Type here')
if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # first add the message to message_history
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            message_chunk[0].content for message_chunk in react_graph.stream(
                {"messages": [HumanMessage(content=f"user_input: {user_input}, image_path: {st.session_state['image_path']}")], "config": CONFIG},
                config=CONFIG,
                stream_mode='messages'
            ) if message_chunk[1].get('langgraph_node') == 'assistant'
        )
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})