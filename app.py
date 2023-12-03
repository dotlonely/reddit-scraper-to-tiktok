from praw import Reddit
from dotenv import load_dotenv
import pandas as pd
import pyttsx3
import os
import pyaudio
from pytube import YouTube
from moviepy.editor import VideoFileClip, AudioFileClip
from time import sleep
import re

load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')

reddit = Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

SAVE_PATH = 'C://Users//noahe//PythonProjects//reddit-scraper//static//downloads'
TEMP_PATH = 'C://Users//noahe//PythonProjects//reddit-scraper//static//temp'
OUTPUT_PATH = 'C://Users//noahe//PythonProjects//reddit-scraper//static//output'


# Downloads youtube video to save path
def download_youtube_video(link: str) -> None:
    try:
        yt = YouTube(link)
        print('Connected')
    except:
        print("Connection Error")
    
    yt.streams.filter(file_extension='mp4').first().download(f'{SAVE_PATH}')


def get_reddit_posts(subreddit: str):
    target = reddit.subreddit(subreddit)

    print(f'Display Name:{target.display_name}')

    return target.top("month")


def merge_video_audio(video_file_path: str, audio_file_path: str) -> VideoFileClip:
    video_clip = VideoFileClip(video_file_path)
    audio_clip = AudioFileClip(audio_file_path)
    audio_length = audio_clip.duration
    video_clip = video_clip.subclip(0, audio_length)
    return video_clip.set_audio(audio_clip)


def save_merged_video(video_clip: VideoFileClip, output_name: str) -> None:
    video_clip.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4')
    video_clip.close()


def init_tts_engine() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    return engine


engine = init_tts_engine()

posts = get_reddit_posts('AmITheAsshole')


for post in posts:
    if post.selftext and post.selftext != '':
        print(f'{post.title} : {post.selftext}')
        output_name = re.sub('[^A-Za-z0-9]+', '', {post.title}.__str__())
        engine.save_to_file(post.selftext, f'{TEMP_PATH}/{output_name}.mp3')
        engine.runAndWait()
        # The minecraft.mp4 is the name of a video I saved to my downloads path to use as the video base.
        output = merge_video_audio(f'{SAVE_PATH}/minecraft.mp4', f'{TEMP_PATH}/{output_name}.mp3')
        save_merged_video(output, output_name=output_name)
    else:
        print('No Post Body')




