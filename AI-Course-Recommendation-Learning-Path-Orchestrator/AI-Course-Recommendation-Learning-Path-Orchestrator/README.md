# AI Course Recommendation & Learning Path Orchestrator

A college-ready Agentic AI mini-project that creates a personalized course recommendation and learning roadmap.

## What makes it agentic?
The backend follows an orchestration workflow:
1. **Profile Agent** – structures the learner's goal, level, interests and constraints.
2. **Research Agent** – uses Tavily to find current learning resources and course pages.
3. **Recommendation Agent** – uses Groq to select and explain suitable resources.
4. **Roadmap Agent** – converts the recommendations into a prerequisite-aware weekly path.
5. **Validation layer** – normalizes the final JSON and keeps the UI stable if an API returns imperfect data.

## Tech stack
- Frontend: HTML + CSS + Vanilla JavaScript
- Backend: Python + Flask
- LLM: Groq API
- Web research: Tavily API
- Storage in browser: localStorage
- No frontend framework and no database required

## Project structure
```text
AI-Course-Recommendation-Learning-Path-Orchestrator/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── static/
    ├── index.html
    ├── styles.css
    └── app.js
```

## Run on Windows / VS Code
1. Install Python 3.10+.
2. Open this folder in VS Code.
3. Open PowerShell in the project folder.
4. Create a virtual environment:
   `python -m venv .venv`
5. Activate it:
   `.\.venv\Scripts\Activate.ps1`
6. Install packages:
   `pip install -r requirements.txt`
7. Create `.env` by copying `.env.example`.
8. Add your `GROQ_API_KEY` and `TAVILY_API_KEY`.
9. Start:
   `python app.py`
10. Open:
   `http://127.0.0.1:5000`

## API keys
Keep API keys in `.env`. Never put them in `static/app.js` or commit `.env` to GitHub.

Groq's official API supports OpenAI-compatible usage and the Python Groq SDK. Tavily provides a Python SDK for search and web research. The project uses those server-side so browser code never exposes your keys.

## If an API key is missing
The UI still opens. Generate will return a clear configuration message rather than crashing the page.

## Demo flow
Try:
- Goal: `Become a backend developer with Python`
- Level: `Beginner`
- Interests: `Python, APIs, SQL`
- Weekly hours: `8`
- Duration: `8 weeks`

Then click **Build my learning path**.

## Optional Git commands
```powershell
git init
git add .
git commit -m "Initial Agentic AI course recommendation project"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```
