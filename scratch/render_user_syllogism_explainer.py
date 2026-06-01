import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes based on the user's Syllogism logical reasoning JSON
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Logical Reasoning: Syllogisms",
            "subtitle": "Statements: Towns, Villages, Forests & Rivers"
        },
        "narration_text": "Hello student! Today we are tackling a syllogism problem. We will evaluate four conclusions based on three statements using set relationships and Venn diagrams."
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. Analyzing the Statements",
            "subtitle": "Building the Venn diagram relations",
            "bullets": [
                "Statement a: All towns are villages. (Towns subset of Villages)",
                "Statement b: No village is forest. (Villages and Forests are disjoint)",
                "Statement c: Some forests are rivers. (Forests and Rivers overlap)"
            ]
        },
        "narration_text": "Let's first map the relationships between our sets. All towns are contained inside villages. No village is forest, meaning villages and forests have zero overlap. Finally, some forests are rivers, meaning there is at least some overlap between the forest and river sets."
    },
    {
        "visual_type": "solution_steps",
        "visual_data": {
            "title": "2. Evaluating the Conclusions",
            "subtitle": "Testing validity in every situation",
            "bullets": [
                "Conclusion I: Some forests are villages. (Invalid: No village is forest)",
                "Conclusion II: Some forests are not villages. (Valid: Forests and Villages are disjoint)",
                "Conclusion III: Some rivers are not villages. (Valid: Rivers in forest cannot be villages)",
                "Conclusion IV: All villages are towns. (Invalid: Villages can exist outside Towns)"
            ]
        },
        "narration_text": "Now we evaluate the conclusions. Conclusion one says some forests are villages, which is invalid since forests and villages never overlap. Conclusion two says some forests are not villages, which is valid because no forest is a village. Conclusion three says some rivers are not villages; this is also valid because the rivers that are forests can never be villages. Conclusion four says all villages are towns, which is invalid because there can be villages outside of towns."
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Statements: All towns are villages. No village is forest. Some forests are rivers. Which conclusions follow?",
            "options": {
                "A": "All follow",
                "B": "either conclusion I or II follows",
                "C": "either conclusion I or II and III follows",
                "D": "None of these"
            }
        },
        "narration_text": "Our analysis shows that only conclusion two and conclusion three follow. Let's look at the multiple choice options to see which matches our findings."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Statements: All towns are villages. No village is forest. Some forests are rivers. Which conclusions follow?",
            "letter": "A",
            "options": {
                "A": "All follow",
                "B": "either conclusion I or II follows",
                "C": "either conclusion I or II and III follows",
                "D": "None of these"
            }
        },
        "narration_text": "Option A says all follow. However, conclusions one and four are completely invalid, so Option A is incorrect."
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Statements: All towns are villages. No village is forest. Some forests are rivers. Which conclusions follow?",
            "letter": "C",
            "options": {
                "A": "All follow",
                "B": "either conclusion I or II follows",
                "C": "either conclusion I or II and III follows",
                "D": "None of these"
            }
        },
        "narration_text": "Option C claims either conclusion one or two and three follows. But conclusion one never follows, and conclusion two independently follows. So this either-or structure is incorrect. Option C does not follow."
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "Statements: All towns are villages. No village is forest. Some forests are rivers. Which conclusions follow?",
            "letters": ["A", "B", "C"],
            "options": {
                "A": "All follow",
                "B": "either conclusion I or II follows",
                "C": "either conclusion I or II and III follows",
                "D": "None of these"
            }
        },
        "narration_text": "This allows us to confidently eliminate Option A, Option B, and Option C."
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "Statements: All towns are villages. No village is forest. Some forests are rivers. Which conclusions follow?",
            "letter": "D",
            "correct_answer": "D",
            "explanation": "Only conclusions II and III follow. None of the options A, B, or C match this correct combination.",
            "options": {
                "A": "All follow",
                "B": "either conclusion I or II follows",
                "C": "either conclusion I or II and III follows",
                "D": "None of these"
            }
        },
        "narration_text": "This leaves Option D: None of these. Since only conclusions two and three logically follow from our statements, and none of the other options capture this combination exactly, Option D is the correct answer."
    }
]

output_dir = "output/job_syllogism_reasoning"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Starting compilation for Syllogism Logical Reasoning lesson...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Syllogism Logical Reasoning",
        job_id="syllogism-reasoning-mcq",
        use_elevenlabs=True
    )
    print("\n🎉 LOGICAL REASONING VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
