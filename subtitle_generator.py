from moviepy.editor import TextClip, CompositeVideoClip, ColorClip
import numpy as np

def generate_kinetic_subtitles(video_clip, narration_text, audio_duration, style="insta_reels"):
    """
    Overlays kinetic 'Insta Reels' style subtitles on a video clip.
    Words are highlighted one-by-one in sync with the audio.
    """
    if style != "insta_reels":
        return video_clip

    print(f"🎬 [Subtitle Gen] Rendering kinetic subtitles for: {narration_text[:30]}...")
    
    words = narration_text.split()
    total_words = len(words)
    if total_words == 0:
        print("   ⚠️ No words in narration — skipping subtitles.")
        return video_clip

    # Heuristic: roughly equal time per word
    word_duration = audio_duration / total_words
    
    subtitle_clips = []
    
    # Text style settings
    font = 'Arial-Bold'
    font_size = 80
    base_color = 'white'
    highlight_color = 'yellow'
    stroke_color = 'black'
    stroke_width = 3

    # Display one word at a time, very large, in the center
    for i, word in enumerate(words):
        start_t = i * word_duration
        end_t = (i + 1) * word_duration
        
        # Current word (Yellow)
        word_clip = TextClip(
            word.upper(),
            fontsize=font_size,
            color=highlight_color,
            font=font,
            stroke_color=stroke_color,
            stroke_width=stroke_width,
            method='caption',
            size=(video_clip.w * 0.9, None)
        ).set_start(start_t).set_end(end_t).set_position(('center', 'center'))
        
        # Optional: add a slight scaling effect for 'pop'
        word_clip = word_clip.resize(lambda t: 1.0 + 0.1 * np.sin(t * 10))
        
        subtitle_clips.append(word_clip)

    return CompositeVideoClip([video_clip] + subtitle_clips)
