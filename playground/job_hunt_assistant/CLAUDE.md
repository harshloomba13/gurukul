# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Job Hunt Assistant that automates job application workflows using CrewAI agents and the Google Gemini API. The system fetches government job postings from USAJobs API, analyzes job descriptions, tailors resumes, and generates personalized outreach messages.

## Architecture

The project follows a multi-agent architecture using CrewAI:

### Core Components
- **orchestrator.py**: Main pipeline coordinator that manages the agent workflow
- **streamlit_app.py**: Web interface for user interaction
- **usajobs_api.py**: Integration with USAJobs.gov API for job fetching

### Agent System
Located in `agents/` directory:
- **jd_analyst.py**: Analyzes job descriptions and extracts requirements
- **resume_cl_agent.py**: Tailors resumes and generates cover letters  
- **messaging_agent.py**: Creates personalized outreach messages

### Utilities
- **utils/config.py**: Environment configuration and API key management
- **utils/tracking.py**: Application logging and tracking functionality

### Data Flow
1. Job posts are fetched from USAJobs API using search keywords
2. JD Analyst agent analyzes job requirements and outputs to `data/report.md`
3. Resume agent tailors application materials and outputs to `data/resume_agent_output.txt`
4. Messaging agent generates outreach content
5. All agents run sequentially in a CrewAI workflow

## Common Commands

### Run the Application
```bash
# Command line interface
python orchestrator.py

# Web interface  
streamlit run streamlit_app.py
```

### Environment Setup
- Requires `.env` file with `GEMINI_API_KEY` and `USAJOBS_API_KEY`
- Uses Python 3.12+ with virtual environment at `/Users/harshloomba/Documents/gurukul/.venv/`

### Key Dependencies
- crewai: Multi-agent orchestration framework
- streamlit: Web UI framework
- google-generativeai: Gemini API integration
- requests: HTTP client for USAJobs API
- python-dotenv: Environment variable management

## Data Structure

Input data expected in `data/` directory:
- `sample_resume.txt`: Template resume for tailoring
- Output files are automatically generated:
  - `report.md`: Job analysis results
  - `resume_agent_output.txt`: Tailored resume and cover letter
  - `applications_log.csv`: Application tracking data

## Agent Configuration

All agents use `gemini/gemini-1.5-flash` model with sequential processing. Each agent has specific token limits (3000-4000 characters) to manage API costs and response quality.