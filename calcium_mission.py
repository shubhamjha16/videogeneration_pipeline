import os
from autonomous_graph import app as tony_app

html_content = """
<html>
  <body>
    <h2>Concept Explanation</h2>
    <p>
      Calcium gluconate is a medication often used to treat conditions related to low calcium levels in the blood or to counteract toxic effects caused by agents that either decrease serum calcium or increase serum potassium. It can be important during emergencies and critical care scenarios such as cardiac arrest, especially when electrolyte disturbances are the underlying cause. In Cardiopulmonary Resuscitation (CPR), the administration of calcium salts like calcium gluconate is considered in specific circumstances where electrolyte imbalances (notably hypocalcemia, hyperkalemia, or calcium channel blocker toxicity) are identified.
    </p>

    <h2>Analysis of Options</h2>
    <ul>
      <li>
        <strong>A. Hypocalcemia:</strong> 
        <p>
          Hypocalcemia (low calcium levels in blood) is an important indication for administering calcium gluconate during CPR. Low calcium can lead to cardiac instability and impaired muscle contraction, which calcium gluconate helps correct.
        </p>
      </li>
      <li>
        <strong>B. Hypokalemia:</strong>
        <p>
          Hypokalemia (low potassium levels in blood) is <strong>not</strong> an indication for giving calcium gluconate in CPR. The correction of hypokalemia involves potassium supplementation, not calcium administration, as the problem is low potassium, not calcium or potassium toxicity. Administering calcium gluconate would have no therapeutic effect in hypokalemia in terms of cardiac stabilization.
        </p>
      </li>
      <li>
        <strong>C. Hyperkalemia:</strong>
        <p>
          Hyperkalemia (high potassium levels in blood) can cause life-threatening cardiac dysrhythmias. Calcium gluconate is used in these cases to stabilize the cardiac membranes, buying time while other measures to reduce potassium are implemented.
        </p>
      </li>
      <li>
        <strong>D. Calcium antagonism:</strong>
        <p>
          Calcium antagonism refers to toxicity caused by calcium channel blockers (such as overdoses of certain antihypertensive drugs). Calcium gluconate is indicated here for reversing the negative effects of these drugs on the heart.
        </p>
      </li>
    </ul>
    <p>
      Therefore, calcium gluconate is <strong>not</strong> used in CPR for hypokalemia. The correct answer is <strong>B. Hypokalemia</strong>.
    </p>
  </body>
</html>
"""

def run_calcium_mission():
    print("🚀 [MISSION CONTROL] Starting Calcium Gluconate Masterclass...")
    initial_state = {
        "raw_input": html_content,
        "topic": "CalciumGluconate",
        "attempt_count": 0,
        "image_prompts": []
    }
    
    final_state = tony_app.invoke(initial_state)
    print(f"🏆 MISSION COMPLETE!")
    print(f"🎬 Output Location: {final_state.get('output_path')}")

if __name__ == "__main__":
    run_calcium_mission()
