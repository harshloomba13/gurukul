from crewai import Crew, Process
from agents.jd_analyst import get_jd_analyst_agent, create_jd_analysis_task
from agents.resume_cl_agent import get_resume_cl_agent, create_resume_cl_task
from agents.messaging_agent import get_messaging_agent, create_messaging_task
from usajobs_api import fetch_usajobs
import logging
import traceback
from utils.config import GEMINI_API_KEY

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_resume(path="data/sample_resume.txt"):
    with open(path, "r") as file:
        return file.read()

def run_pipeline():
    try:
        # Check API key
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            print("Please set GEMINI_API_KEY in your .env file")
            return
        
        logger.info("✅ GEMINI_API_KEY found")
        
        # Step 1: Fetch job post
        logger.info("Fetching job posts...")
        job_posts = fetch_usajobs("business analyst", location="New York")
        if not job_posts:
            logger.error("No job posts found.")
            return

        job_data = job_posts[0]['MatchedObjectDescriptor']
        job_summary = job_data['UserArea']['Details']['JobSummary']
        agency_name = job_data.get('OrganizationName', 'Unknown Agency')
        job_title = job_data.get('PositionTitle', 'Unknown Position')
        
        logger.info(f"Found job: {job_title} at {agency_name}")

        # Step 2: Load resume and bio
        logger.info("Loading resume...")
        resume_text = load_resume()
        user_bio = "I'm a data professional passionate about public service."

        # Step 3: Initialize agents
        logger.info("Initializing agents...")
        jd_agent = get_jd_analyst_agent()
        resume_agent = get_resume_cl_agent()
        message_agent = get_messaging_agent()

        # Step 4: Create tasks
        logger.info("Creating tasks...")
        jd_task = create_jd_analysis_task(jd_agent, job_summary)
        resume_task = create_resume_cl_task(resume_agent, job_summary, resume_text)
        message_task = create_messaging_task(message_agent, job_title, agency_name, user_bio)

        # Step 5: Create and run the crew
        logger.info("Creating crew and running pipeline...")
        crew = Crew(
            agents=[jd_agent, resume_agent, message_agent],
            tasks=[jd_task, resume_task, message_task],
            process=Process.sequential,
            model="gemini/gemini-1.5-flash",
            api_key=GEMINI_API_KEY
        )
        print("crew created")
        result = crew.kickoff()
        print("crew kicked off")
        print("\n=== FINAL OUTPUT ===\n")
        print(result)
        
    except Exception as e:
        print(f"❌ Error in pipeline: {str(e)}")
        print(traceback.format_exc())
        print(f"Error: {str(e)}")
        print("Check the logs above for more details.")

if __name__ == "__main__":
    run_pipeline()