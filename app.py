from praw import Reddit
from dotenv import load_dotenv
import pandas as pd
import os
import pyaudio
from pytube import YouTube
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip
from time import sleep
import re
import pvleopard
from time import sleep
from argparse import ArgumentParser
from typing import *
import pysrt
import datetime
import tkinter as tk
import webbrowser
from tkinter import scrolledtext as st
from tiktok_uploader.upload import upload_video, upload_videos
from tiktok_uploader.auth import AuthBackend
from google.cloud import texttospeech
from moviepy.config import change_settings


change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

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
    buildingVideo = f'Logger: {nowTime} : BUILDING VIDEO'
    writingVideo = f'Logger: {nowTime} : WRITING VIDEO'

log = logger()

# Downloads youtube video to save path
def download_youtube_video(link: str) -> None:
    try:
        yt = YouTube(link)
        print('Connected')
    except:
        print("Connection Error")
    
    yt.streams.filter(file_extension='mp4').first().download(f'{SAVE_PATH}')

def get_reddit_posts(subreddit: str, sliderNum):
    target = reddit.subreddit(subreddit)
    print(f'Display Name:{target.display_name}')
    return target.top(limit=sliderNum)

def merge_video_audio(video_file_path: str, audio_file_path: str) -> VideoFileClip:
    updateLogger(log.audioVideoMerge)
    video_clip = VideoFileClip(video_file_path)
    audio_clip = AudioFileClip(audio_file_path)
    audio_length = audio_clip.duration
    video_clip = video_clip.subclip(0, audio_length)
    return video_clip.set_audio(audio_clip)

def save_merged_video(video_clip: VideoFileClip, output_name: str) -> None:
    updateLogger(log.savingMergedVideo)
    video_clip.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4')
    video_clip.close()
    


def synthesize_text(text, output_name):
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Standard-E",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )

    # The response's audio_content is binary.
    with open(f"{TEMP_PATH}/{output_name}.mp3", "wb") as out:
        out.write(response.audio_content)

def second_to_timecode(x: float) -> str:
    hour, x = divmod(x, 3600)
    minute, x = divmod(x, 60)
    second, x = divmod(x, 1)
    millisecond = int(x * 1000.)

    return '%.2d:%.2d:%.2d,%.3d' % (hour, minute, second, millisecond)

def to_srt(
        words: Sequence[pvleopard.Leopard.Word],
        endpoint_sec: float = 1.,
        length_limit: Optional[int] = 1) -> str:
    updateLogger(log.toSRT)
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


def clear_temp_dir():
    for file in os.listdir(f'{TEMP_PATH}'):
        os.remove(f'{TEMP_PATH}/{file}')


def time_to_seconds(time_obj):
    return time_obj.hours * 3600 + time_obj.minutes * 60 + time_obj.seconds + time_obj.milliseconds / 1000


def create_subtitle_clips(subtitles, fontsize=28, font='Consolas', color='white', debug = False):
    updateLogger(log.subtitleCreate)
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

def RedditScraperEngine(selectedSubReddit, sliderNum):
    videoCounter = 0
    posts = get_reddit_posts(f'{selectedSubReddit}', sliderNum)
    for post in posts:
        if post.selftext and post.selftext != '' and len(post.selftext) <= 5000:
            videoCounter = videoCounter + 1
            
            output_name = re.sub('[^A-Za-z0-9]+', '', {post.title}.__str__())
            
            if f'{output_name}.mp4' not in os.listdir(f'{OUTPUT_PATH}'):

                synthesize_text(post.selftext, output_name)

                # The minecraft.mp4 is the name of a video I saved to my downloads path to use as the video base.
                audioVideoOutput = merge_video_audio(f'{SAVE_PATH}/minecraft.mp4',f'{TEMP_PATH}/{output_name}.mp3')
                
                transcript, words = leopard.process_file(f'{TEMP_PATH}/{output_name}.mp3')
                
                with open(f'{TEMP_PATH}/{output_name}.srt', 'w') as f:
                    f.write(to_srt(words))  #CREATES SRT FROM TEXT
                
                subtitles = pysrt.open(f'{TEMP_PATH}/{output_name}.srt') #OPENS SRT FILE FOR READING
                subtitle_clips = create_subtitle_clips(subtitles) #FORMS MP4 WITH SUBTITLES                            
                
                updateLogger(log.buildingVideo)
                subtitleFinal = CompositeVideoClip([audioVideoOutput] + subtitle_clips) #COMBINES SRT WITH MP4
                
                updateLogger(log.writingVideo)
                subtitleFinal.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4') #WRITES AND SAVES TO OUTPUTPATH
                #save_merged_video(subtitleFinal, output_name=output_name)
                
                updateVideoCounter(videoCounter)
                
                clear_temp_dir()

                if (videoCounter == 1):
                    print(f'{videoCounter} VIDEO MADE')
                else:
                    print(f'{videoCounter} VIDEOS MADE')
            
            with open(f'{TEMP_PATH}/{output_name}.srt', 'w') as f:
                f.write(to_srt(words))  #CREATES SRT FROM TEXT
            
            subtitles = pysrt.open(f'{TEMP_PATH}/{output_name}.srt') #OPENS SRT FILE FOR READING
            subtitle_clips = create_subtitle_clips(subtitles) #FORMS MP4 WITH SUBTITLES                            
            
            updateLogger(log.buildingVideo)
            subtitleFinal = CompositeVideoClip([audioVideoOutput] + subtitle_clips) #COMBINES SRT WITH MP4
            
            updateLogger(log.writingVideo)
            subtitleFinal.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4') #WRITES AND SAVES TO OUTPUT PATH
            #save_merged_video(subtitleFinal, output_name=output_name)
            postTikTik(f'{OUTPUT_PATH}/{output_name}.mp4', 'test', '/Users/alexbrady/Library/Mobile Documents/com~apple~CloudDocs/RedditScrape Repo/reddit-scraper-to-tiktok/tiktokcookies.txt')
            updateVideoCounter(videoCounter)
            if (videoCounter == 1):
                print(f'{videoCounter} VIDEO MADE')
            else:
                print(f'{videoCounter} VIDEOS MADE')
        

        else:
            print('No Post Body or Post is too large.')


