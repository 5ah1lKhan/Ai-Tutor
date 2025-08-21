#Progress Dashboard
import streamlit as st
import pandas as pd
import sqlite3
from typing import Optional, List, Dict
from progress_tracker import run_progress_tracker

# def run():
#     print("Running progress tracker...")
#     return "run function is called"
st.title("Progress Dashboard")
if 'selected_user' not in st.session_state:
    st.session_state['selected_user'] = 'All'  # Default to show all users
    st.rerun()
elif st.session_state['selected_user'] == 'All':
    st.subheader("Select a user to view their progress")
else:
    if st.button("Run Progress Tracker"):
        st.write(run_progress_tracker(st.session_state['selected_user']))
    # if st.button("Run Progress Tracker"):
    #     st.write(run())
# --- User-provided courses & topics (kept here so UI always shows expected structure) ---
COURSES: List[str] = [
    "Computer Science",
    "Mathematics",
    "Physics",
    "Chemistry",
    "Biology",
    "Artificial Intelligence",
    "Machine Learning",
    "Data Science",
]

TOPICS: Dict[str, List[str]] = {
    "Computer Science": ["Python Basics", "Data Structures", "Algorithms", "Web Development"],
    "Mathematics": ["Calculus", "Linear Algebra", "Statistics", "Discrete Mathematics"],
    "Physics": ["Classical Mechanics", "Electromagnetism", "Quantum Physics", "Thermodynamics"],
    "Chemistry": ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry"],
    "Biology": ["Cell Biology", "Genetics", "Evolutionary Biology", "Ecology"],
    "Artificial Intelligence": ["RAG", "Generative AI", "Natural Language Processing"],
    "Machine Learning": ["Transformers", "Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Neural Networks"],
    "Data Science": ["Data Analysis with Python", "Data Visualization", "Big Data Technologies"],
}

DB_PATH = "progress_data.db"  # change if your DB path is different
TABLE_NAME = "student_progress"      # expected table name


# ----------------- Database helpers -----------------
def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn


def load_progress_data(db_path: str = DB_PATH, user_id: Optional[str] = None) -> pd.DataFrame:
    """Load progress table from sqlite into a pandas DataFrame.
    Expected schema: user_id TEXT, course TEXT, topic TEXT, mastery_level INTEGER
    """
    conn = get_connection(db_path)
    try:
        if user_id and user_id != "All":
            df = pd.read_sql_query(
                "SELECT user_id, course, topic, mastery_level FROM {} WHERE user_id = ?".format(TABLE_NAME),
                conn,
                params=(user_id,),
            )
        else:
            df = pd.read_sql_query(
                "SELECT user_id, course, topic, mastery_level FROM {}".format(TABLE_NAME), conn
            )
    except Exception as e:
        # If table doesn't exist or query fails, return empty df with expected columns
        st.error(f"Error reading DB: {e}")
        df = pd.DataFrame(columns=["user_id", "course", "topic", "mastery_level"])
    finally:
        conn.close()

    # Ensure types
    if not df.empty:
        df["mastery_level"] = pd.to_numeric(df["mastery_level"], errors="coerce").fillna(0).astype(int)
        df["course"] = df["course"].astype(str)
        df["topic"] = df["topic"].astype(str)
        df["user_id"] = df["user_id"].astype(str)

    return df


# ----------------- UI helpers -----------------

def compute_course_aggregate(df: pd.DataFrame, course: str) -> int:
    """Return average mastery_level for a course (0-100). If no data, return 0."""
    if df.empty:
        return 0
    sub = df[df["course"] == course]
    if sub.empty:
        return 0
    return int(round(sub["mastery_level"].mean()))


def compute_topic_aggregate(df: pd.DataFrame, course: str, topic: str) -> int:
    if df.empty:
        return 0
    sub = df[(df["course"] == course) & (df["topic"] == topic)]
    if sub.empty:
        return 0
    return int(round(sub["mastery_level"].mean()))


# ----------------- Streamlit Page -----------------

def progress_tracker_page(db_path: str = DB_PATH):
    # st.set_page_config(page_title="Progress Tracker", layout="wide")
    # st.title("📊 Progress Tracker")

    # Load all data (no user filter) to populate user select and overall stats
    all_df = load_progress_data(db_path=db_path, user_id=None)

    # User selector (optional)
    user_ids = ["All"] + sorted(all_df["user_id"].unique().tolist()) if not all_df.empty else ["All"]
    selected_user = st.selectbox("Filter by user:", user_ids)
    if st.session_state.get('selected_user') != selected_user:
        st.session_state['selected_user'] = selected_user  # Store in session state
        st.rerun()
    # Reload filtered data if user selected
    df = load_progress_data(db_path=db_path, user_id=selected_user if selected_user != "All" else None)

    # Top-level course overview
    st.subheader("Course overview")

    cols = st.columns(4)
    for i, course in enumerate(COURSES):
        agg = compute_course_aggregate(df, course)
        with cols[i % 4]:
            st.metric(label=course, value=f"{agg}%")
            st.progress(min(max(agg / 100.0, 0.0), 1.0))
            # Click to open
            if st.button("Open", key=f"open_{course}"):
                st.session_state["selected_course"] = course

    # Also provide a manual chooser for keyboard/mouse users
    st.markdown("---")
    course_choice = st.selectbox("Or choose a course to inspect:", ["__None__"] + COURSES)

    # Persist selection either from button clicks or selectbox
    selected_course = st.session_state.get("selected_course", None)
    if course_choice != "__None__":
        selected_course = course_choice
        st.session_state["selected_course"] = selected_course

    # If a course is selected, show topics inside it
    if selected_course:
        st.subheader(f"{selected_course} — Topic mastery")
        topics_list = TOPICS.get(selected_course, [])

        # Build topic table for display
        rows = []
        for topic in topics_list:
            val = compute_topic_aggregate(df, selected_course, topic)
            rows.append({"topic": topic, "mastery_level": val})

        topics_df = pd.DataFrame(rows)

        # Show table and progress bars side-by-side
        if topics_df.empty:
            st.info("No topic data available for this course yet.")
        else:
            for _, r in topics_df.iterrows():
                st.write(f"**{r['topic']}** — {r['mastery_level']}%")
                st.progress(min(max(int(r['mastery_level']) / 100.0, 0.0), 1.0))

        st.markdown("---")
        st.write("Detailed data from DB (if available):")
        st.dataframe(df[df["course"] == selected_course][["user_id", "topic", "mastery_level"]].reset_index(drop=True))

        # Download filtered data
        csv = topics_df.to_csv(index=False)
        st.download_button("Download topic summary (CSV)", csv, file_name=f"{selected_course}_topics.csv")

    else:
        st.info("Click 'Open' on any course card or pick a course from the dropdown to see topic-level mastery.")


# Allow this file to be run directly for quick testing
if __name__ == "__main__":
    progress_tracker_page()
