import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's Definite Integral Symmetry math curriculum JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Symmetry Trick for Definite Integrals",
            "subtitle": "Definite Integral of ln(t) / (1+t)"
        },
        "narration_text": "Hello student! Today we are tackling an advanced calculus problem: evaluating a definite integral using a clever symmetry trick by substituting t equals 1 over u."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. Definite Integral Symmetry Trick",
            "subtitle": "Relating f(x) to f(1/x)",
            "bullets": [
                "Integrand has ln(t): substitution t = 1/u flips sign of ln(t)",
                "Sign flip: ln(1/u) = -ln(u)",
                "Add the two integrals to produce a simple solvable form",
                "Integrand collapses to ln(u)/u with antiderivative 1/2 * (ln u)^2"
            ]
        },
        "narration_text": "This problem tests a common symmetry trick for definite integrals involving log t and rational functions. When we apply the substitution t equals one over u, the logarithm flips its sign. Summing the integrals collapses the integrand to log u over u, which is simple to integrate."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Step-by-Step Derivation",
            "subtitle": "Simplifying the sum of integrals",
            "bullets": [
                "f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt",
                "f(1/x) = \\int_{1}^{x} \\frac{\\ln u}{u(u+1)}\\,du  \\text{(using } t = 1/u \\text{)}",
                "Sum: f(x) + f(1/x) = \\int_{1}^{x} \\ln u \\cdot \\frac{u+1}{u(u+1)}\\,du",
                "Result: f(x) + f(1/x) = \\int_{1}^{x} \\frac{\\ln u}{u}\\,du = \\frac{1}{2} (\\ln x)^2"
            ]
        },
        "narration_text": "Let's perform the derivation. We write down the definition of f of x, and substitute t equals one over u to find f of one over x. Summing the two integrals, we factor out log u. The fraction simplifies to one over u, giving a final sum identity of one half times the square of log x."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "If f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt, then find the value of f(e) + f(1/e):",
            "options": {
                "A": "1",
                "B": "2",
                "C": "1/2",
                "D": "none of these"
            }
        },
        "narration_text": "Now, let's look at the multiple choice question. We are asked to evaluate the sum f of e plus f of one over e. Which of the four options matches our derived formula?"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "If f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt, then find the value of f(e) + f(1/e):",
            "letter": "A",
            "options": {
                "A": "1",
                "B": "2",
                "C": "1/2",
                "D": "none of these"
            }
        },
        "narration_text": "Option A is one, which would correspond to getting log e squared directly. However, this misses the factor of one half from our antiderivative, so Option A is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "If f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt, then find the value of f(e) + f(1/e):",
            "letter": "B",
            "options": {
                "A": "1",
                "B": "2",
                "C": "1/2",
                "D": "none of these"
            }
        },
        "narration_text": "Option B is two, which is far too large and typically comes from a sign error or misapplying the substitution bounds. Thus, Option B is also incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "If f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt, then find the value of f(e) + f(1/e):",
            "letters": ["A", "B"],
            "options": {
                "A": "1",
                "B": "2",
                "C": "1/2",
                "D": "none of these"
            }
        },
        "narration_text": "We can comfortably cross out both Option A and Option B."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "If f(x) = \\int_{1}^{x} \\frac{\\ln t}{1+t}\\,dt, then find the value of f(e) + f(1/e):",
            "letter": "C",
            "correct_answer": "C",
            "explanation": "Substituting x=e in \\frac{1}{2} (\\ln x)^2 yields \\frac{1}{2} (\\ln e)^2 = \\frac{1}{2} \\cdot 1 = 1/2.",
            "options": {
                "A": "1",
                "B": "2",
                "C": "1/2",
                "D": "none of these"
            }
        },
        "narration_text": "This leaves Option C: one half. Substituting x equals e into our identity, since the natural log of e is one, we get exactly one half. Therefore, Option C is our correct answer."
    }
]

output_dir = "output/job_definite_integral_symmetry"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation using standard Explainer Slides Pipeline...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Symmetry Definite Integral of ln(t)",
        job_id="definite-integral-symmetry-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
