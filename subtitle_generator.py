from moviepy.editor import CompositeVideoClip, ColorClip
import numpy as np

def generate_kinetic_subtitles(video_clip, narration_text, audio_duration, style="insta_reels", alignment_path=None):
    """
    Overlays kinetic 'Insta Reels' style subtitles on a video clip.
    Words are highlighted one-by-one in sync with the audio.
    Uses ElevenLabs alignments if alignment_path is provided or found.
    """
    if style != "insta_reels":
        return video_clip

    print(f"🎬 [Subtitle Gen] Rendering kinetic subtitles for: {narration_text[:30]}...")
    
    words = narration_text.split()
    if not words:
        print("   ⚠️ No words in narration — skipping subtitles.")
        return video_clip

    # 1. Attempt to load alignment data
    word_timestamps = [] # List of (word, start, end)
    
    import json, os
    alignment_data = None
    if alignment_path and os.path.exists(alignment_path):
        try:
            with open(alignment_path, "r") as f:
                alignment_data = json.load(f)
        except Exception as e:
            print(f"⚠️ [Subtitle Engine] Could not parse alignment JSON: {e}")
            pass

    if alignment_data and "characters" in alignment_data:
        print("   ✅ Using frame-perfect ElevenLabs alignments.")
        chars = alignment_data["characters"]
        starts = alignment_data["character_start_times_seconds"]
        ends = alignment_data["character_end_times_seconds"]
        
        # Aggregate characters into words
        current_word_chars = []
        current_word_start = None
        
        for i, char in enumerate(chars):
            # Start of a new word (non-space after space or at start)
            if char.strip():
                if current_word_start is None:
                    current_word_start = starts[i]
                current_word_chars.append(char)
            else:
                # Space encountered, end current word if any
                if current_word_chars:
                    full_w = "".join(current_word_chars)
                    word_timestamps.append((full_w, current_word_start, ends[i-1]))
                    current_word_chars = []
                    current_word_start = None
        
        # Append last word if pending
        if current_word_chars:
            word_timestamps.append(("".join(current_word_chars), current_word_start, ends[-1]))
            
    # 2. Fallback to Heuristic if no alignment or aggregation failed
    if not word_timestamps:
        print("   ⚠️ Falling back to punctuation-weighted heuristic timing.")
        weights = []
        for w in words:
            if w.endswith(('.', '!', '?')): weights.append(2.0)
            elif w.endswith(','): weights.append(1.5)
            else: weights.append(1.0)
        
        base_duration = audio_duration / sum(weights)
        curr = 0.0
        for i, w in enumerate(words):
            dur = base_duration * weights[i]
            word_timestamps.append((w, curr, curr + dur))
            curr += dur

    # 3. Create clips
    subtitle_clips = []
    from text_renderer import create_text_clip
    
    # Text style settings
    font_size = 90
    highlight_color = 'yellow'
    stroke_color = 'black'
    stroke_width = 4

    for word, start_t, end_t in word_timestamps:
        # Prevent zero duration clips
        duration = max(end_t - start_t, 0.05)
        
        word_clip = create_text_clip(
            word.upper(),
            fontsize=font_size,
            color=highlight_color,
            stroke_width=stroke_width,
            stroke_color=stroke_color,
            duration=duration
        ).set_start(start_t).set_end(end_t).set_position(('center', 'center'))
        
        subtitle_clips.append(word_clip)

    return CompositeVideoClip([video_clip] + subtitle_clips)
