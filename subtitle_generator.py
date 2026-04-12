from moviepy.editor import CompositeVideoClip, ColorClip
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

    # Heuristic: roughly equal time per word, weighted for punctuation pauses
    weights = []
    for w in words:
        if w.endswith(('.', '!', '?')): weights.append(2.0)
        elif w.endswith(','): weights.append(1.5)
        else: weights.append(1.0)
    
    total_weight = sum(weights)
    base_duration = audio_duration / total_weight
    
    subtitle_clips = []
    current_time = 0.0
    
    from text_renderer import create_text_clip
    
    # Text style settings
    font_size = 80
    base_color = 'white'
    highlight_color = 'yellow'
    stroke_color = 'black'
    stroke_width = 3

    # Display one word at a time, very large, in the center
    for i, word in enumerate(words):
        w_dur = base_duration * weights[i]
        start_t = current_time
        end_t = current_time + w_dur
        current_time = end_t
        
        # Use PIL-based text renderer instead of TextClip
        word_clip = create_text_clip(
            word.upper(),
            fontsize=font_size,
            color=highlight_color,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            duration=end_t - start_t
        ).set_start(start_t).set_end(end_t).set_position(('center', 'center'))
        
        # Upgrade: removed time-based lambda resize for MoviePy 1.0.3 compatibility
        subtitle_clips.append(word_clip)

    return CompositeVideoClip([video_clip] + subtitle_clips)
