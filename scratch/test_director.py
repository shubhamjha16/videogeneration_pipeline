
import sys
import os
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")

load_dotenv(os.path.dirname(os.path.abspath(__file__)) + "/../.env")

from director_agent import run_director
from html_parser import parse_tony_html

def main():
    print("🎬 Testing Director Agent with OpenAI (GPT-4o)...")
    
    html = """[{"title": "Concept Explanation", "description": "This scenario tests recognition of traumatic brain injury patterns on CT. When a patient is unconscious after trauma but CT shows *no midline shift* (no large focal mass lesion), the concern shifts toward *diffuse* injuries rather than a localized hematoma or large contusion.\\n\\n*Diffuse axonal injury (DAI)* results from rotational/acceleration–deceleration forces that shear axons, classically at the *gray–white matter junction, **corpus callosum, and **brainstem. CT may be normal or may show **multiple tiny (punctate) hemorrhages* without a large space-occupying clot.\\n\\nCompression/effacement of *basal cisterns* can occur due to *diffuse cerebral edema, which can accompany DAI, and it can present with early, disproportionate coma compared with the apparent focal CT findings."}]"""
    topic = "Diffuse Axonal Injury (DAI)"
    
    facts = parse_tony_html(html, topic_hint=topic)
    
    try:
        print("⏳ Calling Director (OpenAI)...")
        from director_agent import run_director
        import director_agent
        
        # Monkey patch provider
        original_get_completion = director_agent.LLMFactory.get_completion
        def patched_get_completion(*args, **kwargs):
            kwargs['provider_override'] = "openai"
            return original_get_completion(*args, **kwargs)
        
        director_agent.LLMFactory.get_completion = patched_get_completion
        
        output = run_director(facts)
        print(f"✅ SUCCESS! Render Mode: {output.render_mode}")
        print(f"🎬 Planned {len(output.scenes)} scenes.")
    except Exception as e:
        print(f"❌ FAILED: {e}")

if __name__ == "__main__":
    main()
