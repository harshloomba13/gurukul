import openai
import re
import httpx
import os
from dotenv import load_dotenv

_ = load_dotenv()
from openai import OpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from IPython.display import Image
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")

client = OpenAI()
prompt = """
You run in a loop of Thought, Action, PAUSE, Observation.
At the end of the loop you output an Answer
Use Thought to describe your thoughts about the question you have been asked.
Use Action to run one of the actions available to you - then return PAUSE.
Observation will be the result of running those actions.

Your available actions are:

calculate:
e.g. calculate: 4 * 7 / 3
Runs a calculation and returns the number - uses Python so be sure to use floating point syntax if necessary

average_dog_weight:
e.g. average_dog_weight: Collie
returns average weight of a dog when given the breed

Example session:

Question: How much does a Bulldog weigh?
Thought: I should look the dogs weight using average_dog_weight
Action: average_dog_weight: Bulldog
PAUSE

You will be called again with this:

Observation: A Bulldog weights 51 lbs

You then output:

Answer: A bulldog weights 51 lbs
""".strip()

class Agent:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        completion = client.chat.completions.create(
                        model="gpt-4o", 
                        temperature=0,
                        messages=self.messages)
        return completion.choices[0].message.content
    
def calculate(what):
    return eval(what)

def average_dog_weight(name):
    if name in "Scottish Terrier": 
        return("Scottish Terriers average 20 lbs")
    elif name in "Border Collie":
        return("a Border Collies average weight is 37 lbs")
    elif name in "Toy Poodle":
        return("a toy poodles average weight is 7 lbs")
    else:
        return("An average dog weights 50 lbs")

known_actions = {
    "calculate": calculate,
    "average_dog_weight": average_dog_weight
}

def query(question, max_turns=5):
    action_re = re.compile('^Action: (\w+): (.*)$')   # python regular expression to selection action
    i = 0
    bot = Agent(prompt)
    next_prompt = question
    while i < max_turns:
        i += 1
        result = bot(next_prompt)
        print(result)
        actions = [
            action_re.match(a) 
            for a in result.split('\n') 
            if action_re.match(a)
        ]
        if actions:
            # There is an action to run
            action, action_input = actions[0].groups()
            if action not in known_actions:
                raise Exception("Unknown action: {}: {}".format(action, action_input))
            print(" -- running {} {}".format(action, action_input))
            observation = known_actions[action](action_input)
            print("Observation:", observation)
            next_prompt = "Observation: {}".format(observation)
        else:
            return

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]

class Agent_with_tools:

    def __init__(self, model, tools, checkpointer, system=""):
        self.system = system
        graph = StateGraph(AgentState)
        graph.add_node("llm", self.call_openai)
        graph.add_node("action", self.take_action)
        graph.add_conditional_edges(
            "llm",
            self.exists_action,
            {True: "action", False: END}
        )
        graph.add_edge("action", "llm")
        graph.set_entry_point("llm")
        self.graph = graph.compile(checkpointer=checkpointer)
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

    def exists_action(self, state: AgentState):
        result = state['messages'][-1]
        return len(result.tool_calls) > 0

    def call_openai(self, state: AgentState):
        messages = state['messages']
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages': [message]}

    def take_action(self, state: AgentState):
        tool_calls = state['messages'][-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            if not t['name'] in self.tools:      # check for bad tool name from LLM
                print("\n ....bad tool name....")
                result = "bad tool name, retry"  # instruct LLM to retry if bad
            else:
                result = self.tools[t['name']].invoke(t['args'])
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}    

def search_tool():
    prompt = """You are a smart research assistant. Use the search engine to look up information. \
    You are allowed to make multiple calls (either together or in sequence). \
    Only look up information when you are sure of what you want. \
    If you need to look up some information before asking a follow up question, you are allowed to do that!
    """
    tool = TavilySearchResults(max_results=4, tavily_api_key=os.getenv("TAVILY_API_KEY")) #increased number of results
    model = ChatOpenAI(model="gpt-3.5-turbo")  #reduce inference cost
    abot = Agent_with_tools(model, [tool], system=prompt)
    #doesnt work with graphviz
    #Image(abot.graph.get_graph().draw_png())

    messages = [HumanMessage(content="What is the weather in sf?")]
    result = abot.graph.invoke({"messages": messages})
    print(result['messages'][-1].content)

