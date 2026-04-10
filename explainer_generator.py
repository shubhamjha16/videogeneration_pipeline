import os
import subprocess
import config

def generate_explainer_video(scenes: list, output_dir: str, topic: str) -> str:
    """
    Higgsfield-style: Stitches narration with B-roll/generative metaphors.
    For now, creates a visual 'prompt card' video for each scene.
    """
    from moviepy.editor import TextClip, ColorClip, concatenate_videoclips, AudioFileClip, CompositeVideoClip
    from tts_generator import generate_audio
    
    print(f"🎬 [Explainer Gen] Generating visual metaphors for: {topic}")
    
    try:
        clips = []
        for i, scene in enumerate(scenes):
            if scene["visual_type"] == "b_roll_clip":
                prompt = scene["visual_data"].get("prompt", "Cinematic visual")
                metaphor = scene["visual_data"].get("metaphor", "")
                display_text = f"METAPHOR: {metaphor}\n\nPROMPT: {prompt}"
            else:
                display_text = f"SCENE {i+1}\n\n{scene['narration_text'][:50]}..."

            # Generate audio for this segment to get duration
            seg_audio_path = generate_audio(scene["narration_text"], f"explainer_{i}", output_dir=output_dir)
            seg_audio = AudioFileClip(seg_audio_path)
            dur = seg_audio.duration
            
            # Create a visual representing the prompt
            bg = ColorClip(size=(1280, 720), color=(20, 20, 30), duration=dur)
            txt = TextClip(
                display_text, 
                fontsize=50, color='white', font='Arial',
                method='caption', size=(1000, 600)
            ).set_duration(dur).set_position('center')
            
            clip = CompositeVideoClip([bg, txt]).set_audio(seg_audio)
            clips.append(clip)

        # Performance: Use 'chain' method since all clips are identical resolution
        final_video = concatenate_videoclips(clips, method="chain")
        output_path = os.path.join(output_dir, f"{topic.lower().replace(' ', '_')}_explainer.mp4")
        final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
        
        # Cleanup clips list
        final_video.close()
        for c in clips:
            c.close()
            
    except Exception as e:
        print(f"   ❌ Explainer Gen Error: {e}")
        raise e
    
    return output_path
