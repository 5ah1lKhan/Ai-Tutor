import sqlite3
import os
import pickle
from typing import TypedDict, List
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage
from graph_database import react_graph , retrieve_all_threads
import json

# --- Database Configuration ---
PROGRESS_DB_FILE = "progress_data.db"
# This should point to the database file used by SqliteSaver in your main app
CHAT_HISTORY_DB_FILE = "chat_history.db" 
##courses
courses = ["Computer Science", "Mathematics", "Physics", "Chemistry", "Biology", "Artificial Intelligence", "Machine Learning", "Data Science"]
topics = {
    "Computer Science": ["Python Basics", "Data Structures", "Algorithms", "Web Development"],
    "Mathematics": ["Calculus", "Linear Algebra", "Statistics", "Discrete Mathematics"],
    "Physics": ["Classical Mechanics", "Electromagnetism", "Quantum Physics", "Thermodynamics"],
    "Chemistry": ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry"],
    "Biology": ["Cell Biology", "Genetics", "Evolutionary Biology", "Ecology"],
    "Artificial Intelligence": ["RAG", "Generative AI", "Natural Language Processing"],
    "Machine Learning": ["Transformers", "Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Neural Networks"],
    "Data Science": ["Data Analysis with Python", "Data Visualization", "Big Data Technologies"]
}
# --- Database Setup ---
def get_progress_db_connection():
    """Establishes a connection to the progress tracking SQLite database."""
    conn = sqlite3.connect(PROGRESS_DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def setup_database():
    """Creates the student_progress table if it doesn't exist."""
    conn = get_progress_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_progress (
            user_id TEXT NOT NULL,
            course TEXT NOT NULL,
            topic TEXT NOT NULL,
            mastery_level REAL DEFAULT 0.0,
            PRIMARY KEY (user_id, course, topic)
        )
    """)
    conn.commit()
    conn.close()
    print("Progress database setup complete.")

# Initialize the database when the module is loaded
setup_database()

# --- LangChain Tools for Progress Tracking ---

# Initialize the LLM for the tools that need it
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

def load_conversation(thread_id):
        return react_graph.get_state(config = {'configurable': {'thread_id': thread_id}}).values['messages']
 
@tool
def get_conversation_history(thread_id: str) -> str:
    """
    Fetches and formats the conversation history for a given thread_id
    from the chat history database (checkpoints).
    """
    print(f"Fetching conversation history for thread_id: {thread_id}...")
    try:
        all_threads = retrieve_all_threads()
        if thread_id not in all_threads:
            return f"No conversation history found for thread_id: {thread_id}"
        else:
            messages = load_conversation(thread_id)
            if not messages:
                return f"No messages found for thread_id: {thread_id}"
            
            formatted_messages = []
            for message in messages:
                if isinstance(message, HumanMessage):
                    formatted_messages.append({'role': 'user', 'content': message.content})
                elif isinstance(message, AIMessage):
                    formatted_messages.append({'role': 'assistant', 'content': message.content})
            
            return formatted_messages
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return f"Error: {e}"


@tool
def identify_course_topic(conversation_history: list[dict]) -> str:
    """
    Uses an LLM to identify the main educational course from a conversation history.
    """
    print("Identifying course and topic from conversation...")
    prompt = f"""
        Analyze the following conversation between a tutor and a student.

        From the provided courses list:
        {courses}

        and the topics dictionary (topics grouped under each course):
        {topics}

        Identify:
        1. The primary course being discussed.
        2. The specific topic within that course.

        ⚠️ Rules:
        - The course *must* be one from the courses list.
        - The topic *must* be one from the topics dictionary for that course.
        - Do not invent new courses or topics.
        - Return ONLY a valid JSON object, nothing else.

        Conversation:
        ---
        {conversation_history}
        ---

        Your response should be in json format:

        {{
        "course": "<Course Name>",
        "topic": "<Topic Name>"
        }}

        NOTE: if the conversation is general conversation and not about a course and topic , then return {{"course": "General", "topic": "General"}}.
        """

    response = llm.invoke(prompt).content.strip()
    # topic = response.content.strip()
    if response.startswith('```json'):
        response = response[7:-3].strip()  # Remove the ```json and ``` markers
    print(f"Identified Topic: {response}")
    return response

@tool
def evaluate_mastery(conversation_history: list[dict], topic: str, course: str , previous_mastery_level: float) -> str:
    """
    Uses an LLM to evaluate a student's mastery of a topic based on their
    interactions and their previous mastery level. Returns a float between 0.0 and 100.0.
    """


    print(f"Evaluating mastery for course: {course} aand topic '{topic}' with previous level {previous_mastery_level}...")
    prompt = f"""
    Analyze the conversation history to assess the student's mastery of the topic: '{topic}'.
    The student's previous mastery level was {previous_mastery_level:.2f} (on a scale of 0.0 to 100.0).

    Conversation History:
    ---
    {conversation_history}
    ---

    Based on this conversation and their prior understanding, evaluate the student's NEW mastery level.
    Consider if they have improved, regressed, or stayed the same.
    - 0.0 means no understanding.
    - 100.0 means full mastery.

    Provide only a single floating-point number as your response.
    """
    response = llm.invoke(prompt)
    print("RESPONSE FROM MASTERY EVALUATION:", response.content)
    try:
        mastery_level = float(response.content.strip())
        return str(mastery_level)
    except ValueError:
        print(f"Could not parse mastery level from LLM response: {response.content}")
        return str(previous_mastery_level) # Return previous level on error

@tool
def get_student_progress(user_id: str, course: str, topic: str) -> float:
    """
    Fetches the current mastery_level of a student for a specific topic.
    Returns 0.0 if no record exists.
    """
    print(f"Fetching previous progress for {user_id} on course : {course} and topic: {topic}...")
    conn = get_progress_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT mastery_level FROM student_progress WHERE user_id = ? AND course = ? AND topic = ?",
        (user_id, course, topic)
    )
    row = cursor.fetchone()
    conn.close()
    response = row["mastery_level"] if row else 0.0
    return response

@tool
def update_student_progress(user_id: str, course: str, topic: str, new_mastery_level: float) -> dict:
    """
    Updates or inserts a student's progress for a specific topic.
    """
    print(f"Updating progress for {user_id} on '{topic}' to {new_mastery_level}...")
    new_mastery_level = max(0.0, min(100.0, new_mastery_level))
    conn = get_progress_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO student_progress (user_id, course, topic, mastery_level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, course, topic) DO UPDATE SET
        mastery_level = excluded.mastery_level;
    """, (user_id, course, topic, new_mastery_level))
    conn.commit()
    conn.close()
    return {"status": "success", "topic": topic, "new_mastery_level": new_mastery_level}

