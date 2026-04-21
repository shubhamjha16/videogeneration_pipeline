from moviepy.editor import CompositeVideoClip, ColorClip
import numpy as np
import json
import os

def generate_kinetic_subtitles(video_clip, narration_text, audio_duration, style="insta_reels", alignment_path=None, audio_path=None):
    """
    Overlays kinetic 'Insta Reels' style subtitles on a video clip.
    Words are highlighted one-by-one in sync with the audio.
    
    Tiers of Alignment:
    1. ElevenLabs JSON (highest precision)
    2. Whisper Local Alignment (high precision, zero cost)
    3. Heuristic (punctuation-weighted, fallback)
    """
    if style != "insta_reels":
        return video_clip

    print(f"🎬 [Subtitle Gen] Rendering kinetic subtitles for: {narration_text[:30]}...")
    
    words = narration_text.split()
    if not words:
        print("   ⚠️ No words in narration — skipping subtitles.")
        return video_clip

    # 1. Attempt to load Tier 1: ElevenLabs alignment data
    word_timestamps = [] # List of (word, start, end)
    
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
            if char.strip():
                if current_word_start is None:
                    current_word_start = starts[i]
                current_word_chars.append(char)
            else:
                if current_word_chars:
                    full_w = "".join(current_word_chars)
                    actual_end = ends[i-1] if i > 0 else ends[0]
                    word_timestamps.append((full_w, current_word_start, actual_end))
                    current_word_chars = []
                    current_word_start = None

        if current_word_chars:
            word_timestamps.append(("".join(current_word_chars), current_word_start, ends[-1]))
            
    # 2. Tier 2: Whisper Local Aligner (Zero-Cost Industrial Alignment)
    if not word_timestamps and audio_path and os.path.exists(audio_path):
        print("   🤖 [Subtitles] ElevenLabs missing — triggering Whisper Local Aligner...")
        try:
            from whisper_aligner import get_word_timestamps
            whisper_words = get_word_timestamps(audio_path)
            
            if whisper_words:
                print(f"   ✅ Whisper aligned {len(whisper_words)} words.")
                # Map whisper dicts to the (word, start, end) format the renderer expects
                for w in whisper_words:
                    word_timestamps.append((w["word"], w["start"], w["end"]))
        except Exception as e:
            print(f"   ⚠️ Whisper Alignment failed: {e}")

    # 3. Tier 3: Fallback to Heuristic if no alignment or aggregation failed
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

    # 4. Create clips
    subtitle_clips = []
    from text_renderer import create_text_clip
    
    # Text style settings
    font_size = 90
    highlight_color = 'yellow'
    stroke_color = 'black'
    stroke_width = 4

    for word, start_t, end_t in word_timestamps:
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

    composite = CompositeVideoClip([video_clip] + subtitle_clips)
    composite.fps = getattr(video_clip, 'fps', None) or 24
    return composite
