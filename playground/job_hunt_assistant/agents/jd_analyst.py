from crewai import Agent, Task
from utils.config import GEMINI_API_KEY
import logging
from crewai.llm import LLM

logger = logging.getLogger(__name__)

def get_jd_analyst_agent():
    try:
        # Create a custom LLM configuration
        llm = LLM(model="gemini/gemini-1.5-flash", api_key=GEMINI_API_KEY)
        
        agent = Agent(
            role="JD Analyst",
            goal="Understand and summarize government job postings",
            backstory="You're an expert in job market analysis with a focus on US federal job listings.",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        logger.info("✅ JD Analyst agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create JD Analyst agent: {e}")
        raise

def create_jd_analysis_task(agent, job_description):
    try:
        # Truncate job description if it's too long to avoid token limits
        max_length = 4000  # Adjust based on your needs
        if len(job_description) > max_length:
            job_description = job_description[:max_length] + "..."
            logger.info(f"Job description truncated to {max_length} characters")
        
        task = Task(
            description=f"""
            Analyze the following USAJobs job posting and extract:
            - A summary of the role
            - Key skills required
            - Any specific qualifications or eligibility
            \n\nJob Description:\n{job_description}
            """,
            expected_output="A structured markdown summary containing sections for Qualifications, Required Skills, and Responsibilities.",
            agent=agent,
            output_file='data/report.md',  # Fixed path
            model="gemini/gemini-1.5-flash",
            api_key=GEMINI_API_KEY
        )
        logger.info("✅ JD Analysis task created successfully")
        return task
    except Exception as e:
        logger.error(f"❌ Failed to create JD Analysis task: {e}")
        raise 