from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage,AIMessage
from langgraph.graph import MessagesState
from langchain_core.messages import SystemMessage
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import pytesseract
import os
from PIL import Image
from google import genai

from dotenv import load_dotenv
load_dotenv()
GEMINI_API_KEY = os.getenv('GOOGLE_API_KEY')
# if 'GOOGLE_API_KEY' in st.secrets:
#         GEMINI_API_KEY = st.secrets['GOOGLE_API_KEY']
# GEMINI_API_KEY = ""

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

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

conn = sqlite3.connect(database = 'chat_history.db', check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

with open('agent_prompt.txt','r')as f:
    content = f.read()
sys_msg = SystemMessage(content=content)

class State(MessagesState):
    image_path: str = "No image uploaded"

# Node
def assistant(state: State):
   sys_msg.content = sys_msg.content.format(image_path=state['image_path'])
   return {"messages": [llm_with_tools.invoke([sys_msg] + state["messages"])] , "image_path": state["image_path"]}

# Graph
builder = StateGraph(State)

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


# CONFIG = {'configurable': {'thread_id': "thread-1"}}
# response = react_graph.invoke({"messages": ['What is my name']}, config=CONFIG)

# print(react_graph.get_state(config=CONFIG).values['messages'])
def retrieve_all_threads():
    """Retrieve all threads from the database."""
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config['configurable']['thread_id'])
    return list(all_threads)

# all_threads = retrieve_all_threads()
# print("All threads:", all_threads)
# for thread in all_threads:
#     response = react_graph.get_state(config={'configurable': {'thread_id': thread}})
#     print(f"Thread {thread} messages:")
#     for message in response.values['messages']:
#         if isinstance(message, HumanMessage):
#             print(f"User: {message.content}")
#         elif isinstance(message, AIMessage):
#             print(f"AI: {message.content}")
#         else:
#             print(f"tool: {message.content}")