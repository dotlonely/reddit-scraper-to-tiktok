from moviepy.editor import VideoFileClip, AudioFileClip, TextClip, CompositeVideoClip, concatenate_audioclips

def merge_video_audio(video_file_path: str, audio_file_path: str) -> VideoFileClip:
    video_clip = VideoFileClip(video_file_path)
    audio_clip = AudioFileClip(audio_file_path)
    audio_length = audio_clip.duration
    video_clip = video_clip.subclip(0, audio_length)
    return video_clip.set_audio(audio_clip)

def save_merged_video(video_clip: VideoFileClip, path: str, output_name: str) -> None:
    video_clip.write_videofile(f'{path}/{output_name}.mp4')
    video_clip.close()