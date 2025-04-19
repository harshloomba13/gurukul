import warnings
warnings.filterwarnings('ignore', message='.*OpenSSL.*')
warnings.filterwarnings('ignore', message='.*resume_download.*')

# Use a pipeline as a high-level helper
from transformers import pipeline, Conversation
from sentence_transformers import SentenceTransformer, util
import torch

def chat_with_bot(user_message):
    chatbot = pipeline(task="conversational", model ="facebook/blenderbot-400M-distill")
    user_message="""what are some fun activities i can do in winter"""
    conversation = Conversation(user_message)
    conversation = chatbot(conversation)

    conversation.add_message({"role": "user", "content":"what else do you recommend?"})
    print(conversation)

def translate_text(text, src_lang, tgt_lang):
    translator = pipeline(task="translation",
                      model="facebook/nllb-200-distilled-600M",
                      torch_dtype=torch.bfloat16) 

    text_translated = translator(text,
                             src_lang=src_lang,
                             tgt_lang=tgt_lang)
    return text_translated

def sentence_similarity():
    model = SentenceTransformer("all-MiniLM-L6-v2")
    sentences1 = ['The cat sits outside',
              'A man is playing guitar',
              'The movies are awesome']
    embeddings1 = model.encode(sentences1, convert_to_tensor=True)
    sentences2 = ['The dog plays in the garden',
              'A woman watches TV',
              'The new movie is so great']
    embeddings2 = model.encode(sentences2, 
                           convert_to_tensor=True)
    cosine_scores = util.cos_sim(embeddings1,embeddings2)

    for i in range(len(sentences1)):
        print("{} \t\t {} \t\t Score: {:.4f}".format(sentences1[i],
                                                 sentences2[i],
                                                 cosine_scores[i][i]))

if __name__ == "__main__":
    text = """\
    My puppy is adorable, \
    Your kitten is cute.
    Her panda is friendly.
    His llama is thoughtful. \
    We all have nice pets!"""

    #text_translated = translate_text(text, "eng_Latn", "fra_Latn")

    #print(text_translated)

    sentence_similarity()
