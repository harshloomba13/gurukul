# gurukul
Functional Requirements Summary
🔧 0. Resume & LinkedIn Optimization (Pre-Prep Stage)
Upload and analyze resume for ATS compliance, formatting, and impact

Provide AI-driven and/or human feedback on resume & LinkedIn profile

Optional 1:1 review with mentor/recruiter

Score and track profile readiness

🛣️ 1. Personalized Roadmap Creation
User defines target role (e.g., SDE, PM) and time frame (e.g., 30 days)

Inputs: role, available prep hours, current skill level

System generates a week-by-week learning plan with milestones

🔗 2. Map Roadmap Items to Resources
Link each roadmap item to:

External learning resources (articles, videos, courses)

Internal expert/mentor from platform panel

Resources can be tagged, rated, or updated

📅 3. Auto-Schedule Sessions Within Timeline
Generate calendar-based plan based on user's availability

Assign tasks and sessions to specific days/hours

Match internal mentor availability for booked 1:1 sessions

Dynamic adjustments for missed or rescheduled tasks

🧪 4. Mock Exams & Interviews
DSA/technical mock tests with scoring, timing, and analytics

Behavioral and technical mock interviews (AI or mentor-led)

Post-mock feedback reports and improvement suggestions

Interview readiness scoring

💬 5. Salary Negotiation Support
1:1 consultation with comp expert or mentor

Offer analyzer tool with market benchmarks

Script generator for negotiation emails/convos

Anonymous peer comparisons and insights

## Quick Prototype App
Run the local Streamlit prototype to explore:
- personalized roadmap creation
- roadmap item to resource mapping
- auto-scheduled prep sessions
- mock interview tracking
- profile readiness scoring
  - uses resume and LinkedIn profile feedback signals such as ATS compliance, formatting, impact, and completeness
  - outputs a readiness score that shows whether the user should keep optimizing, request an optional 1:1 review, or move into prep
  - tracks readiness changes so profile improvements are visible before applications and interviews
- salary negotiation support prompts

Command:
`streamlit run gurukul_quick_app.py`

