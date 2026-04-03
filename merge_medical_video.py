from moviepy.editor import VideoFileClip, AudioFileClip
import os

video_path = "media/videos/iliac_masterclass_manim/480p15/InternalIliacArteryMasterclass.mp4"
audio_path = "iliac_master_audio.mp3"
output_path = "iliac_artery_all_manim_final.mp4"

video = VideoFileClip(video_path)
audio = AudioFileClip(audio_path)

# Ensure video is at least as long as audio
if video.duration < audio.duration:
    video = video.loop(duration=audio.duration)

final_video = video.set_audio(audio)
final_video.write_videofile(output_path, fps=15, codec="libx264")
