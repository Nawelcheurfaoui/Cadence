# Cadence

**Keep sight of where you're going.**

## About

Cadence is an AI-powered goal trajectory app that helps users assess whether their goals are achievable within a chosen timeline. It combines workload evidence, deadlines, current progress, and available capacity to identify gaps between a user's current pace and the pace required to reach their target.

The first implementation focuses on language learning and CEFR levels.

## Tech stack

- Python
- Streamlit
- Groq — AI reasoning and interpretation
- Tavily — web research
- python-dotenv — local environment configuration

## Run locally

1. Clone or download this repository.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project folder with your API keys:

   ```text
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   ```

4. Start the app:

   ```bash
   streamlit run learnlanguage.py
   ```

Never commit your `.env` file or share your API keys publicly.

## Project status

Cadence is an early-stage prototype. Future development will focus on improving workload evidence, trajectory assessments, and support for additional goal types.
