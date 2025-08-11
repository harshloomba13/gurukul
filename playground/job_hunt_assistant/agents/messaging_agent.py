# /agents/messaging_agent.py

from crewai import Agent, Task
from utils.tracking import log_application
from datetime import datetime
from utils.config import GEMINI_API_KEY
import logging
from crewai.llm import LLM

logger = logging.getLogger(__name__)

def get_messaging_agent():
    try:
        # Create a custom LLM configuration
        llm = LLM(model="gemini/gemini-1.5-flash", api_key=GEMINI_API_KEY)
        
        # Define the agent responsible for generating outreach messages
        agent = Agent(
            role="Outreach Messaging Specialist",
            goal="Write engaging and personalized outreach messages for job applications",
            backstory=(
                "You are an expert in professional communication and job applications. "
                "You help job seekers create concise and warm messages to recruiters or hiring managers, "
                "expressing genuine interest in the role and aligning their profile with the job."
            ),
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        logger.info("✅ Messaging Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Messaging Agent: {e}")
        raise

# Define the task that uses the agent
from crewai import Task

def create_messaging_task(agent, job_title, agency, resume_summary, contact_name=None):
    try:
        # Truncate inputs if they're too long to avoid token limits
        max_length = 2000  # Adjust based on your needs
        if len(resume_summary) > max_length:
            resume_summary = resume_summary[:max_length] + "..."
            logger.info(f"Resume summary truncated to {max_length} characters")
        
        prompt = f"""
Write a short and professional outreach message for a job application.

Job Title: {job_title}
Agency/Company: {agency}
Resume Summary: {resume_summary}
{"Contact Name: " + contact_name if contact_name else ""}

The message should:
- Be warm and genuine
- Reference the job and agency
- Briefly highlight qualifications
- Ask for an opportunity to discuss further
- Be less than 150 words
"""

        task = Task(
            description=prompt.strip(),
            expected_output="A short, professional, and personalized outreach message under 150 words.",
            agent=agent,
            model="gemini/gemini-1.5-flash",
            api_key=GEMINI_API_KEY
        )
        logger.info("✅ Messaging task created successfully")
        return task
    except Exception as e:
        logger.error(f"❌ Failed to create Messaging task: {e}")
        raise

