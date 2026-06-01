import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's Probability of Head Runs MCQ
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Probability of Head Runs",
            "subtitle": "Runs of length at least m in m+n tosses (m > n)"
        },
        "narration_text": "Hello student! I'm Tony, your AI teacher. Today we are solving a classic probability problem: finding the chance of getting a consecutive run of heads of length at least m in a sequence of m plus n tosses of a fair coin, under the simplified condition that m is strictly greater than n."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. The Overlap Simplification",
            "subtitle": "Why m > n makes counting easy",
            "bullets": [
                "Condition m > n means total tosses m+n is less than 2m.",
                "Therefore, it is impossible to have two non-overlapping runs of length m.",
                "We can partition the favorable outcomes by the FIRST start position i of the run.",
                "This ensures the cases are completely disjoint and don't double count."
            ]
        },
        "narration_text": "The key to this problem is the condition that m is greater than n. This means the total tosses are less than 2m, so two separate runs of length m cannot fit in the sequence. Thus, we can uniquely classify every favorable sequence by the very first position where a run of m heads starts, guaranteeing no overlap."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Calculating the Counts",
            "subtitle": "Disjoint Cases for i = 1 to n+1",
            "bullets": [
                "Total outcomes = 2^{m+n}",
                "Case i = 1 (Starts at first toss): H^m followed by n free tosses = 2^n sequences.",
                "Case i >= 2: Toss i-1 must be T. Tosses i to i+m-1 are H.",
                "Prefix has i-2 tosses (free). Suffix has n-i+1 tosses (free).",
                "Count for fixed i >= 2: 2^{i-2} * 1 * 1 * 2^{n-i+1} = 2^{n-1} sequences.",
                "Total favorable = 2^n + n * 2^{n-1} = (n+2) 2^{n-1} sequences."
            ]
        },
        "narration_text": "Let's find the favorable counts. There are 2 to the power m plus n total outcomes. If the run starts at the first toss, we have 2 to the n options. For any other starting position i, the toss before must be tails, and the remaining unfixed tosses give 2 to the n minus 1 options. Summing over all starting positions gives exactly n plus 2 times 2 to the n minus 1 favorable sequences."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
            "options": {
                "A": "\\frac{n+2}{2^{m+1}}",
                "B": "\\frac{m-n}{2^{m+n}}",
                "C": "\\frac{m+n}{2^{m+n}}",
                "D": "\\frac{mn}{2^{m+n}}"
            }
        },
        "narration_text": "Now, let's analyze the options to see which matches our result when we divide the favorable outcomes by the total outcomes."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
            "letter": "C",
            "options": {
                "A": "\\frac{n+2}{2^{m+1}}",
                "B": "\\frac{m-n}{2^{m+n}}",
                "C": "\\frac{m+n}{2^{m+n}}",
                "D": "\\frac{mn}{2^{m+n}}"
            }
        },
        "narration_text": "Option C claims the probability is m plus n over 2 to the m plus n. This assumes only m plus n favorable sequences, which is far too small because the free tosses create exponentially many options. So Option C is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
            "letter": "D",
            "options": {
                "A": "\\frac{n+2}{2^{m+1}}",
                "B": "\\frac{m-n}{2^{m+n}}",
                "C": "\\frac{m+n}{2^{m+n}}",
                "D": "\\frac{mn}{2^{m+n}}"
            }
        },
        "narration_text": "Option D suggests a count of m times n favorable outcomes. Again, this purely polynomial term fails to capture the exponential combinations from the free tosses, making Option D incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
            "letters": ["C", "D"],
            "options": {
                "A": "\\frac{n+2}{2^{m+1}}",
                "B": "\\frac{m-n}{2^{m+n}}",
                "C": "\\frac{m+n}{2^{m+n}}",
                "D": "\\frac{mn}{2^{m+n}}"
            }
        },
        "narration_text": "Therefore, we can safely cross out both Option C and Option D."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "What is the probability of getting a run of heads of length at least m in m+n tosses of a fair coin (m > n)?",
            "letter": "A",
            "correct_answer": "A",
            "explanation": "Probability = (n+2)2^{n-1} / 2^{m+n} = (n+2) / 2^{m+1}.",
            "options": {
                "A": "\\frac{n+2}{2^{m+1}}",
                "B": "\\frac{m-n}{2^{m+n}}",
                "C": "\\frac{m+n}{2^{m+n}}",
                "D": "\\frac{mn}{2^{m+n}}"
            }
        },
        "narration_text": "This leaves Option A: n plus 2, over 2 to the m plus 1. Dividing our favorable count of n plus 2 times 2 to the n minus 1 by the total 2 to the m plus n outcomes, the 2 to the n minus 1 simplifies perfectly with the denominator, leaving exactly n plus 2 over 2 to the m plus 1. Option A is the correct answer!"
    }
]

output_dir = "output/job_probability_head_runs"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for Probability of Head Runs lesson...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Probability of Head Runs",
        job_id="probability-head-runs-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 MATHEMATICAL VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
