#=======
#model prompts
import os
from openai import OpenAI

from dotenv import load_dotenv, find_dotenv
_ = load_dotenv(find_dotenv()) # read local .env file
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

#account for deprecation of LLM model
import datetime
#Get the current date
current_date = datetime.datetime.now().date()

#Define the date after which the model should be set to "gpt-3.5-turbo"
target_date = datetime.date(2024, 6, 12)

#Set the model variable based on the current date
if current_date > target_date:
    llm_model = "gpt-3.5-turbo"
else:
    llm_model = "gpt-3.5-turbo-0301"

def get_completion(prompt, model=llm_model):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, 
    )
    return response.choices[0].message.content


# customer_email = """
# Arrr, I be fuming that me blender lid \
# flew off and splattered me kitchen walls \
# with smoothie! And to make matters worse,\
# the warranty don't cover the cost of \
# cleaning up me kitchen. I need yer help \
# right now, matey!
# """
#
# style = """American English \
# in a calm and respectful tone
# """
#
# prompt = f"""Translate the text \
# that is delimited by triple backticks 
# into a style that is {style}.
# text: ```{customer_email}```
# """
#
# response = get_completion(prompt)
#
# from langchain_openai import ChatOpenAI
#
# To control the randomness and creativity of the generated
# text by an LLM, use temperature = 0.0
# chat = ChatOpenAI(temperature=0.0, model=llm_model)
#
# template_string = """Translate the text \
# that is delimited by triple backticks \
# into a style that is {style}. \
# text: ```{text}```
# """
# from langchain_core.prompts import ChatPromptTemplate
#
# prompt_template = ChatPromptTemplate.from_template(template_string)
#print(prompt_template.messages[0].content)
#
#
# customer_review = """\
# This leaf blower is pretty amazing.  It has four settings:\
# candle blower, gentle breeze, windy city, and tornado. \
# It arrived in two days, just in time for my wife's \
# anniversary present. \
# I think my wife liked it so much she was speechless. \
# So far I've been the only one using it, and I've been \
# using it every other morning to clear the leaves on our lawn. \
# It's slightly more expensive than the other leaf blowers \
# out there, but I think it's worth it for the extra features.
# """
#
# review_template = """\
# For the following text, extract the following information:
#
# gift: Was the item purchased as a gift for someone else? \
# Answer True if yes, False if not or unknown.
#
# delivery_days: How many days did it take for the product \
# to arrive? If this information is not found, output -1.
#
# price_value: Extract any sentences about the value or price,\
# and output them as a comma separated Python list.
#
# Format the output as JSON with the following keys:
# gift
# delivery_days
# price_value
#
# text: {text}
# """
#
#
# from langchain_core.prompts import ChatPromptTemplate
# import json
# prompt_template = ChatPromptTemplate.from_template(review_template)
#print(prompt_template)
#
# messages = prompt_template.format_messages(text=customer_review)
# chat = ChatOpenAI(temperature=0.0, model=llm_model)
# response = chat.invoke(messages)
#print(response.content)
#print(type(response.content))
# You will get an error by running this line of code 
# because'gift' is not a dictionary
# 'gift' is a string
#print(json.loads(response.content).get('gift'))
#
# from langchain.output_parsers import ResponseSchema
# from langchain.output_parsers import StructuredOutputParser
#
# gift_schema = ResponseSchema(name="gift",
#                              description="Was the item purchased\
#                              as a gift for someone else? \
#                              Answer True if yes,\
#                              False if not or unknown.")
# delivery_days_schema = ResponseSchema(name="delivery_days",
#                                       description="How many days\
#                                       did it take for the product\
#                                       to arrive? If this \
#                                       information is not found,\
#                                       output -1.")
# price_value_schema = ResponseSchema(name="price_value",
#                                     description="Extract any\
#                                     sentences about the value or \
#                                     price, and output them as a \
#                                     comma separated Python list.")
#
# response_schemas = [gift_schema, 
#                     delivery_days_schema,
#                     price_value_schema]
#
# output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
# format_instructions = output_parser.get_format_instructions()
#print(format_instructions)
#
# review_template_2 = """\
# For the following text, extract the following information:
#
# gift: Was the item purchased as a gift for someone else? \
# Answer True if yes, False if not or unknown.
#
# delivery_days: How many days did it take for the product\
# to arrive? If this information is not found, output -1.
#
# price_value: Extract any sentences about the value or price,\
# and output them as a comma separated Python list.
#
# text: {text}
#
# {format_instructions}
# """
#
# prompt = ChatPromptTemplate.from_template(template=review_template_2)
#
# messages = prompt.format_messages(text=customer_review, 
#                                 format_instructions=format_instructions)
#
#print(f"messages[0].content: {messages[0].content}")
# response = chat.invoke(messages)
#print(f"response.content: {response.content}")
# output_dict = output_parser.parse(response.content)
#print(f"output_dict: {output_dict}")
#print(f"output_dict.get('delivery_days'): {output_dict.get('delivery_days')}")
#
#
#================================================
#memeory management
# from langchain_openai import ChatOpenAI
# from langchain_core.chat_history import InMemoryChatMessageHistory
# from langchain_core.prompts import MessagesPlaceholder
# from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain.memory import (
#     ConversationBufferMemory,
#     ConversationBufferWindowMemory,
#     ConversationTokenBufferMemory,)
# llm = ChatOpenAI(temperature=0.0, model=llm_model)
# memory = ConversationBufferMemory()
# prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", "You are a helpful assistant."),
#         MessagesPlaceholder("history"),
#         ("human", "{input}"),
#     ]
# )
# chain = prompt | llm
# history = InMemoryChatMessageHistory()
# conversation = RunnableWithMessageHistory(
#     chain,
#     lambda session_id: history,
#     input_messages_key="input",
#     history_messages_key="history",
# )
#
#
# print(
#     conversation.invoke(
#         {"input": "Hi, my name is Andrew"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
# print(
#     conversation.invoke(
#         {"input": "What is 1+1?"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
# print(
#     conversation.invoke(
#         {"input": "What is my name?"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
# print(f"memory.buffer: {memory.buffer}")
# print(f"memory.load_memory_variables(): {memory.load_memory_variables({})}")
# memory = ConversationBufferMemory()
# memory.save_context({"input": "Hi"}, 
#                     {"output": "What's up"})
# print(f"memory.buffer: {memory.buffer}")
# print(f"memory.load_memory_variables(): {memory.load_memory_variables({})}")
# memory.save_context({"input": "Not much, just hanging"}, 
#                     {"output": "Cool"})
# print(f"memory.load_memory_variables(): {memory.load_memory_variables({})}")
#
#
# memory = ConversationBufferWindowMemory(k=2)               
# memory.save_context({"input": "Hi"},
#                     {"output": "What's up"})
# memory.save_context({"input": "Not much, just hanging"},
#                     {"output": "Cool"})
#
# print(f"memory.load_memory_variables(): {memory.load_memory_variables({})}")
#
#
# llm = ChatOpenAI(temperature=0.0, model=llm_model)
# memory = ConversationBufferWindowMemory(k=2)
# conversation = RunnableWithMessageHistory(
#     chain,
#     lambda session_id: history,
#     input_messages_key="input",
#     history_messages_key="history",
# )
# print(
#     conversation.invoke(
#         {"input": "Hi, my name is Andrew"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
# print(
#     conversation.invoke(
#         {"input": "What is 1+1?"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
# print(
#     conversation.invoke(
#         {"input": "What is my name?"},
#         config={"configurable": {"session_id": "demo"}},
#     )
# )
#
# llm = ChatOpenAI(temperature=0.0, model=llm_model)
#
# memory = ConversationTokenBufferMemory(llm=llm, max_token_limit=30)
# memory.save_context({"input": "AI is what?!"},
#                     {"output": "Amazing!"})
# memory.save_context({"input": "Backpropagation is what?"},
#                     {"output": "Beautiful!"})
# memory.save_context({"input": "Chatbots are what?"}, 
#                     {"output": "Charming!"})
#
#print(memory.load_memory_variables({}))
#
# from langchain.memory import ConversationSummaryBufferMemory
#
# create a long string
# schedule = "There is a meeting at 8am with your product team. \
# You will need your powerpoint presentation prepared. \
# 9am-12pm have time to work on your LangChain \
# project which will go quickly because Langchain is such a powerful tool. \
# At Noon, lunch at the italian resturant with a customer who is driving \
# from over an hour away to meet you to understand the latest in AI. \
# Be sure to bring your laptop to show the latest LLM demo."
#
# memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=50)
# memory.save_context({"input": "Hello"}, {"output": "What's up"})
# memory.save_context({"input": "Not much, just hanging"},
#                     {"output": "Cool"})
# memory.save_context({"input": "What is on the schedule today?"}, 
#                     {"output": f"{schedule}"})
#
#print(memory.load_memory_variables({}))
#
# summary_history = memory.load_memory_variables({}).get("history", "")
# summary_prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", "You are a helpful assistant."),
#         ("system", "Conversation so far: {history}"),
#         ("human", "{input}"),
#     ]
# )
# summary_response = (summary_prompt | llm).invoke(
#     {"history": summary_history, "input": "What would be a good demo to show?"}
# )
#print(summary_response.content)
#
#print(memory.load_memory_variables({}))
#
#==========
#langchain
# import pandas as pd
# df = pd.read_csv('Data.csv')
# df.head()
#
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import ChatPromptTemplate
# from langchain.chains import LLMChain
#
# llm = ChatOpenAI(temperature=0.9, model=llm_model)
#
# prompt = ChatPromptTemplate.from_template(
#     "What is the best name to describe \
#     a company that makes {product}?"
# )
#
# chain = LLMChain(llm=llm, prompt=prompt)
#
# product = "Queen Size Sheet Set"
#
#print(chain.run(product))
#
# from langchain.chains import SimpleSequentialChain
#
# llm = ChatOpenAI(temperature=0.9, model=llm_model)
#
# prompt template 1
# first_prompt = ChatPromptTemplate.from_template(
#     "What is the best name to describe \
#     a company that makes {product}?"
# )
#
# Chain 1
# chain_one = LLMChain(llm=llm, prompt=first_prompt)
#
# prompt template 2
# second_prompt = ChatPromptTemplate.from_template(
#     "Write a 20 words description for the following \
#     company:{company_name}"
# )
# chain 2
# chain_two = LLMChain(llm=llm, prompt=second_prompt)
#
# overall_simple_chain = SimpleSequentialChain(chains=[chain_one, chain_two],
#                                              verbose=True
#                                             )
#print(overall_simple_chain.run(product))
#
#
# from langchain.chains import SequentialChain
#
# llm = ChatOpenAI(temperature=0.9, model=llm_model)
#
# prompt template 1: translate to english
# first_prompt = ChatPromptTemplate.from_template(
#     "Translate the following review to english:"
#     "\n\n{Review}"
# )
# chain 1: input= Review and output= English_Review
# chain_one = LLMChain(llm=llm, prompt=first_prompt, 
#                      output_key="English_Review"
#                     )
#
# second_prompt = ChatPromptTemplate.from_template(
#     "Can you summarize the following review in 1 sentence:"
#     "\n\n{English_Review}"
# )
# chain 2: input= English_Review and output= summary
# chain_two = LLMChain(llm=llm, prompt=second_prompt, 
#                      output_key="summary"
#                     )
#
#
# prompt template 3: translate to english
# third_prompt = ChatPromptTemplate.from_template(
#     "What language is the following review:\n\n{Review}"
# )
# chain 3: input= Review and output= language
# chain_three = LLMChain(llm=llm, prompt=third_prompt,
#                        output_key="language"
#                       )
#
#
# prompt template 4: follow up message
# fourth_prompt = ChatPromptTemplate.from_template(
#     "Write a follow up response to the following "
#     "summary in the specified language:"
#     "\n\nSummary: {summary}\n\nLanguage: {language}"
# )
# chain 4: input= summary, language and output= followup_message
# chain_four = LLMChain(llm=llm, prompt=fourth_prompt,
#                       output_key="followup_message"
#                      )
#
# overall_chain: input= Review 
# and output= English_Review,summary, followup_message
# overall_chain = SequentialChain(
#     chains=[chain_one, chain_two, chain_three, chain_four],
#     input_variables=["Review"],
#     output_variables=["English_Review", "summary","followup_message"],
#     verbose=True
# )
#
# review = df.Review[5]
#print(overall_chain(review))
#
#
#
# physics_template = """You are a very smart physics professor. \
# You are great at answering questions about physics in a concise\
# and easy to understand manner. \
# When you don't know the answer to a question you admit\
# that you don't know.
#
# Here is a question:
# {input}"""
#
#
# math_template = """You are a very good mathematician. \
# You are great at answering math questions. \
# You are so good because you are able to break down \
# hard problems into their component parts, 
# answer the component parts, and then put them together\
# to answer the broader question.
#
# Here is a question:
# {input}"""
#
# history_template = """You are a very good historian. \
# You have an excellent knowledge of and understanding of people,\
# events and contexts from a range of historical periods. \
# You have the ability to think, reflect, debate, discuss and \
# evaluate the past. You have a respect for historical evidence\
# and the ability to make use of it to support your explanations \
# and judgements.
#
# Here is a question:
# {input}"""
#
#
# computerscience_template = """ You are a successful computer scientist.\
# You have a passion for creativity, collaboration,\
# forward-thinking, confidence, strong problem-solving capabilities,\
# understanding of theories and algorithms, and excellent communication \
# skills. You are great at answering coding questions. \
# You are so good because you know how to solve a problem by \
# describing the solution in imperative steps \
# that a machine can easily interpret and you know how to \
# choose a solution that has a good balance between \
# time complexity and space complexity. 
#
# Here is a question:
# {input}"""
#
#
# prompt_infos = [
#     {
#         "name": "physics", 
#         "description": "Good for answering questions about physics", 
#         "prompt_template": physics_template
#     },
#     {
#         "name": "math", 
#         "description": "Good for answering math questions", 
#         "prompt_template": math_template
#     },
#     {
#         "name": "History", 
#         "description": "Good for answering history questions", 
#         "prompt_template": history_template
#     },
#     {
#         "name": "computer science", 
#         "description": "Good for answering computer science questions", 
#         "prompt_template": computerscience_template
#     }
# ]
#
# from langchain.chains.router import MultiPromptChain
# from langchain.chains.router.llm_router import LLMRouterChain,RouterOutputParser
# from langchain_core.prompts import PromptTemplate
#
# llm = ChatOpenAI(temperature=0, model=llm_model)
#
#
# destination_chains = {}
# for p_info in prompt_infos:
#     name = p_info["name"]
#     prompt_template = p_info["prompt_template"]
#     prompt = ChatPromptTemplate.from_template(template=prompt_template)
#     chain = LLMChain(llm=llm, prompt=prompt)
#     destination_chains[name] = chain  
#     
# destinations = [f"{p['name']}: {p['description']}" for p in prompt_infos]
# destinations_str = "\n".join(destinations)
#
# default_prompt = ChatPromptTemplate.from_template("{input}")
# default_chain = LLMChain(llm=llm, prompt=default_prompt)
#
#
# MULTI_PROMPT_ROUTER_TEMPLATE = """Given a raw text input to a \
# language model select the model prompt best suited for the input. \
# You will be given the names of the available prompts and a \
# description of what the prompt is best suited for. \
# You may also revise the original input if you think that revising\
# it will ultimately lead to a better response from the language model.
#
# << FORMATTING >>
# Return a markdown code snippet with a JSON object formatted to look like:
# ```json
# {{{{
#     "destination": string \ "DEFAULT" or name of the prompt to use in {destinations}
#     "next_inputs": string \ a potentially modified version of the original input
# }}}}
# ```
#
# REMEMBER: The value of “destination” MUST match one of \
# the candidate prompts listed below.\
# If “destination” does not fit any of the specified prompts, set it to “DEFAULT.”
# REMEMBER: "next_inputs" can just be the original input \
# if you don't think any modifications are needed.
#
# << CANDIDATE PROMPTS >>
# {destinations}
#
# << INPUT >>
# {{input}}
#
# << OUTPUT (remember to include the ```json)>>"""
#
#
# router_template = MULTI_PROMPT_ROUTER_TEMPLATE.format(
#     destinations=destinations_str
# )
# router_prompt = PromptTemplate(
#     template=router_template,
#     input_variables=["input"],
#     output_parser=RouterOutputParser(),
# )
#
# router_chain = LLMRouterChain.from_llm(llm, router_prompt)
#
# chain = MultiPromptChain(router_chain=router_chain, 
#                          destination_chains=destination_chains, 
#                          default_chain=default_chain, verbose=True
#                         )
#
#print(chain.run("What is black body radiation?"))
#
#
#application ased on LLM
#
# from langchain.chains import RetrievalQA
# from langchain_openai import ChatOpenAI, OpenAIEmbeddings, OpenAI as LangChainOpenAI
# from langchain.document_loaders import CSVLoader
# from langchain_community.vectorstores import DocArrayInMemorySearch
# from IPython.display import display, Markdown
#
# file = 'OutdoorClothingCatalog_1000.csv'
# loader = CSVLoader(file_path=file)
#
# from langchain.indexes import VectorstoreIndexCreator
#
# index = VectorstoreIndexCreator(
#     embedding=OpenAIEmbeddings(),
#     vectorstore_cls=DocArrayInMemorySearch
# ).from_loaders([loader])
#
# query ="Please list all your shirts with sun protection \
# in a table in markdown and summarize each one."
#
# llm_replacement_model = LangChainOpenAI(
#     temperature=0,
#     model="gpt-3.5-turbo-instruct",
# )
#
# response = index.query(query, 
#                        llm = llm_replacement_model)
#print(Markdown(response).data)
#
# from langchain.document_loaders import CSVLoader
# loader = CSVLoader(file_path=file)
#
# docs = loader.load()
#
#print(docs[0])
#
# from langchain.embeddings import OpenAIEmbeddings
# embeddings = OpenAIEmbeddings()
#
# embed = embeddings.embed_query("Hi my name is Harrison")
#
#print(len(embed))
#
#print(embed[:5])
#
# db = DocArrayInMemorySearch.from_documents(
#     docs, 
#     embeddings
# )
#
# query = "Please suggest a shirt with sunblocking"
#
# docs = db.similarity_search(query)
#
#print(len(docs))
#
#print(docs[0])
#
# retriever = db.as_retriever()
#
# llm = ChatOpenAI(temperature = 0.0, model=llm_model)
#
# qdocs = "".join([docs[i].page_content for i in range(len(docs))])
# response = llm.call_as_llm(f"{qdocs} Question: Please list all your \
# shirts with sun protection in a table in markdown and summarize each one.") 
#
#print(Markdown(response).data)
#
# qa_stuff = RetrievalQA.from_chain_type(
#     llm=llm, 
#     chain_type="stuff", 
#     retriever=retriever, 
#     verbose=True
# )
#
# query =  "Please list all your shirts with sun protection in a table \
# in markdown and summarize each one."
#
#
# response = qa_stuff.run(query)
#
#print(Markdown(response).data)
#
# response = index.query(query, llm=llm)
#
# index = VectorstoreIndexCreator(
#     vectorstore_cls=DocArrayInMemorySearch,
#     embedding=embeddings,
# ).from_loaders([loader])
#
# llm = ChatOpenAI(temperature = 0.0, model=llm_model)
# qa = RetrievalQA.from_chain_type(
#     llm=llm, 
#     chain_type="stuff", 
#     retriever=index.vectorstore.as_retriever(), 
#     verbose=True,
#     chain_type_kwargs = {
#         "document_separator": "<<<<>>>>>"
#     }
# )
#
# examples = [
#     {
#         "query": "Do the Cozy Comfort Pullover Set\
#         have side pockets?",
#         "answer": "Yes"
#     },
#     {
#         "query": "What collection is the Ultra-Lofty \
#         850 Stretch Down Hooded Jacket from?",
#         "answer": "The DownTek collection"
#     }
# ]
#
# from langchain.evaluation.qa import QAGenerateChain
#
# example_gen_chain = QAGenerateChain.from_llm(ChatOpenAI(model=llm_model))
#
# new_examples = example_gen_chain.apply_and_parse(
#     [{"doc": t} for t in docs[:5]]
# )
#
#print(f"examples - {new_examples[0]}")
#
#print(f"doc zero - {docs[0]}")
#
# examples += new_examples
#
#manual evaluation 
# import langchain
# langchain.debug = True
# qa.run(examples[0]["query"])
#
# Turn off the debug mode
# langchain.debug = False
#
#llm asisted evaluation
# predictions = qa.apply(examples)
# from langchain.evaluation.qa import QAEvalChain
#
# llm = ChatOpenAI(temperature=0, model=llm_model)
# eval_chain = QAEvalChain.from_llm(llm)
#
# graded_outputs = eval_chain.evaluate(examples, predictions)
# for i, eg in enumerate(examples):
#     print(f"Example {i}:")
#     print("Question: " + predictions[i]['query'])
#     print("Real Answer: " + predictions[i]['answer'])
#     print("Predicted Answer: " + predictions[i]['result'])
#     print("Predicted Grade: " + graded_outputs[i]['text'])
#
# print(graded_outputs[0])
#
#agents 

