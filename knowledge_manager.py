"""
Knowledge Manager — Hallucination Defense System
Handles persistent storage, retrieval, and distillation of factual search data.
"""

import os
import json
import re
from typing import Optional, List, Dict, Any
import config
from llm_factory import LLMFactory, clean_llm_json
from knowledge_vector_store import index_research

KNOWLEDGE_DIR = "factory_knowledge"

def get_knowledge(topic: str) -> Optional[Dict[str, Any]]:
    """Retrieve verified facts for a topic if they exist in the KB."""
    slug = _slugify_topic(topic)
    path = os.path.join(KNOWLEDGE_DIR, f"{slug}.json")
    
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ Error reading knowledge file {path}: {e}")
    return None

def inject_solution_v2_as_knowledge(topic: str, solution_v2: list) -> dict:
    """
    Convert Spring Boot solutionV2 directly into KB format
    so Director uses it as ground truth instead of searching web
    """
    facts = {
        "summary": "",
        "key_facts": [],
        "visual_metaphors": [],
        "source": "solution_v2"
    }
    
    for section in solution_v2:
        title = section.get("title", "")
        desc = section.get("description", "")
        
        if title == "Concept Explanation":
            facts["summary"] = desc
        elif title == "Option Analysis":
            facts["key_facts"].append(desc)
        elif title == "Final Answer":
            facts["key_facts"].insert(0, f"ANSWER: {desc}")
        elif title == "Citations":
            facts["visual_metaphors"].append(desc)
    
    # Save to KB so Director finds it
    save_knowledge(topic, facts)
    return facts

def save_knowledge(topic: str, facts: Dict[str, Any]) -> str:
    """Save verified facts to the KB."""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    slug = _slugify_topic(topic)
    path = os.path.join(KNOWLEDGE_DIR, f"{slug}.json")
    
    try:
        with open(path, "w") as f:
            json.dump(facts, f, indent=4)
        
        # INDUSTRIAL SENTINEL: Index newly acquired knowledge into the Vector DB
        index_research(topic, facts)
        
        return path
    except Exception as e:
        print(f"❌ Failed to save knowledge for {topic}: {e}")
        return ""

def distill_search_results(topic: str, raw_results: List[Dict[str, Any]], job_id: str = None) -> Dict[str, Any]:
    """
    Use Gemma 4 to convert raw search snippets into a structured, verified fact sheet.
    This reduces 'hallucination' by forcing the agent to stick to summarized ground truth.
    """
    if not raw_results:
        return {}

    # Format snippets for the LLM
    context_str = ""
    for i, res in enumerate(raw_results, 1):
        context_str += f"[{i}] {res['title']}\nSource: {res['url']}\nContent: {res['content']}\n\n"

    system_prompt = """You are a Fact Distiller for an educational video factory.
Your job is to take raw web search results and turn them into a clean, structured 'Fact Sheet'.

━━━ RULES ━━━
- ONLY include facts that appear in the provided snippets.
- If snippets contradict each other, note the discrepancy.
- Categorize information into: summary, key_facts, dates_and_events, and visual_metaphors.
- 'visual_metaphors' should be ideas for cinematic or mathematical visualizations of the concept.
- **KB_CONFIDENCE**: Include a "kb_confidence" float (0.0 to 1.0) reflecting the consistency and authority of the sources.
- **PROVENANCE_NOTE**: Include a brief note on the reliability of the sources used.
- Return ONLY valid JSON.
"""

    user_prompt = f"""TOPIC: {topic}
RAW SEARCH SNIPPETS:
{context_str}

Distill this into a structured JSON fact sheet for an educational video.
"""

    try:
        content = LLMFactory.get_completion(
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            json_mode=True,
            job_id=job_id
        )
        return clean_llm_json(content)
    except Exception as e:
        print(f"⚠️ Distillation failed: {e}")
        return {"summary": "Failed to distill facts.", "key_facts": []}

def _slugify_topic(topic: str) -> str:
    """Create a filesystem-safe filename from a topic string."""
    s = topic.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    return re.sub(r'[\s-]+', '_', s)

if __name__ == "__main__":
    # Test slugify
    print(f"Slug: {_slugify_topic('Internal Iliac Artery (Branching)')}")
    
    # Mock test
    test_topic = "Quantum Entanglement"
    test_data = {"summary": "A physical phenomenon where particles remain connected...", "key_facts": ["Spooky action at a distance"]}
    path = save_knowledge(test_topic, test_data)
    print(f"Saved to: {path}")
    
    loaded = get_knowledge(test_topic)
    print(f"Loaded Summary: {loaded.get('summary')}")
