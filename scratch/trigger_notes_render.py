import requests
import json

url = "http://localhost:8000/render"
headers = {
    "Content-Type": "application/json",
    "X-API-Key": "your_key_here" # The api_bridge will ignore if internal
}

payload = {
    "topic": "Disseminated Intravascular Coagulation (DIC) Investigation",
    "markdown": "# 1. MOST SPECIFIC INVESTIGATION FOR DIC\n\n## CONCEPT\n- DIC is a consumptive coagulopathy.\n- Widespread activation of coagulation -> fibrin clots in microvasculature.\n- Consumes platelets & clotting factors.\n- Secondary activation of fibrinolysis -> ↑ fibrin degradation products (FDPs).\n\n## WHY D-DIMER IS MOST SPECIFIC?\n- D-dimer is produced only when cross-linked fibrin is lysed.\n- Implies: Thrombin -> fibrin & Factor XIII -> cross-linked fibrin.\n- DIC uniquely involves BOTH clot formation & fibrinolysis systemically -> ↑ D-dimer.\n\n## KEY POINTS TO REMEMBER\n- DIC = clot formation + clot breakdown.\n- D-dimer ↑ = specific marker of DIC.\n\n## OPTION ANALYSIS\nA) D-dimer assay (Most specific): Reflects breakdown of cross-linked fibrin.\nB) Bleeding time: Evaluates platelet function, but non-specific.\nC) Clotting time: Crude global test, not sensitive.\nD) Fibrinogen level: Often decreased but not specific.\n\n## FINAL ANSWER\nA) D-dimer assay is the most specific investigation for DIC.",
    "render_mode": "notes"
}

try:
    # Ensure the server is running or use the internal runner
    from autonomous_graph import app
    
    print("🚀 Triggering Notes Pipeline Render (Images 2.0)...")
    config = {"configurable": {"thread_id": "notes_test_1"}}
    
    # We simulate the director result to force 'notes' mode
    initial_state = {
        "topic": payload["topic"],
        "markdown": payload["markdown"],
        "raw_input": payload["markdown"], # Added this
        "render_mode": "notes",
        "video_type": "educational",
        "with_avatar": False,
        "attempt_count": 0,
        "ledger": {},
        "scenes": [],
        "job_id": "test_notes_v1",
        "progress_logs": [],
        "rendering_errors": ""
    }
    
    # Run the graph
    for output in app.stream(initial_state, config):
        for node_name, state in output.items():
            print(f"\n--- Node: {node_name} ---")
            if "rendering_errors" in state and state["rendering_errors"]:
                print(f"❌ Error: {state['rendering_errors']}")
            if "output_path" in state and state["output_path"]:
                print(f"✅ FINAL VIDEO: {state['output_path']}")

except Exception as e:
    print(f"❌ Failed to trigger render: {e}")
