import os
import sys  
import random 
import csv
import re
from typing import Sequence, Optional
from dotenv import load_dotenv
import pysrt
import pvleopard
from praw import Reddit 
from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_audioclips
import tkinter as tk
from tkinter import scrolledtext as st
from google.cloud import texttospeech
from moviepy.config import change_settings
from logger import Logger
from reddit_utils import get_reddit_posts

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
load_dotenv()

logger = Logger() 

#https://console.picovoice.ai/   -> signup(free) get access code and save to ENV
leopard = pvleopard.create(access_key=os.getenv('LEOPARD_ACCESS_KEY'))

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')

SAVE_PATH = os.getenv('SAVE_PATH')
TEMP_PATH = os.getenv('TEMP_PATH')
OUTPUT_PATH = os.getenv('OUTPUT_PATH')

reddit = Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

subreddits = ['AmITheAsshole','stories']

posts = get_reddit_posts(reddit, subreddits, 5)

for p in posts:
    print(p.title)

# sub_reddit = sys.argv[1]
# count = int(sys.argv[2])



def merge_video_audio(video_file_path: str, audio_file_path: str) -> VideoFileClip:
    video_clip = VideoFileClip(video_file_path)
    audio_clip = AudioFileClip(audio_file_path)
    audio_length = audio_clip.duration
    video_clip = video_clip.subclip(0, audio_length)
    return video_clip.set_audio(audio_clip)

def save_merged_video(video_clip: VideoFileClip, output_name: str) -> None:
    video_clip.write_videofile(f'{OUTPUT_PATH}/{output_name}.mp4')
    video_clip.close()

def synthesize_text(text, output_name):
    client = texttospeech.TextToSpeechClient()

    input_text = texttospeech.SynthesisInput(text=text)

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


def create_subtitle_clips(subtitles, fontsize=60, font='ACNH', color='white', debug = False):
    subtitle_clips = []

    for subtitle in subtitles:
        start_time = time_to_seconds(subtitle.start)
        end_time = time_to_seconds(subtitle.end)
        duration = end_time - start_time

        text_clip = TextClip(subtitle.text, fontsize=fontsize, font=font, color=color, bg_color = 'none', method='caption',stroke_color='black', stroke_width=2, align='North').set_start(start_time).set_duration(duration)
        subtitle_x_position = 'center'
        subtitle_y_position = 1100

        text_position = (subtitle_x_position, subtitle_y_position)                    
        subtitle_clips.append(text_clip.set_position(text_position))
    return subtitle_clips
    

