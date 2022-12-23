from youtubesearchpython import *

# title is of the form: Nathalie Cabrol: Search for Alien Life | Lex Fridman Podcast #348 by Lex Fridman 2 days ago 2 hours, 6 minutes
# we want to cleanup the last bit which is after the by Lex fridman
def cleanup_title(title: str):
    end_index = title.rfind('by Lex Fridman')
    final_title = title[:end_index]
    return final_title.strip()

channel_id = "UCSHZKyawb77ixDdsGog4iWA"
playlist = Playlist(playlist_from_channel_id(channel_id))

print(f'Videos Retrieved: {len(playlist.videos)}')

while playlist.hasMoreVideos:
    print('Getting more videos...')
    playlist.getNextVideos()
    print(f'Videos Retrieved: {len(playlist.videos)}')

print('Found all the videos.')

playlist_list = []
for play in playlist.videos:
    title = play['accessibility']['title']
    url = f"https://www.youtube.com/watch?v={play['id']}"
    if '| Lex Fridman Podcast' in title:
        playlist_list.append({
            'title': cleanup_title(title),
            'url': url,
        })
    print(title)
    print(url)

import json
with open('/tmp/document', 'w') as f:
    f.write(json.dumps(playlist_list))