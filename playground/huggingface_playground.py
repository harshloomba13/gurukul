# Use a pipeline as a high-level helper
from transformers import pipeline, Conversation

chatbot = pipeline(task="conversational", model ="facebook/blenderbot-400M-distill")
user_message="""what are some fun activities i can do in winter"""
conversation = Conversation(user_message)
print(conversation)
conversation = chatbot(conversation)
print(conversation)