import os
import shutil
from notes_generator import _generate_notes_audio, _apply_animated_reveal

# 1. SETUP
job_id = "custom_notes_dic_eeg"
output_dir = os.path.join("output", f"job_{job_id}")
os.makedirs(output_dir, exist_ok=True)

# 2. SOURCE IMAGE
# Path from your previous message
source_image = "/Users/apple/.gemini/antigravity/brain/0c165762-124d-4e4f-913a-7eb35efc926c/media__1778147327317.jpg"
local_image_path = os.path.join(output_dir, "notes_infographic.png")
shutil.copy(source_image, local_image_path)

# 3. CONTENT NARRATION
# Combining your provided text into scenes for timing
scenes = [
    {"narration_text": "Topic one. Most specific investigation for disseminated intravascular coagulation or D I C. DIC is a consumptive coagulopathy where widespread activation of coagulation leads to fibrin clots in the microvasculature. This consumes platelets and clotting factors, and secondarily activates fibrinolysis."},
    {"narration_text": "Why is D-dimer most specific? Because fibrin is being formed and then broken down, DIC produces increased fibrin degradation products, especially D-dimers. These are generated only when cross-linked fibrin is lysed. Tests that detect these products are therefore more specific for ongoing intravascular fibrin formation and breakdown."},
    {"narration_text": "Option analysis. Option A, D-dimer assay. It reflects breakdown of cross-linked fibrin, implying thrombin has generated fibrin and factor thirteen has cross-linked it—key events in DIC. Option B, Bleeding time. It evaluates platelet function but is nonspecific. Option C, Clotting time. A crude test, not sensitive. Option D, Fibrinogen level. Often decreased but not specific as it can be low in liver disease or even increased early as an acute-phase reactant."},
    {"narration_text": "Final answer for topic one. Option A, D-dimer assay is the most specific investigation for D I C."},
    {"narration_text": "Topic two. Typical E E G wave in metabolic encephalopathy. Metabolic encephalopathy, from hepatic, renal, or hypoxic causes, typically produces a diffuse slowing of background activity on E E G. This reflects impaired cortical neuronal function globally."},
    {"narration_text": "As encephalopathy worsens, normal faster rhythms like alpha are replaced by progressively slower frequencies. The classic pattern is an increase in theta and especially delta activity, often generalized. EEG frequency bands are alpha, beta, gamma, and delta. The slowest band, delta, is most associated with diffuse cerebral dysfunction."},
    {"narration_text": "Option analysis. Option A, Alpha rhythm is normal for awake adults and tends to slow down in encephalopathy. Option B, Beta is a fast rhythm enhanced by sedatives. Option C, Gamma is even faster and not typical for metabolic brain dysfunction. Option D, Delta waves, representing zero point five to four hertz, are the hallmark of significant generalized slowing."},
    {"narration_text": "Final answer for topic two. Option D, Delta is the typical wave seen in metabolic encephalopathy."}
]

# 4. GENERATE AUDIO
print(f"🚀 Generating narration for {len(scenes)} scenes...")
audio_path, audio_duration = _generate_notes_audio(scenes, output_dir, job_id=job_id)

# 5. ANIMATE (SLIDER FOCUS WITH MANUAL BREAKPOINTS)
print(f"🎬 Animating '{local_image_path}' with Grid-Aware Slider...")
output_path = os.path.join(output_dir, "notes_video.mp4")

# Manual Y-coordinates (fractions 0.0 to 1.0) chosen to match the logical grid of this image
# [Top, DIC Heading End, DIC Content End, DIC Section End, EEG Heading End, EEG Content End, Bottom]
custom_breakpoints = [0.0, 0.11, 0.51, 0.59, 0.69, 0.91, 1.0]

# Trigger render (I will update notes_generator.py to accept these)
_apply_animated_reveal(
    local_image_path, 
    audio_path, 
    output_path, 
    audio_duration, 
    num_sections=len(custom_breakpoints)-1,
    manual_breakpoints=custom_breakpoints
)

print(f"\n✅ GRID-AWARE RENDER COMPLETE!")
print(f"📍 Location: {os.path.abspath(output_path)}")
