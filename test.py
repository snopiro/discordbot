# import requests
# import json
# import os

# #args = ["lucia_(punishing:_gray_raven)"]
# args = ["sldkjfslsf"]
# search_query = '+'.join(args)
# print("tags: " + search_query)

# # Get the total count of images matching the search query
# wideCall = requests.get(f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={search_query}")
# json_data = wideCall.json()

# if (json_data == ""):
#     print("Invalid tags")

# # Get the number of responses
# num_responses = len(json_data)

# print(f"Number of responses: {num_responses}")



from __future__ import unicode_literals
import youtube_dl
print("Insert the link")
link = input ("")

ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '320',
    }],
}

with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    ydl.download([link])