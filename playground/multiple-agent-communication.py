# Add your utilities or helper functions to this file.

import os
from dotenv import load_dotenv, find_dotenv

# these expect to find a .env file at the directory above the lesson.                                                                                                                     # the format for that file is (without the comment)                                                                                                                                       #API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService                                                                                                                                     
def load_env():
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key

OPENAI_API_KEY = get_openai_api_key()
llm_config = {"model": "gpt-3.5-turbo"}

from autogen import ConversableAgent

def joke_teller():
    agent = ConversableAgent(
        name="chatbot",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    reply = agent.generate_reply(
        messages=[{"content": "Tell me a joke.", "role": "user"}]
    )
    print(reply)

    reply = agent.generate_reply(
        messages=[{"content": "Repeat the joke.", "role": "user"}]
    )
    print(reply)

def standup_comedians():
    cathy = ConversableAgent(
        name="cathy",
        system_message=
        "Your name is Cathy and you are a stand-up comedian.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    joe = ConversableAgent(
        name="joe",
        system_message=
        "Your name is Joe and you are a stand-up comedian. "
        "Start the next joke from the punchline of the previous joke.",
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    chat_result = joe.initiate_chat(
        recipient=cathy, 
        message="I'm Joe. Cathy, let's keep the jokes rolling.",
        max_turns=2,
    )

    import pprint

    pprint.pprint(chat_result.chat_history)
    pprint.pprint(chat_result.cost)
    pprint.pprint(chat_result.summary)

standup_comedians()
