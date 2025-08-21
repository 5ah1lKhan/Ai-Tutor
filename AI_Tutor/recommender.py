# recommender.py

import pandas as pd
import numpy as np
import sqlite3
from typing import Dict, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity

from topic_meta import TOPICS, TOPIC_META

# --- Configuration Block ---
# Easily tunable weights for the baseline recommender's scoring function.
BASELINE_WEIGHTS = {
    "mastery": -1.5,          # Higher weight to prioritize topics with lower mastery.
    "course_mastery": -0.5,   # Slightly penalize topics in well-mastered courses.
    "prereq_unmet": 2.0,      # Strongly boost topics where prerequisites are newly met.
    "difficulty": 0.1,        # Slightly favor more difficult topics as a challenge.
}

# --- Database and Data Loading ---

def load_progress(db_path: str = "progress_data.db") -> pd.DataFrame:
    """
    Loads user progress data from the SQLite database.
    Handles cold starts by returning an empty DataFrame if the table is missing.
    
    Time Complexity: O(N) where N is the number of rows in the progress table.
    Memory Complexity: O(N) to store the DataFrame.
    """
    try:
        with sqlite3.connect(db_path) as conn:
            df = pd.read_sql_query("SELECT * FROM student_progress", conn)
        return df
    except pd.errors.DatabaseError:
        # Handle case where the database or table doesn't exist yet
        return pd.DataFrame(columns=['user_id', 'course', 'topic', 'mastery_level'])

# --- Helper Functions ---

def compute_course_aggregates(progress_df: pd.DataFrame) -> Dict[str, float]:
    """
    Computes the average mastery level for each course for a given user.
    
    Time Complexity: O(U) where U is the number of progress entries for the user.
    """
    if progress_df.empty:
        return {}
    return progress_df.groupby('course')['mastery_level'].mean().to_dict()

def compute_prereq_factor(topic: str, user_mastery: Dict[str, int], mastery_threshold: int = 60) -> Tuple[float, List[str]]:
    """
    Calculates a prerequisite factor. Returns 1.0 if all prerequisites are met,
    0.0 otherwise. Also returns the list of unmet prerequisites.
    
    Time Complexity: O(P) where P is the number of prerequisites for a topic.
    """
    meta = TOPIC_META.get(topic, {})
    prereqs = meta.get("prerequisites", [])
    if not prereqs:
        return 1.0, []

    unmet_prereqs = [
        p for p in prereqs if user_mastery.get(p, 0) < mastery_threshold
    ]
    
    return 0.0 if unmet_prereqs else 1.0, unmet_prereqs

def suggest_target(mastery: int) -> int:
    """Suggests a reasonable next target mastery level."""
    if mastery < 40:
        return 70
    if mastery < 75:
        return 85
    return 95

def generate_reason(score_components: Dict) -> str:
    """Generates a human-readable reason for a recommendation."""
    reasons = []
    if score_components['mastery_score'] > 0.5: # Inverted score
        reasons.append(f"Low mastery ({score_components['current_mastery']})")
    if score_components['prereq_factor'] > 0:
        reasons.append("Prerequisites met")
    elif score_components['unmet_prereqs']:
        reasons.append(f"Missing prereqs: {', '.join(score_components['unmet_prereqs'])}")
        
    if score_components['difficulty_score'] > 0.3:
        reasons.append("Challenging topic")

    return "; ".join(reasons) if reasons else "A good next step."

# --- Core Recommender Functions ---

