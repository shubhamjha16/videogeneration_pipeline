import os
import sys
import shutil
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autonomous_graph import app

def run_cycloid_mcq():
    topic = "Vertical Components of Rim Point on a Rolling Wheel"
    
    # Standard solutionV2 format from the user request
    solution_v2 = [
        {
            "title": "Concept Explanation",
            "description": "A point on the rim of a wheel (or ring) rolling without slipping traces a **cycloid**. The key constraint is the no-slip condition, which ties the translational speed of the center to the angular speed: $v=R\\omega$.\n\nTo find the velocity and acceleration of the rim point, it’s convenient to write its position parametrically in terms of the rotation angle $\\theta=\\omega t=\\frac{v}{R}t$, then differentiate. The answer choices indicate we are looking at the **vertical components** (since they involve only $\\sin$ or $\\cos$ of $\\theta$, not the horizontal term $1-\\cos\\theta$ that appears in $v_x$)."
        },
        {
            "title": "Step-by-Step Solution",
            "description": "1. Relate rolling speed and angular speed:\n\n$$\n\\omega=\\frac{v}{R},\\qquad \\theta=\\omega t=\\frac{v}{R}t.\n$$\n\n2. Use the standard cycloid for a point that starts at the ground contact point (origin) at $t=0$:\n\n$$\n\\begin{aligned}\nx(\\theta) &= R(\\theta-\\sin\\theta),\\\\\ny(\\theta) &= R(1-\\cos\\theta).\n\\end{aligned}\n$$\n\n3. Differentiate $y(t)$ to get the vertical velocity:\n\n$$\n\\begin{aligned}\n\\dot y &= \\frac{dy}{d\\theta}\\frac{d\\theta}{dt}\n= \\left(R\\sin\\theta\\right)\\omega\n= R\\omega\\sin\\theta\n= v\\sin\\theta.\n\\end{aligned}\n$$\n\nSo,\n\n$$\n\\dot y(t)=v\\sin\\left(\\frac{vt}{R}\\right).\n$$\n\n4. Differentiate again to get the vertical acceleration:\n\n$$\n\\begin{aligned}\n\\ddot y &= \\frac{d}{dt}\\left(v\\sin\\theta\\right)\n= v\\cos\\theta\\,\\dot\\theta\n= v\\cos\\theta\\,\\omega\n= v\\cos\\theta\\,\\frac{v}{R}\n= \\frac{v^2}{R}\\cos\\theta.\n\\end{aligned}\n$$\n\nThus,\n\n$$\n\\ddot y(t)=\\frac{v^2}{R}\\cos\\left(\\frac{vt}{R}\\right).\n$$"
        },
        {
            "title": "Option Analysis",
            "description": "### Option A) $v\\sin\\left(\\frac{vt}{R}\\right),\\ \\frac{v^2}{R}\\sin\\left(\\frac{vt}{R}\\right)$\nThe velocity part matches the vertical velocity $v_y=v\\sin\\theta$. However, the vertical acceleration should be proportional to $\\cos\\theta$, not $\\sin\\theta$, so the second expression is incorrect.\n\n### Option B) $v\\sin\\left(\\frac{vt}{R}\\right),\\ \\frac{v^2}{R}\\cos\\left(\\frac{vt}{R}\\right)$\nThis matches the vertical velocity $v_y=v\\sin\\theta$ and vertical acceleration $a_y=\\frac{v^2}{R}\\cos\\theta$ obtained by differentiating the cycloid’s $y$-coordinate with $\\theta=\\frac{vt}{R}$.\n\n### Option C) $v\\cos\\left(\\frac{vt}{R}\\right),\\ \\frac{v^2}{R}\\sin\\left(\\frac{vt}{R}\\right)$\nThis swaps the trigonometric dependence: the vertical velocity is not $v\\cos\\theta$ for a cycloid starting at the origin. Also the acceleration term should be $\\cos\\theta$ (for the vertical component), not $\\sin\\theta$.\n\n### Option D) Cannot be determined\nWith the no-slip condition and the specified initial condition (point at the origin at $t=0$), the cycloid is fully determined, so both the velocity and acceleration components can be determined."
        },
        {
            "title": "Final Answer",
            "description": "**Option B**: $\\displaystyle v\\sin\\left(\\frac{vt}{R}\\right),\\ \\frac{v^2}{R}\\cos\\left(\\frac{vt}{R}\\right)$."
        },
        {
            "title": "Citations",
            "description": "- **University Physics with Modern Physics** — Hugh D. Young, Roger A. Freedman\n- **Planar Kinematics of Rigid Bodies** — Texas A&M University\n- **Energy, Christiaan Huygens, and the Wonderful Cycloid—Theory versus Experiment** — D. A. G. M. van der Heijden"
        }
    ]
    
    job_id = "cycloid_rolling_wheel_mcq"
    image_src = "/Users/apple/.gemini/antigravity/brain/880c4146-29cb-4a83-a684-4ce33f9f6ccb/media__1779190996827.png"
    
    # Set up job directory and copy injected diagram manually
    job_dir = f"output/job_{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    if os.path.exists(image_src):
        shutil.copy2(image_src, os.path.join(job_dir, "tony_diagram.png"))
        print(f"📸 Successfully copied injected diagram to {job_dir}/tony_diagram.png")
    else:
        print(f"⚠️ Warning: Injected diagram not found at {image_src}")

    print(f"🚀 Triggering Manim pipeline for: {topic}")
    
    # Set up pipeline state
    initial_state = {
        "raw_input": solution_v2,
        "topic": topic,
        "job_id": job_id,
        "source_type": "solution_v2",
        "video_type": "educational",
        "render_mode": "manim",
        "with_avatar": False,
        "use_elevenlabs": True,
        "avatar_type": "logo",
        "image_path": image_src,
        "overrides": {
            "render_mode": "manim",
            "use_elevenlabs": True,
            "enable_ambient": True,
            "has_formula": True,
            "max_scenes": 5,
            "narration_style": "strictly direct and concise",
            "max_generated_images": 1
        },
        
        # Required graph fields
        "attempt_count": 0,
        "ppt_attempt_count": 0,
        "no_vision": False,
        "ledger": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "elevenlabs_chars": 0,
            "heygen_seconds": 0
        },
        "rejected_attempts": [],
        "media_manifest": [],
        "research_count": 0
    }
    
    final_state = app.invoke(initial_state)
    
    print("\n🏁 Manim Production Complete!")
    print(f"📁 Output Video: {final_state.get('output_path')}")
    print(f"🌐 Video URL: {final_state.get('video_url')}")
    print(f"💰 Ledger: {final_state.get('ledger')}")

if __name__ == "__main__":
    run_cycloid_mcq()