#methods to take mp4 compiled videos and post to respective platforms UNUSED
def postTikTik(videoFile : CompositeVideoClip, description : str, cookies):
    upload_video(videoFile, description, cookies)
def postFacebook():
    print()
def postYoutube():
    print()

# **************** TKINTER WINDOW SETUP / TKINTER METHODS *********************
window = tk.Tk()
window.title('Scraping Home')
window.geometry('700x300')

leftFrameMain = tk.Frame(window)
leftFrameMain.pack(side='left', fill='both')

rightFrameMain = tk.Frame(window)
rightFrameMain.pack(side='right', fill='both')

bottomFramMain = tk.Frame(window)
bottomFramMain.pack(side= 'bottom', fill='y')

videocounter = tk.Text(rightFrameMain, height=2, width=15, font=('arial 18'),)
videocounter.pack()

appLogger = st.ScrolledText(rightFrameMain, height=8, width=100)
appLogger.pack()

def updateLogger(message : str):
    appLogger.insert(tk.INSERT, message + '\n')
    appLogger.update()
    print(message)
    
def updateVideoCounter(numVids):
    videocounter.delete("1.0", "end")
    videocounter.insert('end', f'Videos created: {numVids}')
    videocounter.update()

def getWeb(url):
    webbrowser.open_new(url)


gitLink = tk.Label(leftFrameMain, text='GitHub Repo', font='Helvetica 15 underline', fg='light blue')
gitLink.pack()
gitLink.bind("<Button-1>", lambda e:(getWeb('https://github.com/dotlonely/reddit-scraper-to-tiktok')))

redditLink = tk.Label(leftFrameMain, text='Reddit Page', font='Helvetica 15 underline', fg='light blue')
redditLink.pack()
redditLink.bind("<Button-2>", lambda e:(getWeb('https://www.reddit.com')))

def newTikTokWindow():
    tiktokWindow = tk.Toplevel(window)
    tiktokWindow.title('TikTok from Reddit')
    tiktokWindow.geometry('600x300')

    subRedditLabel = tk.Label(tiktokWindow,text='Choose SubReddit:',font=(14)).grid(row=0)
    subReddits = [
        'AmITheAsshole',
        'Money',
        'LegalAdvice',
        'Scams'
                ]

    clicked = tk.StringVar() 
    clicked.set( "AmITheAsshole") 

    drop = tk.OptionMenu( tiktokWindow , clicked , *subReddits ) 
    drop.grid(row=0,column=1)
    drop.config(width=14)

    redditPostNumSlider = tk.Scale(tiktokWindow, label='Number of Reddit posts to be scraped', orient='horizontal', length=400, width=45, from_=0, to=50, cursor='dot', activebackground='red') 
    redditPostNumSlider.grid(row=20, column=0, columnspan=10)
    
    vidCreateButton = tk.Button( tiktokWindow,command=(lambda:RedditScraperEngine(clicked.get(),redditPostNumSlider.get())), text="begin creating videos",height=1, width=15)
    vidCreateButton.grid(row=0, column=10)

    postTikTok = tk.IntVar()
    tiktokPostCheckBox = tk.Checkbutton(tiktokWindow, text='Post to TikTok', variable=postTikTok)
    tiktokPostCheckBox.grid(row=3, column=10)
    if postTikTok.get():
        print() #will post to tiktok
    else:
        print() #will not post to tiktok
    
    savemp4 = tk.IntVar()
    savemp4CheckBox = tk.Checkbutton(tiktokWindow, text='Save mp4 file(s)', variable=savemp4)
    savemp4CheckBox.grid(row=4, column=10)
    if savemp4.get():
        print() #call method to save to computer hard drive ... use save_merged_video(video, hardDrive)
    else:
        print() # sends boolean to delete_video method in the engine loop

