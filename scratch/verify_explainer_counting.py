import os
import shutil
from explainer_generator import generate_explainer_video

def test_contextual_building_blocks():
    print("🧪 Testing Proper Path 3 Building Blocks (Layered Metaphor)")
    
    output_dir = "test_proper_output"
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Create a "World" background (The Train)
    from PIL import Image, ImageDraw
    bg_img = Image.new('RGB', (1280, 720), color=(40, 40, 60))
    d_bg = ImageDraw.Draw(bg_img)
    d_bg.rectangle([100, 400, 1100, 600], fill=(80, 80, 100)) # Simple Train shape
    d_bg.text((500, 450), "TRAIN TRACKS", fill=(200, 200, 200))
    bg_path = os.path.join(output_dir, "train_bg.png")
    bg_img.save(bg_path)
    
    # 2. Create a "Logic" asset (The Number/Item)
    item_img = Image.new('RGB', (256, 256), color=(255, 255, 255))
    d_item = ImageDraw.Draw(item_img)
    d_item.text((100, 100), "X", fill=(255, 0, 0), font_size=60)
    item_path = os.path.join(output_dir, "math_item.png")
    item_img.save(item_path)
    
    # 3. Define the "Proper" scene
    scenes = [
        {
            "narration_text": "To understand linear differences, imagine a train cruising at a steady pace.",
            "visual_type": "counting_metaphor",
            "visual_data": {
                "item_name": "marker", 
                "count": 4, 
                "background_prompt": "A cinematic high speed train on rails"
            }
        }
    ]
    
    image_paths = {
        "counting_0_marker": item_path,
        "counting_bg_0": bg_path
    }
    
    # 4. Trigger generation
    print("🚀 Rendering 'Proper' explainer with background composition...")
    try:
        video_path = generate_explainer_video(scenes, image_paths, output_dir, "Proper Test")
        if os.path.exists(video_path):
            print(f"✅ Success! Layered video generated at: {video_path}")
            print("   (Check if X-markers pop in over the zooming train image)")
        else:
            print("❌ Video file was not created.")
    except Exception as e:
        print(f"❌ Render failed: {e}")

if __name__ == "__main__":
    # Mock some env vars if needed
    os.environ["ELEVENLABS_API_KEY"] = "" # Fallback to local TTS if empty
    test_contextual_building_blocks()