# --- LangGraph Agent State and Nodes ---

class ProgressState(TypedDict):
    """Represents the state of our progress tracking agent."""
    user_id: str
    course: str
    # Fields populated by the graph
    conversation_history: list[dict]
    topic: str
    previous_mastery_level: float
    evaluated_mastery: float
    thread_id : str

def fetch_history_node(state: ProgressState):
    """Fetches the conversation history from the database."""
    print("---NODE: FETCH HISTORY---")
    state['conversation_history'] = get_conversation_history.invoke({"thread_id": state['thread_id']})
    return state

def identify_topic_node(state: ProgressState):
    """Identifies the topic from the conversation."""
    print("---NODE: IDENTIFY TOPIC---")
    data = identify_course_topic.invoke({"conversation_history": state['conversation_history']})
    data = json.loads(data)  # Parse the JSON response
    state['topic'] = data.get("topic") 
    state['course'] = data.get("course")
    return state

def get_previous_progress_node(state: ProgressState):
    """Gets the student's previous mastery level for the identified topic."""
    print("---NODE: GET PREVIOUS PROGRESS---")
    state['previous_mastery_level'] = get_student_progress.invoke({
        "user_id": state['user_id'],
        "course": state['course'],
        "topic": state['topic']
    })
    return state

def evaluator_node(state: ProgressState):
    """Evaluates the new mastery level based on all gathered context."""
    print("---NODE: EVALUATE MASTERY---")
    mastery_str = evaluate_mastery.invoke({
        "conversation_history": state['conversation_history'],
        "topic": state['topic'],
        "course": state['course'],
        "previous_mastery_level": state['previous_mastery_level']
    })
    state['evaluated_mastery'] = float(mastery_str)
    return state

def updater_node(state: ProgressState):
    """Updates the progress database with the new mastery level."""
    print("---NODE: UPDATE DATABASE---")
    update_student_progress.invoke({
        "user_id": state['user_id'],
        "course": state['course'],
        "topic": state['topic'],
        "new_mastery_level": state['evaluated_mastery']
    })
    return state

