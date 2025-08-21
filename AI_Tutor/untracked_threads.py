import os
import json
import streamlit as st

def save_thread_id(thread_id, file_path='untracked_threads.json'):
    if not os.path.exists(file_path):
        with open(file_path, 'w') as f:
            json.dump({"thread_ids": []}, f, indent=4)

    # Read the existing JSON
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Add thread_id if not already present
    if thread_id not in data["thread_ids"]:
        data["thread_ids"].append(thread_id)

        # Save back to file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
