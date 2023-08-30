import discord
import asyncio
import os
import threading
import requests
import random
import youtube_dl
import re
import json
from discord.ext import commands
from gtts import gTTS

intents = discord.Intents.default()
intents.message_content = True

with open('config.json', 'r') as file:
    config = json.load(file)
    token = config["DISCORD_BOT_TOKEN"]

bot = commands.Bot(command_prefix='$', intents=intents)

# Global variables
running_threads = []


#################################################################
#helper commands
#################################################################

#google tts engine
def text_to_speech(text, output_file):
    tts = gTTS(text)
    tts.save(output_file)

def cleanup_loose_files():
    # Clean up loose TTS files
    for filename in os.listdir():
        if filename.endswith(".mp3"):
            print("Removing " + filename)
            os.remove(filename)

    print("Loose files cleaned up.")


#################################################################
#bot commands
#################################################################
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} ({bot.user.id})')
    in_command = False
    cleanup_loose_files()

@bot.command()
async def hello(ctx):
    await ctx.send('Hello, World!')

@bot.command()
async def tts(ctx, *, message=None):

    # Check if TTS is already in progress
    if getattr(bot, 'is_tts_running', False):
        await ctx.send("TTS is already in progress.")
        return
    
    if len(ctx.message.attachments) > 0:
        await ctx.send("This command does not support file attachments. Please use the `longtts` command instead.")
        return
    
    if (message == None):
        await ctx.send("Nothing was inputted.")
        return

    try:
        channel = ctx.message.author.voice.channel
        if channel:
            voice_client = await channel.connect()
            await ctx.send("Speaking the text.")
            bot.is_tts_running = True

            tts = gTTS(text=message, lang='en')
            tts.save("tts.mp3")
            voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", pipe=False, source="tts.mp3"))

            # Wait until the audio finishes playing
            while voice_client.is_playing():
                await asyncio.sleep(1)

            await voice_client.disconnect()
            await ctx.send("Audio playback finished.")
            bot.is_tts_running = False

            os.remove(f"tts.mp3")
        else:
            await ctx.send("You must be in a voice channel to use this command.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

@bot.command()
async def longtts(ctx):

    # Check if TTS is already in progress
    if getattr(bot, 'is_tts_running', False):
        await ctx.send("TTS is already in progress.")
        return

    if len(ctx.message.attachments) == 0:
        await ctx.send("No file attached.")
        return

    file = ctx.message.attachments[0]
    if not file.filename.endswith('.txt'):
        await ctx.send("Please attach a text file.")
        return

    try:
        in_command = True

        # Cleanup previous files if they exist
        for filename in os.listdir():
            if filename.startswith("tts_") and filename.endswith(".mp3"):
                os.remove(filename)

        content = await file.read()
        content = content.decode('utf-8')

        channel = ctx.message.author.voice.channel
        if channel:
            voice_client = await channel.connect()
            await ctx.send("Reading file in voice channel.")
            bot.is_tts_running = True
            # Determine the maximum character limit per chunk
            max_chars_per_chunk = 200

            # Find appropriate splitting points based on periods
            splitting_points = [0]
            current_length = 0

            for i, char in enumerate(content):
                current_length += 1
                if char == "." and current_length >= max_chars_per_chunk:
                    splitting_points.append(i + 1)
                    current_length = 0

            splitting_points.append(len(content))

            # Function for generating audio chunk in a separate thread
            def generate_audio_chunk(start, end):
                chunk = content[start:end]
                tts = gTTS(text=chunk, lang='en')
                tts.save(f"tts_{start}.mp3")

            # Create and start separate threads for audio generation
            running_threads = []

            for i in range(len(splitting_points) - 1):
                start = splitting_points[i]
                end = splitting_points[i + 1]
                thread = threading.Thread(target=generate_audio_chunk, args=(start, end))
                running_threads.append(thread)
                thread.start()

            # Wait for all threads to finish
            for thread in running_threads:
                thread.join()

            # Play audio chunks
            for i in range(len(splitting_points) - 1):
                start = splitting_points[i]
                voice_client.play(discord.FFmpegPCMAudio(executable="ffmpeg", pipe=False, source=f"tts_{start}.mp3"))

                # Wait until the current chunk finishes playing
                while voice_client.is_playing():
                    await asyncio.sleep(1)

                # Delete the temporary mp3 file
                if getattr(bot, 'is_tts_running', False):
                    os.remove(f"tts_{start}.mp3")

            await voice_client.disconnect()
            await ctx.send("Audio playback finished.")
            bot.is_tts_running = False
        else:
            await ctx.send("You must be in a voice channel to use this command.")
    except Exception as e:
        await ctx.send(f"Error reading file: {e}")

@bot.command()
async def stop(ctx):
    # Stop all running threads
    for thread in running_threads:
        thread.join()

    #disconnect the discord bot
    try:
        voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        if voice_client and voice_client.is_connected():
            await voice_client.disconnect()
            await ctx.send("Bot disconnected from the voice channel.")
        else:
            await ctx.send("Bot is not currently connected to a voice channel.")
    except Exception as e:
        await ctx.send(f"Error: {e}")

    cleanup_loose_files()

    await ctx.send("Playback stopped and files cleaned up.")
    bot.is_tts_running = False

@bot.command()
async def rule34(ctx, *args):
    # Join the arguments as a single string
    search_query = '+'.join(args)
    #print(search_query)

    try:
        # Get the total count of images matching the search query
        wideCall = requests.get(f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&json=1&tags={search_query}")
        json_data = wideCall.json()

        # Get the number of responses
        num_responses = len(json_data)
        #print(f"Number of responses: {num_responses}")

        # Set a random offset based on the total count of images
        offset = random.randint(0, num_responses - 1)

        # Get a random image from rule34.xxx API based on the search query and offset
        url = f"https://api.rule34.xxx/index.php?page=dapi&s=post&q=index&limit=1&json=1&tags={search_query}&pid={offset}"
        response = requests.get(url)
        data = response.json()

        if not data:
            await ctx.send("No images found.")
            return

        # Extract the image URL from the API response
        image_url = data[0]['file_url']

        # Send the image URL in Discord
        await ctx.send(image_url)

    except Exception as e:
        await ctx.send(f"Error: Invalid tags")

@bot.command()
async def youtubemp3(ctx, link):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',
        }],
    }
    await ctx.send(f"Processing...")

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(link, download=False)
        title = info['title']
        ydl.download([link])
        filename = ydl.prepare_filename(info)
        filename = re.sub(r"\.(webm|m4a)$", ".mp3", filename)
        print("Expected filename: " + filename)

    try:
        while not os.path.exists(filename):
            await asyncio.sleep(1)  # Wait until the file finishes downloading

        with open(filename, 'rb') as file:
            await ctx.send(file=discord.File(file, filename=filename))
        await ctx.send(f"Download complete: {title}")

        os.remove(filename)  # Remove the local MP3 file
    except Exception as e:
        await ctx.send(f"Error during download: {e}")


# Add more commands and event handlers as needed

bot.run(token)