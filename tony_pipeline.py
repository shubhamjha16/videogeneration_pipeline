"""
Presentation Pipeline — Slide-based video for non-Manim render mode.
Used when Director Agent picks render_mode="presentation".

Flow: narration text → split into scenes → TTS + slide image → compose with avatar → mp4
"""

import os
import re
import sys

from PIL import Image
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import loop as fx_loop

import config
from avatar_generator import generate_avatar_video
from slide_generator import generate_slide_image
from tts_generator import generate_audio

# Pillow 10+ compatibility
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

OUT_W, OUT_H = 854, 480


def _split_into_scenes(text: str) -> list[str]:
    """Split narration into 5–7 sentences for pacing."""
    sentences = re.split(r"\.\s+(?=[A-Z])", text.strip())
    cleaned = [
        s.strip() + ("" if s.strip().endswith(".") else ".")
        for s in sentences
        if len(s.strip()) > 10
    ]
    return cleaned[:7]


def run_tony_pipeline(
    narration: str,
    topic_name: str = "tony_ai_output",
    avatar_type: str = config.DEFAULT_AVATAR,
    output_dir: str = None,
    bg_image: str = None,
) -> str:
    """
    Generate a slide-based presentation video.

    Args:
        narration   : Full narration text (will be split into scenes)
        topic_name  : Used for output filenames and folder naming
        avatar_type : "logo" | "human" | "pro" | "user"
        output_dir  : Override output directory (default: output/job_<topic>)
        bg_image    : Optional background image path for slides

    Returns:
        Absolute path to the output mp4
    """
    job_dir = output_dir or os.path.join(
        "output", f"job_{topic_name.replace(' ', '_').lower()}"
    )
    os.makedirs(job_dir, exist_ok=True)

    script = _split_into_scenes(narration)
    print(f"  Presentation: {len(script)} scenes for '{topic_name}'")

    # Pre-render shared avatar once (logo/human reuse the same clip across scenes)
    shared_avatar = None
    if avatar_type in ("logo", "human"):
        ref_audio = generate_audio("Reference", 0, output_dir=job_dir)
        shared_avatar = generate_avatar_video(
            "", ref_audio, "shared", output_dir=job_dir, avatar_type=avatar_type
        )

    scenes = []
    for i, line in enumerate(script):
        audio = generate_audio(line, i + 1, output_dir=job_dir)
        slide = generate_slide_image(line, i + 1, output_dir=job_dir, bg_image=bg_image)
        avatar = shared_avatar or generate_avatar_video(
            line, audio, i + 1, output_dir=job_dir, avatar_type=avatar_type
        )
        scenes.append({
            "text":   line,
            "audio":  audio,
            "slide":  slide,
            "avatar": avatar,
            "layout": "side_avatar" if i % 2 == 0 else "ppt_presentation",
        })

    clips = []
    for scene in scenes:
        audio_clip  = AudioFileClip(scene["audio"])
        duration    = audio_clip.duration
        slide_clip  = ImageClip(scene["slide"]).set_duration(duration)
        avatar_clip = fx_loop(VideoFileClip(scene["avatar"]).without_audio(), duration=duration)

        if scene["layout"] == "side_avatar":
            sw      = int(OUT_W * 0.7)
            aw      = OUT_W - sw
            slide_s = slide_clip.resize(height=OUT_H)
            if slide_s.w > sw:
                slide_s = slide_s.resize(width=sw)
            bg    = ColorClip(size=(aw, OUT_H), color=(20, 20, 20)).set_duration(duration)
            av_s  = avatar_clip.resize(width=aw)
            frame = CompositeVideoClip([
                slide_s.set_position((0, 0)),
                bg.set_position((sw, 0)),
                av_s.set_position((sw, (OUT_H - av_s.h) // 2)),
            ], size=(OUT_W, OUT_H)).set_audio(audio_clip)
        else:
            slide_s = slide_clip.resize(height=OUT_H)
            av_s    = avatar_clip.resize(width=180)
            frame   = CompositeVideoClip([
                slide_s.set_position(("center", "center")),
                av_s.set_position((OUT_W - 200, OUT_H - 160)),
            ], size=(OUT_W, OUT_H)).set_audio(audio_clip)

        clips.append(frame)

    output_path = os.path.join(job_dir, "tony_ai_video.mp4")
    concatenate_videoclips(clips, method="compose").write_videofile(
        output_path, fps=24, codec="libx264"
    )
    print(f"  Presentation video saved: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) > 2:
        with open(sys.argv[1]) as f:
            text = f.read()
        topic       = sys.argv[2]
        avatar_type = sys.argv[3] if len(sys.argv) > 3 else "human"
        run_tony_pipeline(text, topic, avatar_type)
    else:
        sample = (
            "Newton's first law states that an object at rest stays at rest unless acted upon. "
            "The second law explains that force equals mass times acceleration. "
            "The third law says that for every action, there is an equal and opposite reaction."
        )
        run_tony_pipeline(sample, "Newton Laws Test")
