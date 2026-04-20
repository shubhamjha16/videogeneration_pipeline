import json
import sys
import os

# Add root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from html_parser import parse_tony_html

def simulate_real_integration():
    # 1. Mocking the exact JSON structure from teacherapi.easetolearn.com
    teacher_api_response = {
        "responseTxt": "success",
        "questionId": 212173,
        "solution": """
            <h2>Concept Explanation</h2>
            <p>The larynx is innervated by branches of the <strong>Vagus nerve (CN X)</strong>. 
            The superior laryngeal nerve provides sensory input above the vocal folds, 
            while the recurrent laryngeal nerve innervates all intrinsic muscles except the cricothyroid.</p>
            
            <h2>Option Analysis</h2>
            <ul>
                <li><strong>A. Recurrent Laryngeal Nerve</strong> This nerve is a branch of the vagus nerve and is critical for vocal cord movement.</li>
                <li><strong>B. Glossopharyngeal Nerve</strong> This nerve primarily handles the posterior third of the tongue and gag reflex.</li>
            </ul>
            
            <h2>Citations</h2>
            <p>Gray's Anatomy, 42nd Edition.</p>
            <p>Netter's Atlas of Human Anatomy.</p>
        """
    }

    print(f"📡 [Simulating teacherapi.easetolearn.com response for ID: {teacher_api_response['questionId']}]")
    
    # 2. Extract the 'solution' just like Spring Boot will
    raw_html = teacher_api_response["solution"]
    topic = "Larynx Innervation" # Derived from questionId in real system

    # 3. Run the factory parser
    structured_facts = parse_tony_html(raw_html, topic_hint=topic)

    print("\n✅ [Factory Ingestion Success]")
    print(f"🔍 Detected Subject: {structured_facts['subject']}")
    print(f"🔍 Content Type:     {structured_facts['content_type']}")
    print(f"🔍 Topic:            {structured_facts['topic']}")
    print(f"🔍 Citations Found:  {len(structured_facts['citations'])}")
    
    # Verify we caught the specific medical facts
    print("\n📝 Extracted Concept Preview:")
    print(f"   {structured_facts['concept'][:150]}...")

if __name__ == "__main__":
    simulate_real_integration()
