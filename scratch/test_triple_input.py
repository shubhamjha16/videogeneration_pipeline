
import json
from html_parser import parse_tony_html

def test_unified_parser():
    print("🚀 Starting Triple-Threat Input Validation...")
    
    # 1. Swagger Style (List)
    swagger_json = [
        {"title": "Concept", "description": "TBI recognition."},
        {"title": "Option A", "description": "Contusion facts."}
    ]
    res1 = parse_tony_html(swagger_json)
    print(f"\n✅ Type 1 (Swagger): {res1['topic']} | Options: {list(res1.get('options', {}).keys())}")
    
    # 2. Pipeline Style (Dict)
    pipeline_json = {"raw_input": "### Header\nOption B) Text"}
    res2 = parse_tony_html(pipeline_json)
    print(f"✅ Type 2 (Pipeline): {res2['topic']} | Options: {list(res2.get('options', {}).keys())}")
    
    # 3. Raw Text (String)
    raw_text = "### Messy Note\n**Option C) word**\nOption D. desc"
    res3 = parse_tony_html(raw_text)
    print(f"✅ Type 3 (Raw Text): {res3['topic']} | Options: {list(res3.get('options', {}).keys())}")
    if res3.get('options', {}).get('C'):
        print(f"   ↳ Option C Content: '{res3['options']['C']['name']}'")

if __name__ == "__main__":
    test_unified_parser()
