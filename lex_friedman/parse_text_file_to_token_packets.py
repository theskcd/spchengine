# Input is in the format:
# Michael Levin: Biology, Life, Aliens, Evolution, Embryogenesis & Xenobots | Lex Fridman Podcast #325 {'name': 'Michael Levin', 'file_name': 'episode_0325_large.vtt', 'url': 'https://www.youtube.com/watch?v=p3lsYlod5OU', 'video_name': '  Michael Levin: Biology, Life, Aliens, Evolution, Embryogenesis & Xenobots | Lex Fridman Podcast #325'}
# The name of the video_name: {actor_name, file_name, url_yt, video_name}
# We store in fireestore in the above format as well
# lex/vidoe_name/embeddings
# and we also store a special lex/video_name/embeddings/metadata
# in metadata we will store the yt_url like and the video name as well,
# on the UI we want to show this as a URL in a table so people can click and
# play with it (lets worry about performance later once we get everything building and working)

alread_done_list = [
]

parsed_name_with_url_and_file_path = {}
import json
with open('/tmp/parsed_text_file', 'r') as f:
    file_info = f.readlines()
    parsed_name_with_url_and_file_path = json.loads(file_info[0])

for item, value in parsed_name_with_url_and_file_path.items():
    if not item.isascii():
        print("Found offending entry", item)
        print(value)

# print(parsed_name_with_url_and_file_path)

# First we need to parse a single packet of text with the metadata, what do we generate
# The file looks like this
# 40:49.520 --> 40:57.760
#  War I, it would be to make sure that systems aren't locked into place, that escalate wars out of
# 
# And repeat above
CHUNK_SIZE = 1024

# Time string is in format HH:MM:SECONDS (seconds can be in float)
def convert_timestring_to_seconds(time_string):
    time_string_parts = time_string.strip().split(':')
    # Reverse it to make writing code easier as we do seconds + min * 60 + house * 60 * 60
    time_string_parts.reverse()
    time_string_length = len(time_string_parts)
    total_time = 0
    if time_string_length == 2:
        total_time = int(float(time_string_parts[0])) + int(time_string_parts[1]) * 60
    elif time_string_length == 3:
        total_time = int(float(time_string_parts[0])) + int(time_string_parts[1]) * 60 + int(time_string_parts[2]) * 60
    return total_time

# Returns a bulk of dialouge here
def parse_input_files_in_chunks(file_name):
    file_contents = []
    with open(file_name, 'r') as f:
        file_contents = f.readlines()
    
    final_file_contents = []
    file_length = len(file_contents) - 1
    start_index = 2
    while start_index < file_length:
        if (start_index + 1 > file_length):
            break
        time_string = file_contents[start_index]
        time_string_parts = time_string.split('-->')
        # print(time_string_parts)
        first_time_string_part = time_string_parts[0].strip()
        second_time_string_part = time_string_parts[1].strip()
        # print(first_time_string_part, second_time_string_part)
        content = file_contents[start_index + 1]
        start_index = start_index + 3
        final_content_string = content
        final_file_contents.append(
            {
                'content': f"{final_content_string}",
                'start_timestamp': convert_timestring_to_seconds(first_time_string_part),
                'token_count': len(final_content_string.split(' ')),
                'end_timestamp': convert_timestring_to_seconds(second_time_string_part),
            }
        )
    return final_file_contents

# Now that we have the file parts we need to group them together in groups of 2048 tokens and then send
# them over to firestore, we also need metadata about the video as well
# testing_file_name = parsed_name_with_url_and_file_path['  John Carmack: Doom, Quake, VR, AGI, Programming, Video Games, and Rockets | Lex Fridman Podcast #309']['file_name']
# testing_file_property = parsed_name_with_url_and_file_path['  John Carmack: Doom, Quake, VR, AGI, Programming, Video Games, and Rockets | Lex Fridman Podcast #309']
# file_parts = parse_input_files_in_chunks(f'/Users/skcd/Downloads/vtt/{testing_file_name}')

