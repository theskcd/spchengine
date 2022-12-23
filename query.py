# This is a sample example of how we can query the embeddings and use that to do something

import openai
import pinecone

# copy-pasta judge me idgaf
# Initialize firebase bullshit here
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate("/Users/skcd/spchengine/lex_friedman/creds.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
openai.api_key = "PUT_TOKEN_HERE"
pinecone.init(api_key="API_KEY_HERE", environment="us-west1-gcp")
PINECONE_INDEX = pinecone.Index('testing-index4') # this is the testing index we have

def create_initial_prompt_for_question(convo_context, context, query):
    return f"Answer this as thruthfully you can, and if you dont know say \"I dont know\", \n This is a conversation between {convo_context}.\n The conversation is given below:\n {context} \n. Answer the following: {query}. Be short and concise and reply in 2-3 sentences\n"


def give_more_context(convo_context, context, query, previous_answer):
    return f"Answer this as thruthfully you can, and if you dont know say \"I dont know\", \n This is a conversation between {convo_context}.\n The conversation is given below:\n {context} \n. Answer the following: {query}, you previously answered with {previous_answer}. Be short and concise and reply in 2-3 sentences\n"

def openai_completion(context, query, convo_context):
    response = openai.Completion.create(model="text-davinci-002", temperature=0.1, prompt=create_initial_prompt_for_question(convo_context, context, query), max_tokens=256)
    return response


# This returns the embedding of the query we are asking the DB
def get_query_embedding(query):
    response = openai.Embedding.create(input=query, model="text-embedding-ada-002")
    return response['data'][0]['embedding']

# Get 2-NN for now for the query from the pinecone DB we have
def get_knn_from_pinecone_index(embedding):
    response = PINECONE_INDEX.query(
        embedding,
        top_k=1,
        include_values=True,
    )
    return response.matches


if __name__ == '__main__':
    query = "What debuggers did john carmack use?"
    print(f"Query: {query}")
    query_embedding = get_query_embedding(query=query)
    related_embeddings = get_knn_from_pinecone_index(query_embedding)
    firestore_ids = []
    for matching_response in related_embeddings:
        firestore_ids.append(matching_response['id'])
    convo_context = "Lex Friedman and John Carmack"
    # firestore_ids = ['lex_friedman/mnsMdWWw8Nk24CflbxEr', 'lex_friedman/JrYNU4yFcuh8e0S2zs43', 'lex_friedman/9vTvMBy6xd3UE783BQqR']
    # Now that we have the firestore embeddings, lets ask chat=gpt about this and see
    # what it thinks, again this API is token based so we can iterate through things
    # we will figure out the cost factor later on (famous last words)
    context_for_answer = []
    for firestore_id in firestore_ids:
        print("We are here...")
        print(firestore_id)
        split_firestore_id = firestore_id.split('/')
        data = db.document(firestore_id).get()
        print(data)
        print(data.to_dict()['content'])
        context_for_answer.append(data.to_dict()['content'])
        response = openai_completion(context_for_answer, query, convo_context)
        print(response)
