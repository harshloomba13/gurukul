import os
from openai import OpenAI
from utils import (
    generate_with_single_input,
    generate_with_multiple_input,
)

# Simple OpenAI client using OPENAI_API_KEY from the environment.
client = OpenAI()

messages = [
    {'role': 'user', 'content': 'Hello, who won the FIFA world cup in 2018?'},
    {'role': 'assistant', 'content': 'France won the 2018 FIFA World Cup.'},
    {'role': 'user', 'content': 'Who was the captain?'}
]

response = client.chat.completions.create(
    messages=messages,
    model="gpt-4o-mini",
)

#print(response.choices[0].message.content)

house_data = [
    {
        "address": "123 Maple Street",
        "city": "Springfield",
        "state": "IL",
        "zip": "62701",
        "bedrooms": 3,
        "bathrooms": 2,
        "square_feet": 1500,
        "price": 230000,
        "year_built": 1998
    },
    {
        "address": "456 Elm Avenue",
        "city": "Shelbyville",
        "state": "TN",
        "zip": "37160",
        "bedrooms": 4,
        "bathrooms": 3,
        "square_feet": 2500,
        "price": 320000,
        "year_built": 2005
    }
]

# First, let's create a layout for the houses

def house_info_layout(houses):
    # Create an empty string
    layout = ''
    # Iterate over the houses
    for house in houses:
        # For each house, append the information to the string using f-strings
        # The following way using brackets is a good way to make the code readable as in each line you can start a new f-string that will appended to the previous one
        layout += (f"House located at {house['address']}, {house['city']}, {house['state']} {house['zip']} with "
            f"{house['bedrooms']} bedrooms, {house['bathrooms']} bathrooms, "
            f"{house['square_feet']} sq ft area, priced at ${house['price']}, "
            f"built in {house['year_built']}.\n") # Don't forget the new line character at the end!
    return layout

def generate_prompt(query, houses):
    # The code made above is modular enough to accept any list of houses, so you could also choose a subset of the dataset.
    # This might be useful in a more complex context where you want to give only some information to the LLM and not the entire data
    houses_layout = house_info_layout(houses)
    # Create a hard-coded prompt. You can use three double quotes (") in this cases, so you don't need to worry too much about using single or double quotes and breaking the code
    PROMPT = f"""
Use the following houses information to answer users queries.
{houses_layout}
Query: {query}    
             """
    return PROMPT

query = "What is the most expensive house? And the bigger one?"
# Asking without the augmented prompt, let's pass the role as user
query_without_house_info = generate_with_single_input(prompt = query, role = 'user')
# With house info, given the prompt structuer, let's pass the role as assistant
enhanced_query = generate_prompt(query, houses = house_data)
query_with_house_info = generate_with_single_input(prompt = enhanced_query, role = 'assistant')

# Without house info
#print(f"Without house info: {query_without_house_info['content']}")

# With house info
#print(f"With house info: {query_with_house_info['content']}")


from sentence_transformers import SentenceTransformer

# Load the pre-trained sentence transformer model
model_name = "BAAI/bge-base-en-v1.5"

# Use MODELS env var if set, otherwise load directly (will download if needed)
if 'MODELS' in os.environ:
    model = SentenceTransformer(os.path.join(os.environ['MODELS'], model_name))
else:
    model = SentenceTransformer(model_name)

# To get a string embedded, just pass it to the model.
res = model.encode("RAG is awesome")
#print(res.shape)

words = ['apple', 'car', 'fruit', 'automobile', 'love', 'sentiment']
vectorized_words = model.encode(words)

word = 'apple'
print(f"{word}:")
for i, w in enumerate(words):
    # Get the vectorized word for the word defined above
    vectorized_word = vectorized_words[words.index(word)]
    print(f"\t{w}:\t\tCosine Similarity: {cosine_similarity(vectorized_word, vectorized_words[i])[0]:.4f}")
print("\n\n\n")
for i, w in enumerate(words):
    # Get the vectorized word for the word defined above
    vectorized_word = vectorized_words[words.index(word)]
    print(f"\t{w}:\t\tEuclidean Distance: {euclidean_distance(vectorized_word, vectorized_words[i])[0]:.4f}")