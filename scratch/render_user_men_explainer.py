import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's MEN curriculum JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Multiple Endocrine Neoplasia (MEN) Syndromes",
            "subtitle": "Clinical Diagnosis and Triad Identification"
        },
        "narration_text": "Welcome to today's clinical endocrinology case analysis. Today, we will study Multiple Endocrine Neoplasia, commonly known as M E N, analyzing how to classify these syndromes based on glandular involvement."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. The MEN 1 (Wermer) Triad",
            "subtitle": "The classic 3 P's mnemonic",
            "bullets": [
                "Parathyroid hyperplasia or adenoma (primary hyperparathyroidism)",
                "Pancreatic neuroendocrine islet cell tumors (e.g. gastrinoma)",
                "Pituitary adenomas (e.g. prolactinoma)"
            ],
            "objects": ["human endocrine gland locations", "pituitary hormone levels chart"]
        },
        "narration_text": "First, let's learn the theory. M E N one, also called Wermer syndrome, classically presents with the three P's: parathyroid hyperplasia, pancreatic neuroendocrine islet cell tumors, and pituitary adenomas. It can also feature adrenal cortical hyperplasia and skin findings like cutaneous facial angiofibromas."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Differentiating MEN 1 vs. MEN 2",
            "subtitle": "Genetic and anatomical contrasts",
            "bullets": [
                "MEN 1: Parathyroid, Pancreas, Pituitary (3 P's)",
                "MEN 2A: Medullary thyroid cancer, Pheochromocytoma, Parathyroid",
                "MEN 2B: Medullary thyroid cancer, Pheochromocytoma, Mucosal neuromas"
            ],
            "objects": ["thyroid and adrenal gland sketch", "RET proto-oncogene illustration"]
        },
        "narration_text": "Next, let's contrast the subtypes. While M E N one involves the three P's, M E N two syndromes are driven by R E T mutations and focus on medullary thyroid carcinoma and pheochromocytoma. M E N two A includes parathyroid hyperplasia, whereas M E N two B is distinguished by mucosal neuromas and a marfanoid body habitus."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "Let's review the options. We need to match this specific patient constellation to the correct M E N subtype."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "letter": "B",
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "Analyzing Option B, M E N two A classically features medullary thyroid carcinoma and pheochromocytoma, with possible parathyroid hyperplasia. Since pancreatic and pituitary tumors are absent, Option B is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "letter": "C",
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "Analyzing Option C, M E N two B is defined by medullary thyroid cancer, pheochromocytoma, mucosal neuromas, and a marfanoid body shape. It does not present with pituitary or pancreatic neuroendocrine tumors, so Option C is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "letter": "D",
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "Analyzing Option D, M E N two C is a highly theoretical term not recognized as a major subtype in standard endocrinology. Thus, Option D is also incorrect."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "letters": ["B", "C", "D"],
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "Consequently, we cross out Option B, Option C, and Option D from our choices."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "Which MEN subtype classically presents with primary hyperparathyroidism, pituitary adenomas, pancreatic islet cell tumors, and cutaneous angiofibromas?:",
            "letter": "A",
            "correct_answer": "A",
            "explanation": "The clinical constellation of parathyroid, pancreatic islet cell, and pituitary tumors with cutaneous angiofibromas is the diagnostic hallmark of MEN 1.",
            "options": {
                "A": "MEN 1",
                "B": "MEN 2A",
                "C": "MEN 2B",
                "D": "MEN 2C"
            }
        },
        "narration_text": "This leaves Option A: M E N one. The combination of hyperparathyroidism, pancreatic neuroendocrine islet cell tumors, pituitary adenomas, and cutaneous angiofibromas is the diagnostic triad of M E N one, Wermer syndrome. Option A is the correct answer."
    }
]

output_dir = "output/user_men_explainer_slides"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation using standard Explainer Slides Pipeline for MEN syndromes...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="MEN Syndromes",
        job_id="user-men-job",
        use_elevenlabs=True
    )
    print("\n🎉 VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
