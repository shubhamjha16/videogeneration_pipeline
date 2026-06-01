import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes with dynamic Tony AI Avatar poses for the Lozere Wolves Resurgence lesson
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "RC Comprehension: Lozere Wolves",
            "subtitle": "Analyzing Resurgent Populations"
        },
        "narration_text": "Hello student! Today we are analyzing an insightful reading comprehension passage regarding the recovery and expansion of wolf populations in Lozere, focusing on identifying the factors that drive this resurgence.",
        "tony_pose": "desk_happy"
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "Resurgence of Wolves",
            "subtitle": "Identifying the driving factors",
            "bullets": [
                "Wolves are expanding across Europe and Lozere.",
                "Primary factors include rural depopulation.",
                "Increased woodland and forest habitat cover.",
                "Legal protection status and NGO monitoring."
            ]
        },
        "narration_text": "Modern scientific and administrative changes have allowed wolf populations to expand. In recent decades, three primary drivers have supported this return: first, depopulation of rural areas; second, a corresponding increase in woodland and forest habitats; and third, the granting of strict legal and administrative protection status to wolves across Europe.",
        "tony_pose": "explaining"
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "Historical Context",
            "subtitle": "Past eradication of wolves",
            "bullets": [
                "Luparii were royal officers tasked with extermination.",
                "Helped eliminate wolves by the 1930s.",
                "Represents past eradication, not modern resurgence.",
                "Hence, unrelated to the growing wolf population."
            ]
        },
        "narration_text": "Historically, wolves were actively hunted and eliminated by the 1930s, assisted by the royal office of the Luparii. However, these historical details explain the past eradication of the species and have no direct relation to the drivers behind their modern comeback.",
        "tony_pose": "reading"
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "Let's review the options to find the factor that did not contribute to the modern increase of the wolf population in Lozere.",
        "tony_pose": "thinking"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "letter": "A",
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "Option A mentions an increase in woodlands and forest cover. The passage tells us that expanding forest habitats directly support the return and spread of wolves. So, this is a valid contributing factor.",
        "tony_pose": "confused"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "letter": "B",
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "Option B names the protected status granted to wolves in Europe. The text explains that legal and administrative protection protects wolves from hunting, which helps populations recover. Thus, Option B is also a contributing factor.",
        "tony_pose": "confused"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "letter": "C",
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "Option C references a decline in the rural population. Rural depopulation leads to less human disturbance and agricultural pressure, allowing nature and wildlife to rebound. Therefore, Option C is a true contributing factor.",
        "tony_pose": "confused"
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "letters": ["A", "B", "C"],
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "Since Options A, B, and C are all valid drivers of the modern resurgence, we can eliminate them from being our answer.",
        "tony_pose": "standing_point_up"
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "Which of the following is NOT described as a factor behind wolves increasing/spreading in Lozere?",
            "letter": "D",
            "correct_answer": "D",
            "explanation": "The Luparii were historical wolf-catchers who helped eradicate the wolves by the 1930s. The shutting down of their royal office is historical context for the past eradication, not a factor in their modern resurgence.",
            "options": {
                "A": "An increase in woodlands and forest cover in Lozere.",
                "B": "The granting of a protected status to wolves in Europe.",
                "C": "A decline in the rural population of Lozere.",
                "D": "The shutting down of the royal office of the Luparii."
            }
        },
        "narration_text": "This leaves Option D: The shutting down of the royal office of the Luparii. This office was historically tasked with extermination. Its shutdown is a historical note about their eradication in the past, not a driver of their modern comeback. Option D is our correct answer.",
        "tony_pose": "victory"
    }
]

output_dir = "output/job_wolves_resurgence"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Re-compiling Lozere Wolves Resurgence lesson WITH Tony AI Avatar...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Lozere Wolves Resurgence",
        job_id="wolves-resurgence-mcq-explainer-avatar",
        use_elevenlabs=True,
        avatar_type="tony_cartoon",
        with_avatar=True
    )
    print("\n🎉 AVATAR VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
