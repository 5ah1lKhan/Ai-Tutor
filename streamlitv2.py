# frontend/app.py

import streamlit as st
from langchain_core.messages import HumanMessage
import os
# from graph import react_graph , set_api_key\\\
from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.graph import MessagesState
from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import InMemorySaver
import pytesseract
import os
from PIL import Image
from google import genai

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


def set_api_key(api_key):
    """Set the API key for Google Gemini."""
    # global GEMINI_API_KEY
    os.environ['GEMINI_API_KEY'] = api_key
    os.environ['GOOGLE_API_KEY'] = api_key

with st.sidebar:
    api = st.text_input("API Key", type="password", placeholder="Only GEMINI API key")
    if api.startswith('"') and api.endswith('"'):
        api = api[1:-1]
    if api:
        st.info(f"API key set successfully!")
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
# -----------------backend logic-----------------
if not os.environ.get('GEMINI_API_KEY'):
    st.warning("Please enter your GEMINI API key in the sidebar to use the app.")
else:
    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

    #tools
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
    )

    @tool
    def explain_text(input_or_image_text: str) -> str:
        """
        Uses Google Gemini to explain the obatined text from user input and given image in simple terms.
        """
        print("explaining the concept")
        prompt = f"Explain the following concept step-by-step in simple language: {input_or_image_text}"
        response = llm.invoke(prompt)
        return response.content


    @tool
    def generate_feedback(user_name: str, questions: str, answers: str, ) -> str:
        """
        Uses Google Gemini to generate personalized feedback based on current answers and past performance.
        Updates the session history for the user.
        """
        print("generating feedback")
        # Craft prompt with context
        prompt = (
            f"The student {user_name} answered the following questions:\n"
            + "\n".join(questions) + "\n"
            f"With answers: {answers}.\n"
            "Provide encouraging feedback and suggestions for improvement."
        )
        response = llm.invoke(prompt)
        
        feedback = response.content
    
        return feedback


    @tool
    def generate_quiz(input_or_image_text: str, num_questions: int = 5) -> list:
        """
        Generates a list of quiz questions (strings) about the topic_text using Google Gemini.
        """
        print("generating quiz")
        prompt = (
            f"Generate exactly {num_questions} unique multiple-choice questions about the content below. "
            "Do not write any introductory text or repeat yourself. "
            f"CONTENT: \"{input_or_image_text}\"\n\n"
        )
        response = llm.invoke(prompt)
        questions = response.content
        print("question:" , questions)
        print("QUIZ END \n\n")
        return questions

    @tool
    def extract_text_from_image(image_path: str) -> str:
        ''' extract text from image given the image_path'''
        print("reading image")
        # Load image
        from PIL import Image
        print(image_path)
        img = Image.open(image_path)

        try:
            response = client.models.generate_content(
                model='gemma-3-4b-it',
                contents=[img, "Describe this image in detail"]
            )
            return response.text
        except Exception as e:
            print(f"Error generating content: {e}")
            print("Now using OCR as fallback.")
            response = pytesseract.image_to_string(img)
            return response.strip()



    tools = [explain_text, generate_quiz, generate_feedback, extract_text_from_image]

    llm_with_tools = llm.bind_tools(tools)


    checkpointer = InMemorySaver()
    # System message
    sys_msg = SystemMessage(content="your are an Ai tutor with year of experience, given a user_input(question/problem), you decide to help the student by answering his query , explaining the problem , generating quizes around the problem topic, and to do so you utilize the tools you have"
    )
    # Node
    def assistant(state: MessagesState):
        return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])]}

    # Graph
    builder = StateGraph(MessagesState)

    # Define nodes: these do the work
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))

    # Define edges: these determine how the control flow moves
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges(
        "assistant",
        tools_condition,
    )
    builder.add_edge("tools", "assistant")
    react_graph = builder.compile(checkpointer=checkpointer)

    # #------------------frontend logic-----------------

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
    