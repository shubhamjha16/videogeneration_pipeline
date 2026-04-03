import os
from autonomous_graph import app as tony_app

html_content = """
<html>
  <body>
    <h2>Understanding Carpopedal Spasm in Hyperventilation</h2>
    <p>
      Carpopedal spasm is a form of tetany involving involuntary contractions of the muscles of the hands (carpo-) and feet (pedal). 
      It is commonly observed during episodes of hyperventilation due to the resultant respiratory alkalosis. 
      When a person hyperventilates, they expel more carbon dioxide (CO2) from the body than normal. 
      The drop in CO2 levels leads to an increase in blood pH (alkalosis). 
      This alkalosis causes calcium to bind more avidly to plasma proteins, particularly albumin, which reduces the level of free or ionized calcium in the blood.
      Ionized calcium is the biologically active form of calcium responsible for neuromuscular function. 
      When its level drops, the threshold for nerve excitability is lowered, leading to increased neuromuscular irritability and spasms.
    </p>
  </body>
</html>
"""

def run_carpopedal_mission():
    print("🚀 [MISSION CONTROL] Starting Carpopedal Spasm Masterclass...")
    initial_state = {
        "raw_input": html_content,
        "topic": "CarpopedalSpasm",
        "attempt_count": 0,
        "image_prompts": []
    }
    
    final_state = tony_app.invoke(initial_state)
    print(f"🏆 MISSION COMPLETE!")
    print(f"🎬 Output Location: {final_state.get('output_path')}")

if __name__ == "__main__":
    run_carpopedal_mission()