from langchain_community.agent_toolkits.load_tools import load_tools
from langchain.agents import initialize_agent
from langchain.agents import AgentType
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(temperature=0, model=llm_model)

tools = load_tools(["llm-math","wikipedia"], llm=llm)

agent= initialize_agent(
    tools, 
    llm, 
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    verbose = False)


#print(agent("What is the 25% of 300?"))

question = "Tom M. Mitchell is an American computer scientist \
and the Founders University Professor at Carnegie Mellon University (CMU)\
what book did he write?"
result = agent(question) 

customer_list = [
    ["Harrison", "Chase"],
    ["Lang", "Chain"],
    ["Dolly", "Too"],
    ["Elle", "Elem"],
    ["Geoff", "Fusion"],
    ["Trance", "Former"],
    ["Jen", "Ayai"],
]

try:
    from langchain_experimental.agents.agent_toolkits.python.base import (
        create_python_agent,
    )
    from langchain_experimental.tools.python.tool import PythonREPLTool

    python_agent = create_python_agent(
        llm=llm,
        tool=PythonREPLTool(),
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        agent_executor_kwargs={"handle_parsing_errors": True},
    )
    #python_agent.run(
    #    "Sort these customers by last name and then first name "
    #    f"and print the output: {customer_list}"
    #)
except Exception as exc:
    print(f"Python agent disabled: {exc}")



from langchain.agents import tool
from datetime import date

@tool
def time(text: str) -> str:
    """Returns todays date, use this for any \
    questions related to knowing todays date. \
    The input should always be an empty string, \
    and this function will always return todays \
    date - any date mathmatics should occur \
    outside this function."""
    return str(date.today())

agent= initialize_agent(
    tools + [time], 
    llm, 
    agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    verbose = True)

try:
    result = agent("whats the date today?") 
except: 
    print("exception on external access")