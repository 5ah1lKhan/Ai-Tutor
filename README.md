# AI Tutor

An interactive AI-powered learning assistant that lets students upload images or submit text, explains concepts, generates quizzes, collects answers, provides feedback, tracks progress, and recommends next topics — all in a Streamlit web app backed by LangGraph workflows and Google Gemini.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the App](#running-the-app)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Image-to-Text Extraction**: Extract text from uploaded images using Google Gemini OCR or Tesseract fallback.
- **Concept Explanation**: Provide step-by-step explanations of extracted or user-provided text.
- **Quiz Generation**: Generate multiple-choice quizzes based on content.
- **Human-in-the-Loop**: Pause for user answers and then generate personalized feedback.
- **Progress Tracking**: Evaluate and store mastery levels for each user and topic.
- **Recommendations**: Suggest next topics based on past performance.
- **Streamlit UI**: Clean web interface with sidebar for API key and image upload.

## Project Structure

```
├── AI_Tutor/
│   ├── agent_prompt.txt       #Prompt for agent 
│   ├── progress_tracker.py    # Mastery evaluation & database update
│   ├── recommender.py         # Topic recommendation logic
│   ├── graph_database.py      # Tool definitions and client factory
│   ├── AiTutor.py             # Alternative entry point / multi-page app
│   ├── topic_meta.py          # Course + Topic structure and details
│   ├── images/                # Sample and uploaded images
│   ├── requirement.txt        # Python dependencies
│   └── Pages                  # Pages for dashboard, recommendation      
└── README.md              # Project documentation
```

## Prerequisites

- Python 3.10 or newer
- `git`, `pip`
- Google Gemini / Google Cloud API Key

## Installation

```bash
# Clone the repository
git clone https://github.com/5ah1lKhan/Ai-Tutor.git
cd Ai-Tutor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirement.txt
```

## Configuration

1. Create a `.streamlit/secrets.toml` file (this file should be git-ignored).
2. Add your API key:
   ```toml
   GOOGLE_API_KEY = "YOUR_GOOGLE_API_KEY"
   GEMINI_API_KEY = "YOUR_GOOGLE_API_KEY"
   ```

Alternatively, you can enter your API key in the Streamlit sidebar when the app launches.

## Running the App

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Streamlit
streamlit run frontend/app.py
```

The app will be available at http://localhost:8501.

## Usage

1. Enter your API key in the sidebar.
2. Upload an image or enter text.
3. The assistant will extract or accept text, explain the concept, and generate a quiz.
4. Answer the quiz questions to receive personalized feedback.
5. Track your progress and receive topic recommendations.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Commit your changes (`git commit -m "Add new feature"`)
4. Push to the branch (`git push origin feature/YourFeature`)
5. Open a Pull Request

Please do **not** commit any secrets or API keys.

## License

This project is licensed under the MIT License.
