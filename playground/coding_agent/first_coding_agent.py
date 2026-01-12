# Warning control
import warnings
warnings.filterwarnings('ignore')

from demos import coding_agent_demo_ui

#coding_agent_demo_ui()

from openai import OpenAI
from llm import llm

client = OpenAI()

messages = [{"role": "user", "content": "hi!"}]
system = "You speak like a linkedin influencer"

response = llm(client, messages, system)

print(response.output_text)