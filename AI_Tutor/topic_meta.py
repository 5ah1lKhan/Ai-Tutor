# topic_meta.py

from typing import Dict, List

# 1. Known courses and topics
COURSES: List[str] = [
    "Computer Science", "Mathematics", "Physics", "Chemistry", "Biology",
    "Artificial Intelligence", "Machine Learning", "Data Science"
]

TOPICS: Dict[str, List[str]] = {
    "Computer Science": ["Python Basics", "Data Structures", "Algorithms", "Web Development"],
    "Mathematics": ["Calculus", "Linear Algebra", "Statistics", "Discrete Mathematics"],
    "Physics": ["Classical Mechanics", "Electromagnetism", "Quantum Physics", "Thermodynamics"],
    "Chemistry": ["Organic Chemistry", "Inorganic Chemistry", "Physical Chemistry", "Analytical Chemistry"],
    "Biology": ["Cell Biology", "Genetics", "Evolutionary Biology", "Ecology"],
    "Artificial Intelligence": ["RAG", "Generative AI", "Natural Language Processing"],
    "Machine Learning": ["Transformers", "Supervised Learning", "Unsupervised Learning", "Reinforcement Learning", "Neural Networks"],
    "Data Science": ["Data Analysis with Python", "Data Visualization", "Big Data Technologies"]
}

# 2. Topic metadata: difficulty, prerequisites, and estimated time
TOPIC_META: Dict[str, Dict] = {
    # Computer Science
    "Python Basics": {"difficulty": 1, "prerequisites": [], "estimated_minutes": 90},
    "Data Structures": {"difficulty": 3, "prerequisites": ["Python Basics"], "estimated_minutes": 180},
    "Algorithms": {"difficulty": 4, "prerequisites": ["Data Structures"], "estimated_minutes": 240},
    "Web Development": {"difficulty": 3, "prerequisites": ["Python Basics"], "estimated_minutes": 200},
    # Mathematics
    "Calculus": {"difficulty": 4, "prerequisites": [], "estimated_minutes": 220},
    "Linear Algebra": {"difficulty": 3, "prerequisites": [], "estimated_minutes": 180},
    "Statistics": {"difficulty": 2, "prerequisites": [], "estimated_minutes": 150},
    "Discrete Mathematics": {"difficulty": 3, "prerequisites": [], "estimated_minutes": 160},
    # Physics
    "Classical Mechanics": {"difficulty": 4, "prerequisites": ["Calculus"], "estimated_minutes": 240},
    "Electromagnetism": {"difficulty": 5, "prerequisites": ["Calculus"], "estimated_minutes": 260},
    "Quantum Physics": {"difficulty": 5, "prerequisites": ["Classical Mechanics", "Linear Algebra"], "estimated_minutes": 300},
    "Thermodynamics": {"difficulty": 3, "prerequisites": ["Calculus"], "estimated_minutes": 180},
    # AI/ML/DS
    "RAG": {"difficulty": 4, "prerequisites": ["Natural Language Processing"], "estimated_minutes": 150},
    "Generative AI": {"difficulty": 4, "prerequisites": ["Neural Networks"], "estimated_minutes": 180},
    "Natural Language Processing": {"difficulty": 3, "prerequisites": ["Machine Learning Foundations"], "estimated_minutes": 200},
    "Transformers": {"difficulty": 5, "prerequisites": ["Neural Networks"], "estimated_minutes": 240},
    "Supervised Learning": {"difficulty": 2, "prerequisites": ["Python Basics", "Statistics"], "estimated_minutes": 160},
    "Unsupervised Learning": {"difficulty": 3, "prerequisites": ["Python Basics", "Statistics"], "estimated_minutes": 160},
    "Reinforcement Learning": {"difficulty": 5, "prerequisites": ["Supervised Learning"], "estimated_minutes": 220},
    "Neural Networks": {"difficulty": 4, "prerequisites": ["Supervised Learning", "Linear Algebra"], "estimated_minutes": 200},
    "Data Analysis with Python": {"difficulty": 2, "prerequisites": ["Python Basics"], "estimated_minutes": 180},
    "Data Visualization": {"difficulty": 2, "prerequisites": ["Data Analysis with Python"], "estimated_minutes": 120},
    "Big Data Technologies": {"difficulty": 4, "prerequisites": ["Data Structures"], "estimated_minutes": 200},
}

# Add default metadata for topics not explicitly defined
for course, topics in TOPICS.items():
    for topic in topics:
        if topic not in TOPIC_META:
            TOPIC_META[topic] = {"difficulty": 3, "prerequisites": [], "estimated_minutes": 120}

