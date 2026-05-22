#!/usr/bin/env python3
"""
Generate Cycloid Video Through the Autonomous Pipeline
Uses the full Tony AI video generation pipeline (Director → Vision → Architect → Supervisor)
"""

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from autonomous_graph import app, TonyState

load_dotenv()

# Problem statement and content from the physics concept
topic = "Cycloid: A Point on a Rolling Wheel"

raw_input = """
# Cycloid: A Point on a Rolling Wheel

## The Problem
A point on the rim of a wheel (or ring) rolling without slipping traces a special curve called a **cycloid**.

The key constraint is the no-slip condition, which ties the translational speed of the center to the angular speed:

$$v = R\\omega$$

where:
- **v** = linear velocity of wheel center
- **R** = radius of wheel
- **ω** = angular velocity

## Parametric Equations

When a wheel of radius R rolls without slipping, a point that starts at the ground contact point traces a cycloid:

$$x(\\theta) = R(\\theta - \\sin\\theta)$$
$$y(\\theta) = R(1 - \\cos\\theta)$$

where **θ = ωt = (v/R)t** is the rotation angle at time t.

## Finding Velocity

To find the **vertical velocity**, differentiate y with respect to time:

$$\\dot{y} = \\frac{dy}{d\\theta} \\cdot \\frac{d\\theta}{dt} = R\\sin\\theta \\cdot \\omega$$

Substituting **ω = v/R**:

$$\\dot{y}(t) = v\\sin\\left(\\frac{vt}{R}\\right)$$

So the vertical velocity component is: **v sin(vt/R)**

## Finding Acceleration

To find the **vertical acceleration**, differentiate the velocity:

$$\\ddot{y} = \\frac{d}{dt}(v\\sin\\theta) = v\\cos\\theta \\cdot \\frac{d\\theta}{dt} = v\\cos\\theta \\cdot \\omega$$

Substituting **ω = v/R**:

$$\\ddot{y} = \\frac{v^2}{R}\\cos\\theta = \\frac{v^2}{R}\\cos\\left(\\frac{vt}{R}\\right)$$

So the vertical acceleration component is: **(v²/R) cos(vt/R)**

## Key Insight

The no-slip condition **v = Rω** fully determines the cycloid motion. This constraint completely specifies both the velocity and acceleration components.

## The Answer

For the vertical components of a point on the rim of a rolling wheel:

**Vertical Velocity**: $$v\\sin\\left(\\frac{vt}{R}\\right)$$

**Vertical Acceleration**: $$\\frac{v^2}{R}\\cos\\left(\\frac{vt}{R}\\right)$$

This is **Option B** from the original problem.
"""

# State for the pipeline
initial_state = {
    "topic": topic,
    "raw_input": raw_input,
    "source_type": "markdown",
    "video_type": "educational",
    "render_mode": "manim",
    "with_avatar": False,
    "use_elevenlabs": True,
    "avatar_type": "logo",
    "overrides": {
        "render_mode": "manim",
        "use_elevenlabs": True,
        "enable_ambient": True,
        "has_formula": True
    },
    "job_id": "cycloid_rolling_wheel",
    "attempt_count": 0,
    "ppt_attempt_count": 0,
    "no_vision": False,
    "research_count": 0,
}

print("=" * 80)
print("🎓 CYCLOID VIDEO GENERATION")
print("=" * 80)
print(f"📚 Topic: {topic}")
print(f"🎬 Mode: Manim Animation")
print(f"🎙️  Audio: ElevenLabs TTS")
print(f"📊 Job ID: {initial_state['job_id']}")
print("=" * 80)
print()

try:
    print("🚀 Starting autonomous pipeline...")
    print()

    final_state = app.invoke(initial_state)

    print()
    print("=" * 80)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 80)
    print()
    print(f"📁 Output Video Path: {final_state.get('output_path')}")

    if final_state.get('video_url'):
        print(f"🌐 Video URL: {final_state.get('video_url')}")

    if final_state.get('ledger'):
        print(f"\n💰 Cost Metrics:")
        ledger = final_state.get('ledger', {})
        print(f"   • Prompt Tokens: {ledger.get('prompt_tokens', 0)}")
        print(f"   • Completion Tokens: {ledger.get('completion_tokens', 0)}")
        print(f"   • Total Cost: ${ledger.get('total_cost', 0):.2f}")

    if final_state.get('rendering_errors'):
        print(f"\n⚠️  Errors: {final_state.get('rendering_errors')}")

except Exception as e:
    print()
    print("=" * 80)
    print(f"❌ PIPELINE FAILED: {e}")
    print("=" * 80)
    import traceback
    traceback.print_exc()
    sys.exit(1)