def newFacebookWindow():
    facebookWindow = tk.Toplevel(window)
    facebookWindow.geometry('600x300')
    facebookWindow.title('Facebook from Reddit')
    facebookWindow.config(bg='RoyalBlue1')
    
    subRedditLabel = tk.Label(facebookWindow,text='Choose SubReddit:',font=(14)).grid(row=0)
    subReddits = [
        'AmITheAsshole',
        'Money',
        'LegalAdvice',
        'Scams'
                ]

    clicked = tk.StringVar() 
    clicked.set( "AmITheAsshole") 

    drop = tk.OptionMenu( facebookWindow , clicked , *subReddits ) 
    drop.grid(row=0,column=1)
    drop.config(width=14)

    redditPostNumSlider = tk.Scale(facebookWindow, label='Number of Reddit posts to be scraped', orient='horizontal', length=400, width=45, from_=0, to=50, cursor='dot', activebackground='red') 
    redditPostNumSlider.grid(row=20, column=0, columnspan=10)
    
    vidCreateButton = tk.Button( facebookWindow, text="begin creating videos",height=1, width=15)
    vidCreateButton.grid(row=0, column=10)

    postTikTok = tk.IntVar()
    facebookPostCheckBox = tk.Checkbutton(facebookWindow, text='Post to Facebook', variable=postTikTok)
    facebookPostCheckBox.grid(row=3, column=10)
    if postTikTok.get():
        print() #will post to tiktok
    else:
        print() #will not post to tiktok
    
    savemp4 = tk.IntVar()
    savemp4CheckBox = tk.Checkbutton(facebookWindow, text='Save mp4 file(s)', variable=savemp4)
    savemp4CheckBox.grid(row=4, column=10)
    if savemp4.get():
        print() #call method to save to computer hard drive ... use save_merged_video(video, hardDrive)
    else:
        print() # sends boolean to delete_video method in the engine loop
    
def newYoutubeWindow():
    youtubeWindow = tk.Toplevel(window)
    youtubeWindow.geometry('600x300')
    youtubeWindow.title('Youtube from Reddit')
    
    subRedditLabel = tk.Label(youtubeWindow,text='Choose SubReddit:',font=(14)).grid(row=0)
    subReddits = [
        'AmITheAsshole',
        'Money',
        'LegalAdvice',
        'Scams'
                ]

    clicked = tk.StringVar() 
    clicked.set( "AmITheAsshole") 

    drop = tk.OptionMenu( youtubeWindow , clicked , *subReddits ) 
    drop.grid(row=0,column=1)
    drop.config(width=14)

    redditPostNumSlider = tk.Scale(youtubeWindow, label='Number of Reddit posts to be scraped', orient='horizontal', length=400, width=45, from_=0, to=50, cursor='dot', activebackground='red') 
    redditPostNumSlider.grid(row=20, column=0, columnspan=10)
    
    vidCreateButton = tk.Button( youtubeWindow, text="begin creating videos",height=1, width=15)
    vidCreateButton.grid(row=0, column=10)

    postTikTok = tk.IntVar()
    youtubePostCheckBox = tk.Checkbutton(youtubeWindow, text='Post to Youtube', variable=postTikTok)
    youtubePostCheckBox.grid(row=3, column=10)
    if postTikTok.get():
        print() #will post to tiktok
    else:
        print() #will not post to tiktok
    
    savemp4 = tk.IntVar()
    savemp4CheckBox = tk.Checkbutton(youtubeWindow, text='Save mp4 file(s)', variable=savemp4)
    savemp4CheckBox.grid(row=4, column=10)
    if savemp4.get():
        print() #call method to save to computer hard drive ... use save_merged_video(video, hardDrive)
    else:
        print() # sends boolean to delete_video method in the engine loop

#menu bar
mainMenu = tk.Menu(window)
appMenu = tk.Menu(mainMenu, tearoff=0)
appMenu.add_command(label='TikTok', command=newTikTokWindow)
appMenu.add_command(label='Facebook', command=newFacebookWindow)
appMenu.add_command(label='Youtube', command=newYoutubeWindow)
appMenu.add_separator()
appMenu.add_command(label='Quit', command=window.quit)
mainMenu.add_cascade(label='Reddit', menu=appMenu)
window.config(menu=mainMenu)


window.mainloop()

# ********************************* END OF WINDOW SETUP ***********************************************