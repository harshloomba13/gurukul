from crewai import Agent, Task
from utils.config import GEMINI_API_KEY
import logging
from crewai.llm import LLM

logger = logging.getLogger(__name__)

def get_resume_cl_agent():
    try:
        # Create a custom LLM configuration
        llm = LLM(model="gemini/gemini-1.5-flash", api_key=GEMINI_API_KEY)
        
        agent = Agent(
            role="Resume & Cover Letter Writer",
            goal="Customize application materials to match job descriptions",
            backstory="You're an expert in professional writing and tailoring resumes for job applications, especially in government and tech roles.",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
        logger.info("✅ Resume Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"❌ Failed to create Resume Agent: {e}")
        raise

def create_resume_cl_task(agent, job_summary, resume_text):
    try:
        # Truncate inputs if they're too long to avoid token limits
        max_length = 3000  # Adjust based on your needs
        if len(job_summary) > max_length:
            job_summary = job_summary[:max_length] + "..."
            logger.info(f"Job summary truncated to {max_length} characters")
        
        if len(resume_text) > max_length:
            resume_text = resume_text[:max_length] + "..."
            logger.info(f"Resume text truncated to {max_length} characters")
        
        task = Task(
            description=f"""
            Based on the job summary below, tailor the candidate's resume summary and generate a personalized cover letter.
            
            --- Job Summary ---
            {job_summary}
            
            --- Resume Text ---
            {resume_text}
            
            Your output should include:
            1. Updated professional summary for resume
            2. A personalized cover letter suitable for a government job
            """,
            agent=agent,
            expected_output="""
            <<RESUME_SUMMARY>>
            [Your tailored 3-5 sentence resume summary here]

            <<COVER_LETTER>>
            [Your personalized cover letter here]
            """,
            output_file='data/resume_agent_output.txt',  # Fixed path
            model="gemini/gemini-1.5-flash",
            api_key=GEMINI_API_KEY
        )
        logger.info("✅ Resume CL task created successfully")
        return task
    except Exception as e:
        logger.error(f"❌ Failed to create Resume CL task: {e}")
        raise