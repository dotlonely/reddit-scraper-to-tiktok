from praw import Reddit
from dotenv import load_dotenv
import pandas as pd
import pyttsx3
import os
import pyaudio
from pytube import YouTube
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from time import sleep
import re
import pvleopard
import time
from argparse import ArgumentParser
from typing import *
import pysrt
import datetime

load_dotenv()

#https://console.picovoice.ai/   -> signup(free) get access code and save to ENV
leopard = pvleopard.create(access_key=os.getenv('LEOPARD_ACCESS_KEY'))

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')

SAVE_PATH = os.getenv('SAVE_PATH')
TEMP_PATH = os.getenv('TEMP_PATH')
OUTPUT_PATH = os.getenv('OUTPUT_PATH')

reddit = Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

class logger:
    nowTime = datetime.datetime.now()
    audioVideoMerge = f'LOGGER: {nowTime} : MERGING AUDIO WITH VIDEO'
    savingMergedVideo = f'LOGGER: {nowTime} : SAVING MERGED VIDEO'
    toSRT = f'LOGGER: {nowTime} : CONVERTING TEXT TO SRT'
    subtitleCreate = f'LOGGER: {nowTime} : CREATING SUBTITLES'
    subtitleVieoMerge = f'LOGGER: {nowTime} : MERGING VIDEO WITH SUBTITLES'

log = logger()

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
    print(log.audioVideoMerge)
    video_clip = VideoFileClip(video_file_path)
    audio_clip = AudioFileClip(audio_file_path)
    audio_length = audio_clip.duration
    video_clip = video_clip.subclip(0, audio_length)
    return video_clip.set_audio(audio_clip)


def save_merged_video(video_clip: VideoFileClip, output_name: str) -> None:
    print(log.savingMergedVideo)
    video_clip.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4')
    video_clip.close()
    

def init_tts_engine() -> pyttsx3.Engine:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[1].id)
    return engine

def second_to_timecode(x: float) -> str:
    hour, x = divmod(x, 3600)
    minute, x = divmod(x, 60)
    second, x = divmod(x, 1)
    millisecond = int(x * 1000.)

    return '%.2d:%.2d:%.2d,%.3d' % (hour, minute, second, millisecond)

def to_srt(
        words: Sequence[pvleopard.Leopard.Word],
        endpoint_sec: float = 1.,
        length_limit: Optional[int] = 16) -> str:
    print(log.toSRT)
    def _helper(end: int, ) -> None:
        lines.append("%d" % section)
        lines.append(
            "%s --> %s" %
            (
                second_to_timecode(words[start].start_sec),
                second_to_timecode(words[end].end_sec)
            )
        )
        lines.append(' '.join(x.word for x in words[start:(end + 1)]))
        lines.append('')

    lines = list()
    section = 0
    start = 0
    for k in range(1, len(words)):
        if ((words[k].start_sec - words[k - 1].end_sec) >= endpoint_sec) or \
                (length_limit is not None and (k - start) >= length_limit):
            _helper(k - 1)
            start = k
            section += 1
    _helper(len(words) - 1)
    
    return '\n'.join(lines)


def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000


def create_subtitle_clips(subtitles, fontsize=18, font='Arial', color='white', debug = False):
    print(log.subtitleCreate)
    subtitle_clips = []

    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time

        text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, bg_color = 'none', method='caption', stroke_width=3.5, align='North').set_start(start_time).set_duration(duration)
        subtitle_x_position = 'center'
        subtitle_y_position = 'center' 

        text_position = (subtitle_x_position, subtitle_y_position)                    
        subtitle_clips.append(text_clip.set_position(text_position))
    return subtitle_clips

videoCounter = 0
posts = get_reddit_posts('AmITheAsshole')
engine = init_tts_engine()
for post in posts:
    if post.selftext and post.selftext != '':
        videoCounter = videoCounter + 1
        #print(f'{post.title} : {post.selftext}') #COMMENTED TO SAVE RUNTIME
        
        output_name = re.sub('[^A-Za-z0-9]+', '', {post.title}.__str__())
        engine.save_to_file(post.selftext, f'{TEMP_PATH}/{output_name}.mp3')
        
        # The minecraft.mp4 is the name of a video I saved to my downloads path to use as the video base.
        audioVideoOutput = merge_video_audio(f'{SAVE_PATH}/minecraft.mp4','/Users/alexbrady/Library/Mobile Documents/com~apple~CloudDocs/RedditScrape Repo/reddit-scraper-to-tiktok/static/downloads/AITAfor.mp3')
        
        transcript, words = leopard.process_file('/Users/alexbrady/Library/Mobile Documents/com~apple~CloudDocs/RedditScrape Repo/reddit-scraper-to-tiktok/static/downloads/AITAfor.mp3')
        
        with open(f'{TEMP_PATH}/{output_name}.srt', 'w') as f:
            f.write(to_srt(words))  #CREATES SRT FROM TEXT
        
        subtitles = pysrt.open(f'{TEMP_PATH}/{output_name}.srt') #OPENS SRT FILE FOR READING
        subtitle_clips = create_subtitle_clips(subtitles) #FORMS MP4 WITH SUBTITLES                            
        
        subtitleFinal = CompositeVideoClip([audioVideoOutput] + subtitle_clips) #COMBINES SRT WITH MP4
        subtitleFinal.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4') #WRITES AND SAVES TO OUTPUTPATH
        #save_merged_video(subtitleFinal, output_name=output_name)
        
        if (videoCounter == 1):
            print(f'{videoCounter} VIDEO MADE')
        else:
            print(f'{videoCounter} VIDEOS MADE')
    
    else:
        print('No Post Body')





