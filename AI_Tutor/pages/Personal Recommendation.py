#Personal Recommendation

import streamlit as st
import pandas as pd
from recommender import load_progress, baseline_recommend, cf_recommend, log_user_feedback

def render_recommendations_panel(user_id: str):
    """
    Renders the recommendation panel in a Streamlit app.
    """
    st.header("🚀 Your Personalized Learning Path")
    st.write("Here are some topics we think you should focus on next. Choose a method to see different recommendations.")

    # Load data once
    all_progress_df = load_progress()

    # Scorer selection
    scorer_options = ["Baseline", "Collaborative Filtering (Hybrid)" , "Community Recommendation"]
    selected_scorer = st.radio(
        "Recommendation Method:",
        options=scorer_options,
        horizontal=True,
        label_visibility="collapsed"
    )

    # Generate recommendations based on selection
    baseline_recs = baseline_recommend(user_id, all_progress_df, top_k=10)
    
    if selected_scorer == "Baseline":
        recs_df = baseline_recs.head(5)
        recs_df = recs_df.rename(columns={"score": "final_score"})
    else: # Hybrid
        hybrid_recs = cf_recommend(user_id, all_progress_df, baseline_recs, top_k=5)
        recs_df = hybrid_recs.rename(columns={"hybrid_score": "final_score"})


    if recs_df.empty:
        st.info("No recommendations available yet. Complete some topics to get started!")
        return

    # Display recommendations
    for _, row in recs_df.iterrows():
        st.markdown("---")
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader(f"{row['topic']}")
            st.caption(f"Course: **{row['course']}**")
            
            # Progress bar for mastery
            st.progress(int(row['mastery']), text=f"Current Mastery: {row['mastery']}%")
            st.markdown(f"🎯 **Target:** Reach **{row['target_mastery']}%** mastery.")
            st.markdown(f"💬 **Reason:** *{row['reason']}*")

        with col2:
            st.button("Start Practice", key=f"start_{row['topic']}", use_container_width=True)
            if st.button("Snooze", key=f"snooze_{row['topic']}", use_container_width=True):
                log_user_feedback(user_id, row['topic'], 'snooze')
                st.toast(f"Snoozed '{row['topic']}'. We'll show it again later.", icon="😴")
                st.rerun()


        # Explainability Expander
        with st.expander("Why was this recommended? (See score details)"):
            score_components = row.get('score_components', {})
            if score_components:
                st.markdown(f"- **Low Mastery Priority:** `{score_components['mastery_score']:.2f}` (1 is lowest mastery)")
                st.markdown(f"- **Course Focus:** `{score_components['course_mastery_score']:.2f}` (1 means less focus on this course)")
                st.markdown(f"- **Prerequisites Met:** `{'✅ Yes' if score_components['prereq_factor'] > 0 else '❌ No'}`")
                st.markdown(f"- **Difficulty Factor:** `{score_components['difficulty_score']:.2f}` (1 is most difficult)")
            
            if 'cf_score' in row:
                st.markdown(f"- **Similarity Score (CF):** `{row['cf_score']:.2f}` (Based on similar users)")
                st.markdown(f"- **Baseline Score (Normalized):** `{row['normalized_baseline_score']:.2f}`")
                st.markdown(f"---")
                st.markdown(f"**Hybrid Score:** `{row['final_score']:.2f}`")

render_recommendations_panel('student456')