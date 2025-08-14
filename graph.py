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
import streamlit as st
# from dotenv import load_dotenv
# load_dotenv()
# GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
if 'GOOGLE_API_KEY' in st.secrets:
        GEMINI_API_KEY = st.secrets['GOOGLE_API_KEY']
client = genai.Client(api_key=GEMINI_API_KEY)

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