# --- Graph Definition ---
builder = StateGraph(ProgressState)
builder.add_node("fetch_history", fetch_history_node)
builder.add_node("identify_topic", identify_topic_node)
builder.add_node("get_previous_progress", get_previous_progress_node)
builder.add_node("evaluate_mastery", evaluator_node)
builder.add_node("update_database", updater_node)

builder.add_edge(START, "fetch_history")
builder.add_edge("fetch_history", "identify_topic")
builder.add_edge("identify_topic", "get_previous_progress")
builder.add_edge("get_previous_progress", "evaluate_mastery")
builder.add_edge("evaluate_mastery", "update_database")
builder.add_edge("update_database", END)

progress_tracker_graph = builder.compile()

# --- Example Usage ---
# def setup_dummy_chat_history():
#     """Creates a dummy chat history database for testing."""
#     if os.path.exists(CHAT_HISTORY_DB_FILE):
#         return # Don't overwrite if it exists
#     print("Setting up dummy chat history for example...")
#     conn = sqlite3.connect(CHAT_HISTORY_DB_FILE)
#     cursor = conn.cursor()
#     cursor.execute("""
#         CREATE TABLE checkpoints (
#             thread_id TEXT PRIMARY KEY,
#             thread_ts TEXT,
#             parent_ts TEXT,
#             ts TEXT,
#             checkpoint BLOB
#         )
#     """)
    
#     dummy_messages = [
#         HumanMessage(content="What is a variable in Python?"),
#         AIMessage(content="A variable is a container for storing data values."),
#         HumanMessage(content="So like x = 5?"),
#         AIMessage(content="Exactly! 'x' is the variable, and 5 is the value it holds.")
#     ]
    
#     dummy_checkpoint = {
#         "v": 1,
#         "ts": "2024-01-01T00:00:00Z",
#         "channel_values": {"messages": dummy_messages},
#         "channel_versions": {},
#         "versions_seen": {}
#     }
    
#     pickled_checkpoint = pickle.dumps(dummy_checkpoint)
    
#     cursor.execute(
#         "INSERT INTO checkpoints (thread_id, ts, checkpoint) VALUES (?, ?, ?)",
#         ("student456", "2024-01-01T00:00:00Z", pickled_checkpoint)
#     )
#     conn.commit()
#     conn.close()


def run_progress_tracker(user_id: str):
    """
    Runs the progress tracker graph for a given user and thread.
    """
    print("\n--- Running Full Progress Tracker Workflow ---")
    
    # The only inputs needed are the user's ID (thread_id) and the course
    # course = "Computer Science"
    # thread_id = "e0eb2abc-3a3c-41f0-b039-ae732405f548"  # Example thread ID, replace with actual if needed
    file_path='untracked_threads.json'
    with open(file_path, 'r') as f:
        data = json.load(f)
    if not data.get("thread_ids"):
        return "No untracked threads found."
    for thread_id in data["thread_ids"][:]:
        initial_state = {
            "user_id": user_id,
            'thread_id': thread_id,
        }

        print(f"\n1. Invoking graph for user '{user_id}'...")
        final_state = progress_tracker_graph.invoke(initial_state)
        
        print("\n2. Graph execution complete. Final state:")
        print(f"   - Identified Topic: {final_state.get('topic')}")
        print(f"   - Course: {final_state.get('course')}")
        print(f"   - Previous Mastery: {final_state.get('previous_mastery_level')}")
        print(f"   - New Evaluated Mastery: {final_state.get('evaluated_mastery')}")

        print("\n3. Verifying final progress in database...")
        final_progress = get_student_progress.invoke({
            "user_id": user_id, 
            "course": final_state.get('course'), 
            "topic": final_state.get('topic')
        })
        print(f"   - Mastery level in DB: {final_progress}")
        
        print("\n--- Workflow Finished ---")
        data["thread_ids"].remove(thread_id)
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    
    return "Update complete for all threads."

        
        # final_state = progress_tracker_graph.invoke(initial_state)
        # return final_state

if __name__ == "__main__":
    # setup_dummy_chat_history()
    student_id = "student456"
    thread_id = "e0eb2abc-3a3c-41f0-b039-ae732405f548"  # Example thread ID
    run_progress_tracker(student_id, thread_id)