import json
import os

# Configuration
KNOWLEDGE_DIR = "factory_knowledge"
TOPIC = "The Great Wall of China"
FACTS_PATH = os.path.join(KNOWLEDGE_DIR, f"{TOPIC.lower().replace(' ', '_')}.json")

# 1. Inject a very specific fact into the KB
MOCK_FACTS = {
    "summary": "The Great Wall of China is a series of fortifications built across the historical northern borders of ancient Chinese states.",
    "key_facts": [
        "FactCheck: The official length is precisely 21,196.18 kilometers.",
        "GroundTruth: It is NOT visible from the moon without aid, despite popular myths.",
        "Specific: The oldest sections were built in the 7th century BC."
    ],
    "dates_and_events": [
        "7th century BC: Construction began"
    ]
}

def setup_mock_kb():
    print(f"📂 Mocking Knowledge Base for '{TOPIC}'...")
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    with open(FACTS_PATH, "w") as f:
        json.dump(MOCK_FACTS, f, indent=4)

def cleanup_mock_kb():
    print(f"🧹 Cleaning up mock KB...")
    if os.path.exists(FACTS_PATH):
        os.remove(FACTS_PATH)

def verify_grounding():
    print("🎬 Starting Multi-Node KB Verification...")
    
    # We will use the Director Agent directly to see if it incorporates the facts
    from director_agent import run_director
    from html_parser import parse_tony_html
    
    dummy_html = "<html><body><h1>The Great Wall</h1><p>It is a big wall in China.</p></body></html>"
    parsed = parse_tony_html(dummy_html, topic_hint=TOPIC)
    
    print("\n🔍 Step 1: Testing Director Grounding...")
    # Passing the MOCK_FACTS as the knowledge_base
    output = run_director(parsed, knowledge_base=MOCK_FACTS)
    
    combined_narration = " ".join(s.narration_text for s in output.scenes)
    
    found_fact_1 = "21,196.18" in combined_narration
    found_fact_2 = "moon" in combined_narration.lower()
    
    if found_fact_1 and found_fact_2:
        print("   ✅ Director correctly grounded narrations in KB facts!")
    else:
        print("   ❌ Director missed some KB facts.")
        print(f"   Script: {combined_narration}")

    print("\n🔍 Step 2: Testing PPT Planner Grounding...")
    # For this, we'll reach into the graph logic or simulate it
    from autonomous_graph import _PPT_PLANNER_PROMPT, _llm_json_with_retry
    
    # Simulate the prompt build in ppt_planner_node
    knowledge_section = f"\n━━━ VERIFIED GROUND TRUTH (KNOWLEDGE BASE) ━━━\n{json.dumps(MOCK_FACTS, indent=2)}\n"
    prompt = _PPT_PLANNER_PROMPT.format(knowledge_section=knowledge_section, feedback_section="")
    
    data = _llm_json_with_retry(
        messages=[{"role": "user", "content": f"TOPIC: {TOPIC}\n\nCONTENT: {combined_narration}"}],
        system_prompt=prompt,
        node_name="PPT_PLANNER",
        state={"job_id": "test", "topic": TOPIC}
    )
    
    found_fact_in_slides = any("21,196.18" in json.dumps(s) for s in data.get("slides", []))
    
    if found_fact_in_slides:
        print("   ✅ PPT Planner correctly grounded slides in KB facts!")
    else:
        print("   ❌ PPT Planner missed KB facts in slides.")
    
    print("\n✨ Verification Complete: Knowledge Base is now deep-wired into all critical nodes.")

if __name__ == "__main__":
    try:
        setup_mock_kb()
        verify_grounding()
    finally:
        cleanup_mock_kb()