def search_tool_advance():
    prompt = """You are a smart research assistant. Use the search engine to look up information. \
    You are allowed to make multiple calls (either together or in sequence). \
    Only look up information when you are sure of what you want. \
    If you need to look up some information before asking a follow up question, you are allowed to do that!
    """
    tool = TavilySearchResults(max_results=4, tavily_api_key=os.getenv("TAVILY_API_KEY")) #increased number of results
    model = ChatOpenAI(model="gpt-3.5-turbo")  #reduce inference cost
    abot = Agent_with_tools(model, [tool], system=prompt, checkpointer=memory)
    #doesnt work with graphviz
    #Image(abot.graph.get_graph().draw_png())

    messages = [HumanMessage(content="What is the weather in sf?")]
    thread = {"configurable": {"thread_id": "1"}}
    for event in abot.graph.stream({"messages": messages}, thread):
        for v in event.values():
            print(v['messages'])
    result = abot.graph.invoke({"messages": messages})
    print(result['messages'][-1].content)
    messages = [HumanMessage(content="What about in la?")]
    thread = {"configurable": {"thread_id": "1"}}
    for event in abot.graph.stream({"messages": messages}, thread):
        for v in event.values():
            print(v)

def search(query, max_results=6):
    # libraries
    from dotenv import load_dotenv
    import os
    from tavily import TavilyClient
    import requests
    from bs4 import BeautifulSoup
    from duckduckgo_search import DDGS
    import re
    # load environment variables from .env file
    _ = load_dotenv()

    # connect
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    # run search
    result = client.search("What is in Nvidia's new Blackwell GPU?",
                       include_answer=True)

    ddg = DDGS()

    try:
        results = ddg.text(query, max_results=max_results)
        return [i["href"] for i in results]
    except Exception as e:
        print(f"returning previous results due to exception reaching ddg.")
        results = [ # cover case where DDG rate limits due to high deeplearning.ai volume
            "https://weather.com/weather/today/l/USCA0987:1:US",
            "https://weather.com/weather/hourbyhour/l/54f9d8baac32496f6b5497b4bf7a277c3e2e6cc5625de69680e6169e7e38e9a8",
        ]
        return results  

def scrape_weather_info(url):
    """Scrape content from the given URL"""
    if not url:
        return "Weather information could not be found."
    
    # fetch data
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return "Failed to retrieve the webpage."

    # parse result
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup



if __name__ == "__main__":
    #search_tool()
    # choose location (try to change to your own city!)
    city = "San Francisco"

    query = f"""
        what is the current weather in {city}?
        Should I travel there today?
        "weather.com"
    """
    
    for i in search(query):
        print(i)
    # use DuckDuckGo to find websites and take the first result
    url = search(query)[0]

    # scrape first wesbsite
    soup = scrape_weather_info(url)

    print(f"Website: {url}\n\n")
    print(str(soup.body)[:50000]) # limit long outputs
    # extract text
    weather_data = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
        text = tag.get_text(" ", strip=True)
        weather_data.append(text)

    # combine all elements into a single string
    weather_data = "\n".join(weather_data)

    # remove all spaces from the combined text
    weather_data = re.sub(r'\s+', ' ', weather_data)
        
    print(f"Website: {url}\n\n")
    print(weather_data)
    # run search
    result = client.search(query, max_results=1)

    # print first result
    data = result["results"][0]["content"]

    print(data)
    import json
    from pygments import highlight, lexers, formatters

    # parse JSON
    parsed_json = json.loads(data.replace("'", '"'))

    # pretty print JSON with syntax highlighting
    formatted_json = json.dumps(parsed_json, indent=4)
    colorful_json = highlight(formatted_json,
                            lexers.JsonLexer(),
                            formatters.TerminalFormatter())

    print(colorful_json)