def baseline_recommend(user_id: str, all_progress_df: pd.DataFrame, top_k: int = 5) -> pd.DataFrame:
    """
    A rule-based baseline recommender.
    
    Computes a score for each topic based on a weighted combination of features.
    
    Time Complexity: O(T) where T is the total number of topics.
    Memory Complexity: O(T) to store recommendation candidates.
    """
    user_progress = all_progress_df[all_progress_df['user_id'] == user_id]
    user_mastery = user_progress.set_index('topic')['mastery_level'].to_dict()
    course_mastery_agg = compute_course_aggregates(user_progress)
    
    recommendations = []

    all_topics = [topic for course_topics in TOPICS.values() for topic in course_topics]
    # print(all_topics)
    for topic in all_topics:
        # Skip topics the user has already mastered
        current_mastery = user_mastery.get(topic, 0)
        if current_mastery >= 95:
            continue

        course = [c for c, t_list in TOPICS.items() if topic in t_list][0]
        meta = TOPIC_META.get(topic, {})
        
        # 1. Mastery Score (normalized and inverted: 0 is mastered, 1 is unstarted)
        mastery_score = 1 - (current_mastery / 100.0)
        
        # 2. Course Mastery Score (normalized and inverted)
        course_mastery = course_mastery_agg.get(course, 0)
        course_mastery_score = 1 - (course_mastery / 100.0)
        
        # 3. Prerequisite Factor (binary: 1 if met, 0 if not)
        prereq_met_factor, unmet_prereqs = compute_prereq_factor(topic, user_mastery)
        # We want to recommend topics whose prerequisites are met, so a factor of 0 should be penalized.
        # A simple way is to give a large negative score if unmet.
        prereq_unmet_penalty = (prereq_met_factor-1.0)*1000
        # 4. Difficulty Score (normalized)
        difficulty = meta.get("difficulty", 3)
        difficulty_score = difficulty / 5.0

        # Combine scores with weights
        score = (
            BASELINE_WEIGHTS["mastery"] * mastery_score +
            BASELINE_WEIGHTS["course_mastery"] * course_mastery_score +
            BASELINE_WEIGHTS["difficulty"] * difficulty_score +
            prereq_unmet_penalty # Apply penalty directly
        )
        
        # Store score components for explainability
        score_components = {
            'mastery_score': mastery_score,
            'course_mastery_score': course_mastery_score,
            'prereq_factor': prereq_met_factor,
            'difficulty_score': difficulty_score,
            'current_mastery': current_mastery,
            'unmet_prereqs': unmet_prereqs,
        }
        
        # if prereq_unmet_penalty == 0: # Only consider topics with met prerequisites
        if True:
            recommendations.append({
                "course": course,
                "topic": topic,
                "mastery": current_mastery,
                "score": score,
                "target_mastery": suggest_target(current_mastery),
                "reason": generate_reason(score_components),
                "score_components": score_components
            })

    if not recommendations:
        return pd.DataFrame()
    print(recommendations)
    recs_df = pd.DataFrame(recommendations)
    result = recs_df.sort_values(by="score", ascending=False)
    print(result)
    return result.head(top_k)


def cf_recommend(user_id: str, all_progress_df: pd.DataFrame, baseline_recs: pd.DataFrame, top_k: int = 5, cf_weight: float = 0.3) -> pd.DataFrame:
    """
    Item-based collaborative filtering recommender.
    
    Time Complexity: O(U*T + T^2) where U is users, T is topics. Dominated by similarity matrix.
    Memory Complexity: O(U*T) for the utility matrix.
    """
    if all_progress_df.empty or user_id not in all_progress_df['user_id'].unique():
        return pd.DataFrame() # Cold start for user

    # Create user-topic mastery matrix
    utility_matrix = all_progress_df.pivot_table(
        index='user_id', columns='topic', values='mastery_level'
    ).fillna(0)
    
    # Compute item-item similarity (cosine similarity between topic vectors)
    item_similarity = cosine_similarity(utility_matrix.T)
    item_sim_df = pd.DataFrame(item_similarity, index=utility_matrix.columns, columns=utility_matrix.columns)
    
    # Get topics the user has interacted with
    user_vector = utility_matrix.loc[user_id]
    interacted_topics = user_vector[user_vector > 0].index
    
    # Predict scores for un-interacted topics
    predictions = {}
    all_topics = utility_matrix.columns
    
    for topic in all_topics:
        if topic not in interacted_topics:
            # Weighted sum of similarities of topics the user *has* rated
            weighted_sum = 0
            sim_sum = 0
            for interacted_topic in interacted_topics:
                sim = item_sim_df.loc[topic, interacted_topic]
                if sim > 0:
                    weighted_sum += sim * user_vector[interacted_topic]
                    sim_sum += sim
            
            if sim_sum > 0:
                predictions[topic] = weighted_sum / sim_sum

    if not predictions:
        return baseline_recs # Fallback to baseline if no CF signal

    cf_scores = pd.Series(predictions).sort_values(ascending=False)
    
    # Normalize CF scores to be on a similar scale to baseline scores (0-1)
    if not cf_scores.empty:
        cf_scores = (cf_scores - cf_scores.min()) / (cf_scores.max() - cf_scores.min() + 1e-9)

    # Hybrid Scoring
    hybrid_recs = baseline_recs.copy()
    hybrid_recs['cf_score'] = hybrid_recs['topic'].map(cf_scores).fillna(0)
    
    # Normalize baseline score for blending
    bs_scores = hybrid_recs['score']
    hybrid_recs['normalized_baseline_score'] = (bs_scores - bs_scores.min()) / (bs_scores.max() - bs_scores.min() + 1e-9)
    
    hybrid_recs['hybrid_score'] = (1 - cf_weight) * hybrid_recs['normalized_baseline_score'] + cf_weight * hybrid_recs['cf_score']

    return hybrid_recs.sort_values(by='hybrid_score', ascending=False)

# --- Optional: User Feedback Logging ---

def log_user_feedback(user_id: str, topic: str, feedback: str, db_path: str = "feedback.db"):
    """Logs user feedback (e.g., 'snooze', 'start') to a database."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id TEXT,
                topic TEXT,
                feedback TEXT
            )
        """)
        cursor.execute(
            "INSERT INTO feedback (user_id, topic, feedback) VALUES (?, ?, ?)",
            (user_id, topic, feedback)
        )
        conn.commit()

