import os
import sys
sys.path.append(os.path.abspath("."))

from PIL import Image, ImageDraw
from explainer_slides_generator import render_explainer_mcq_slide

visual_data = {
    "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
    "options": {
        "A": "\\frac{n+2}{2^{m+1}}",
        "B": "\\frac{m-n}{2^{m+n}}",
        "C": "\\frac{m+n}{2^{m+n}}",
        "D": "\\frac{mn}{2^{m+n}}"
    },
    "letter": "A"
}

output_path = "output/job_probability_head_runs/test_render_slide.png"
os.makedirs(os.path.dirname(output_path), exist_ok=True)
render_explainer_mcq_slide("option_highlight", visual_data, output_path)
print(f"🎬 Test render finished! Saved to: {output_path}")