def RedditScraperEngine(sub_reddit:str, num_videos_to_make: int, target_num: int, i: int, videos_created: list) -> None:

    target_num = target_num
    videos_created = videos_created

    if not videos_created:
        #make list from csv
        with open('created_videos.csv', 'r') as file:
            reader = csv.reader(file)
            videos_created = reader.__next__()

    posts = get_reddit_posts(f'{sub_reddit}', num_videos_to_make)

    i = i
    for post in posts:
        if post.selftext and post.selftext != '' and len(post.selftext) <= 5000:
            
            output_name = re.sub('[^A-Za-z0-9]+', '', {post.title}.__str__())
            
            if output_name not in videos_created:
                
                if 'AITA' in post.title:
                    post.title = (post.title).replace('AITA', 'Am I the Asshole', 1)

                synthesize_text(post.title, f'{output_name}-title')
                synthesize_text(post.selftext, output_name)

                audio_length = AudioFileClip(f'{TEMP_PATH}/{output_name}.mp3').duration

                num_videos = int(audio_length // 60)
                num_videos = 1 if num_videos == 0 else num_videos
                
                video_length = float(audio_length / num_videos)

                video_index = random.randint(0, len(os.listdir(f'{SAVE_PATH}')) - 1)

                start_length = 0
                j = 0
                while j < num_videos:

                    video_clip = VideoFileClip(f'{SAVE_PATH}/{os.listdir(SAVE_PATH)[video_index]}')
                    sub_clip = AudioFileClip(f'{TEMP_PATH}/{output_name}.mp3').subclip(start_length - j, (video_length + start_length))
                    title_clip = AudioFileClip(f'{TEMP_PATH}/{output_name}-title.mp3')
                    
                    clip_list = []
                    clip_list.append(title_clip)
                    clip_list.append(sub_clip)
                    clip_with_title = concatenate_audioclips(clips=clip_list)

                    clip_with_title.write_audiofile(f'{TEMP_PATH}/{output_name}-{j}.mp3')

                    transcript, words = leopard.process_file(f'{TEMP_PATH}/{output_name}-{j}.mp3')               
                    
                    with open(f'{TEMP_PATH}/{output_name}-{j}.srt', 'w') as f:
                        f.write(to_srt(words))  #CREATES SRT FROM TEXT

                    subtitles = pysrt.open(f'{TEMP_PATH}/{output_name}-{j}.srt') #OPENS SRT FILE FOR READING
                    subtitle_clips = create_subtitle_clips(subtitles) #FORMS MP4 WITH SUBTITLES                            

                    video_clip = video_clip.subclip(start_length, (video_length + start_length) + title_clip.duration)
                    video_clip = video_clip.set_audio(clip_with_title)
            
                    start_length += video_length

                    subtitleFinal = CompositeVideoClip([video_clip] + subtitle_clips) #COMBINES SRT WITH MP4

                    subtitleFinal.write_videofile(f'{OUTPUT_PATH}/{output_name}-{j}.mp4')
                    
                    j += 1
                    videos_created.append(output_name)

                target_num += 1
            else:
                print("Post already used")
        else:
            print('No Post Body or Post is too large.')

    i+=1

    if (target_num != count):   
        RedditScraperEngine(sub_reddit, count+i, target_num, i, videos_created)

    with open('created_videos.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(videos_created)

    try:
        clear_temp_dir()
    except OSError:
        print('Could not clear temp.')


#RedditScraperEngine(sub_reddit, count, 0, 0, [])


# **************** TKINTER WINDOW SETUP / TKINTER METHODS *********************
# window = tk.Tk()
# window.title('Scraping Home')
# window.geometry('700x300')

# leftFrameMain = tk.Frame(window)
# leftFrameMain.pack(side='left', fill='both')

# rightFrameMain = tk.Frame(window)
# rightFrameMain.pack(side='right', fill='both')

# bottomFramMain = tk.Frame(window)
# bottomFramMain.pack(side= 'bottom', fill='y')

# videocounter = tk.Text(rightFrameMain, height=2, width=15, font=('arial 18'),)
# videocounter.pack()

# appLogger = st.ScrolledText(rightFrameMain, height=8, width=100)
# appLogger.pack()

# def updateLogger(message : str):
#     appLogger.insert(tk.INSERT, message + '\n')
#     appLogger.update()
#     print(message)
    
# def updateVideoCounter(numVids):
#     videocounter.delete("1.0", "end")
#     videocounter.insert('end', f'Videos created: {numVids}')
#     videocounter.update()

# def getWeb(url):
#     webbrowser.open_new(url)


# gitLink = tk.Label(leftFrameMain, text='GitHub Repo', font='Helvetica 15 underline', fg='light blue')
# gitLink.pack()
# gitLink.bind("<Button-1>", lambda e:(getWeb('https://github.com/dotlonely/reddit-scraper-to-tiktok')))

# redditLink = tk.Label(leftFrameMain, text='Reddit Page', font='Helvetica 15 underline', fg='light blue')
# redditLink.pack()
# redditLink.bind("<Button-2>", lambda e:(getWeb('https://www.reddit.com')))

# def newScraperWindow():
#     redditScrapingWindow = tk.Toplevel(window)
#     redditScrapingWindow.title('Reddit Scraper')
#     redditScrapingWindow.geometry('600x300')

#     subRedditLabel = tk.Label(redditScrapingWindow,text='Choose SubReddit:',font=(14)).grid(row=0)
#     subReddits = [
#         'AmITheAsshole',
#         'Money',
#         'LegalAdvice',
#         'Scams'
#                 ]

#     clicked = tk.StringVar() 
#     clicked.set( "AmITheAsshole") 

#     drop = tk.OptionMenu( redditScrapingWindow , clicked , *subReddits ) 
#     drop.grid(row=0,column=1)
#     drop.config(width=14)

#     redditPostNumSlider = tk.Scale(redditScrapingWindow, label='Number of Reddit posts to be scraped', orient='horizontal', length=400, width=45, from_=0, to=50, cursor='dot', activebackground='red') 
#     redditPostNumSlider.grid(row=20, column=0, columnspan=10)
    
#     vidCreateButton = tk.Button( redditScrapingWindow,command=(lambda:RedditScraperEngine(clicked.get(),redditPostNumSlider.get())), text="begin creating videos",height=1, width=15)
#     vidCreateButton.grid(row=0, column=10)


# #menu bar
# mainMenu = tk.Menu(window)
# appMenu = tk.Menu(mainMenu, tearoff=0)
# appMenu.add_command(label='Reddit', command=newScraperWindow)
# appMenu.add_separator()
# appMenu.add_command(label='Quit', command=window.quit)
# mainMenu.add_cascade(label='Reddit', menu=appMenu)
# window.config(menu=mainMenu)


# window.mainloop()

# ********************************* END OF WINDOW SETUP ***********************************************