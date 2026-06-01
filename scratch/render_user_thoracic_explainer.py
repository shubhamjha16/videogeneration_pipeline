import os
import sys

# Ensure project root is in python path
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import generate_explainer_slides_video

# Define scenes with dynamic Tony AI Avatar poses for the Thoracic Duct lesson
scenes = [
    {
        "visual_type": "title_card",
        "visual_data": {
            "title": "Anatomy: The Thoracic Duct",
            "subtitle": "Commencement and Vertebral Level"
        },
        "narration_text": "Hello student! Today we are exploring the thoracic duct, the main lymphatic channel of the human body, focusing on where it commences and its key anatomical vertebral levels.",
        "tony_pose": "desk_happy"
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "1. The Cisterna Chyli",
            "subtitle": "Commencement of the Thoracic Duct",
            "bullets": [
                "The thoracic duct begins in the abdomen as an expanded lymphatic sac.",
                "This dilated origin is called the **cisterna chyli**.",
                "It receives lymph from the intestinal and lumbar trunks.",
                "Anatomically lies retrocrurally, anterior to the T12 to L2 vertebrae."
            ]
        },
        "narration_text": "The thoracic duct is the main lymphatic channel of the body. It commences in the upper abdomen as an expanded, dilated lymphatic sac known as the cisterna chyli. This sac receives lymph from both the intestinal and lumbar trunks, and lies classically in the retrocrural space anterior to the bodies of the upper lumbar and lower thoracic vertebrae.",
        "tony_pose": "explaining"
    },
    {
        "visual_type": "concept_explanation",
        "visual_data": {
            "title": "2. Vertebral Levels & diaphragm passage",
            "subtitle": "Mapping the commencement level",
            "bullets": [
                "Cisterna chyli sits classically anterior to the **T12/L1** vertebral bodies.",
                "Most board exam questions simplify this commencement level to **T12**.",
                "Ascends through the diaphragm's **aortic hiatus** at **T12**.",
                "Continues upward through the posterior mediastinum."
            ]
        },
        "narration_text": "Anatomists describe the cisterna chyli as sitting classically anterior to the T12 or L1 vertebral bodies. Consequently, board exams routinely standardize the commencement of the thoracic duct at the T12 level. It is also at this level that the duct ascends through the aortic hiatus of the diaphragm alongside the aorta to enter the thorax.",
        "tony_pose": "reading"
    },
    {
        "visual_type": "mcq_layout",
        "visual_data": {
            "question": "At which vertebral level does the thoracic duct commence?",
            "options": {
                "A": "L5",
                "B": "L3",
                "C": "T12",
                "D": "T4"
            }
        },
        "narration_text": "Now, let's analyze our options to identify the correct vertebral level at which the thoracic duct commences.",
        "tony_pose": "thinking"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "At which vertebral level does the thoracic duct commence?",
            "letter": "A",
            "options": {
                "A": "L5",
                "B": "L3",
                "C": "T12",
                "D": "T4"
            }
        },
        "narration_text": "Option A is L5. This is in the lower abdomen and pelvis, which is far too low for the cisterna chyli. Thus, Option A is incorrect.",
        "tony_pose": "confused"
    },
    {
        "visual_type": "option_highlight",
        "visual_data": {
            "question": "At which vertebral level does the thoracic duct commence?",
            "letter": "B",
            "options": {
                "A": "L5",
                "B": "L3",
                "C": "T12",
                "D": "T4"
            }
        },
        "narration_text": "Option B is L3. While closer, L3 sits below the typical abdominal origin of the thoracic duct, which classically starts higher up. So Option B is also incorrect.",
        "tony_pose": "confused"
    },
    {
        "visual_type": "cross_out",
        "visual_data": {
            "question": "At which vertebral level does the thoracic duct commence?",
            "letters": ["A", "B", "D"],
            "options": {
                "A": "L5",
                "B": "L3",
                "C": "T12",
                "D": "T4"
            }
        },
        "narration_text": "This allows us to confidently cross out Option A, Option B, and Option D.",
        "tony_pose": "standing_point_up"
    },
    {
        "visual_type": "answer_reveal",
        "visual_data": {
            "question": "At which vertebral level does the thoracic duct commence?",
            "letter": "C",
            "correct_answer": "C",
            "explanation": "The thoracic duct commences from the cisterna chyli, classically described at about the T12 vertebral level, and ascends through the aortic hiatus of the diaphragm.",
            "options": {
                "A": "L5",
                "B": "L3",
                "C": "T12",
                "D": "T4"
            }
        },
        "narration_text": "This leaves Option C: T12. This sits perfectly at the classical level of the cisterna chyli and the aortic hiatus of the diaphragm through which the duct enters the chest cavity. Option C is the correct answer.",
        "tony_pose": "victory"
    }
]

output_dir = "output/job_thoracic_duct_whiteboard"
os.makedirs(output_dir, exist_ok=True)

print("🚀 Compiling Thoracic Duct lesson with ChatGPT Images 2.0 + Tony Cartoon Avatar...")
try:
    output_path, ledger = generate_explainer_slides_video(
        scenes=scenes,
        output_dir=output_dir,
        topic="Thoracic Duct Anatomy Level",
        job_id="thoracic-duct-mcq-explainer-avatar",
        use_elevenlabs=True,
        avatar_type="tony_cartoon",
        with_avatar=True
    )
    print("\n🎉 WHITEBOARD AVATAR VIDEO RENDER SUCCESS!")
    print(f"🎬 Output video saved to: {output_path}")
    print(f"📊 Resource Ledger: {ledger}")
except Exception as e:
    print(f"\n❌ Pipeline execution encountered an error: {e}")
    sys.exit(1)