# each file part is made up of the json content, start_timestamp, token_count, end_timestamp
def get_grouped_file_content_from_file(file_parts):
    start_index = 0
    file_parts_length = len(file_parts) - 1
    grouped_file_parts = []
    while start_index < file_parts_length:
        now_pointer = start_index
        token_count = 0
        part_group = []
        timestamps = []
        while now_pointer < file_parts_length:
            token_count = token_count + file_parts[now_pointer]['token_count']
            timestamps.append(file_parts[now_pointer]['start_timestamp'])
            part_group.append(file_parts[now_pointer])
            now_pointer = now_pointer + 1
            if token_count > CHUNK_SIZE:
                grouped_file_parts.append({'text_for_group': part_group, 'timestamps': timestamps})
                break
        start_index = now_pointer
        if len(part_group) != 0:
            grouped_file_parts.append({'text_for_group': part_group, 'timestamps': timestamps})
    # now we do something here with the file parts, we need to group them together in chunk sizes
    return grouped_file_parts

# grouped_file_input = get_grouped_file_content_from_file(file_parts)
# print(len(grouped_file_input))

# Now we store these groupings in firestore and hope that we can generate the context from this
import pinecone
import openai

# Initialize firebase bullshit here
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
cred = credentials.Certificate("/Users/skcd/spchengine/lex_friedman/creds.json")
firebase_admin.initialize_app(cred)
db = firestore.client()


openai.api_key = "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"
# Are we here?
pinecone.init(api_key="803b2348-5642-49b3-893c-633f2e5e6a38", environment="us-west1-gcp")
# We are here?
PINECONE_INDEX = pinecone.Index('testing-index6') # this is the testing index we have

def put_embedding_in_firestore(embedding, firestore_path):
    PINECONE_INDEX.upsert([(firestore_path, embedding)])

# This gives us back the vector of embeddings which we should use for cosine-similarity
# I think it returns a vector because it might be splitting the input text by itself
# into chunks (most probably but not sure, lets better be safe as the api works based
# on tokens we are inserting)
def openai_embedding(content):
    response = openai.Embedding.create(input=content, model="text-embedding-ada-002")
    return response['data'][0]['embedding']

# Now lets store this in firestore and then add the embeddings to openai and see what we get when we query
def save_to_firestore(content, video_name, counter_count, podcast_url, name, timestamps, embeddings):
    collection_path = f"lex_friedman/convo6/{video_name}"
    response = db.collection(collection_path).document(f"{counter_count}").set({
        'content': content,
        'podcast_url': podcast_url,
        'name': name,
        'timestamps': timestamps,
        'embeddings': embeddings,
    })
    return f"lex_friedman/convo6/{video_name}/{counter_count}"


import sys

# the metadata contains the link to the video and the name of the person in the podcast
def put_grouped_file_content_in_firestore(grouped_file_input, metadata, video_name):
    podcast_convo_with = metadata['name']
    podcast_url = metadata['url']
    prompt = f"The following is a conversation between {podcast_convo_with} and Lex Friedman.\n\n"
    for idx, grouped_input in enumerate(grouped_file_input):
        file_input = "".join([input['content'] for input in grouped_input['text_for_group']])
        timestamps = grouped_input['timestamps']
        final_input = prompt + file_input
        embedding = openai_embedding(final_input)
        firestore_path = save_to_firestore(final_input, video_name, idx, podcast_url, podcast_convo_with, timestamps, embedding)
        put_embedding_in_firestore(embedding, firestore_path)
        # Now we put this on firestore and see how it works

# put_grouped_file_content_in_firestore(grouped_file_input, testing_file_property)


# Create final function which will do everything from a single input
# we also need to take care of the cases where the file might be generated using
# a small model
# print(parsed_name_with_url_and_file_path)
import os
for key, parsed_name_with_url_and_file in parsed_name_with_url_and_file_path.items():
    file_name = parsed_name_with_url_and_file['file_name']
    name = parsed_name_with_url_and_file['name']
    video_name = parsed_name_with_url_and_file['video_name'].strip()
    # First we try to see if we have already put the data in for this video name,
    # if so we skip
    already_put = False
    for done_list in alread_done_list:
        if done_list in video_name:
            already_put = True
            print(f"We have already seen this video {video_name}")
    if already_put:
        continue
    print(video_name)
    podcast_url = parsed_name_with_url_and_file['url']
    # We need to check which of large or small is present here, so lets do that
    file_parts = parse_input_files_in_chunks(f'/Users/skcd/Downloads/vtt/{file_name}')
    grouped_file_input = get_grouped_file_content_from_file(file_parts)
    put_grouped_file_content_in_firestore(grouped_file_input, parsed_name_with_url_and_file, video_name)
