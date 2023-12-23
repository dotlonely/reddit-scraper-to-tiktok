import os
import sys  
import random 
import csv
import re
from dotenv import load_dotenv
import pysrt
import pvleopard
from praw import Reddit 
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip, concatenate_audioclips
import tkinter as tk
from tkinter import scrolledtext as st
from moviepy.config import change_settings
from logger import Logger
from reddit_utils import get_reddit_posts
from video_utils import  synthesize_text, to_srt, clear_dir, create_subtitle_clips

change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})
load_dotenv()

logger = Logger() 


CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
USER_AGENT = os.getenv('USER_AGENT')

SAVE_PATH = os.getenv('SAVE_PATH')
TEMP_PATH = os.getenv('TEMP_PATH')
OUTPUT_PATH = os.getenv('OUTPUT_PATH')


#https://console.picovoice.ai/   -> signup(free) get access code and save to ENV
leopard = pvleopard.create(access_key=os.getenv('LEOPARD_ACCESS_KEY'))


reddit = Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT)

subreddits = ['AmITheAsshole','stories']


count = int(sys.argv[1])


def scrape_reddit(sub_reddits:str, num_videos_to_make: int, target_num: int, i: int, videos_created: list) -> None:

    target_num = target_num
    videos_created = videos_created

    if not videos_created:
        with open('created_videos.csv', 'r') as file:
            reader = csv.reader(file)
            videos_created = reader.__next__()

    posts = get_reddit_posts(reddit, subreddits, 5)

    i = i
    for post in posts:
        if post.selftext and post.selftext != '' and len(post.selftext) <= 5000:
            
            output_name = re.sub('[^A-Za-z0-9]+', '', {post.title}.__str__())
            
            if output_name not in videos_created:
                
                if 'AITA' in post.title:
                    post.title = (post.title).replace('AITA', 'Am I the Asshole', 1)

                synthesize_text(post.title, TEMP_PATH, f'{output_name}-title')
                synthesize_text(post.selftext,TEMP_PATH, output_name)

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
        scrape_reddit(subreddits, count+i, target_num, i, videos_created)

    with open('created_videos.csv', 'w') as file:
        writer = csv.writer(file)
        writer.writerow(videos_created)

    try:
        clear_dir(TEMP_PATH)
    except OSError:
        print('Could not clear directory.')


scrape_reddit(subreddits, count, 0, 0, [])


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