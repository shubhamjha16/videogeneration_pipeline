import markdown
from html_parser import parse_tony_html
import json

md = """
### Sample MCQ
A. First Option
B. Second Option
C. Third Option
D. Fourth Option

Correct Answer: A
"""

html = markdown.markdown(md, extensions=['extra', 'tables', 'fenced_code'])
print("--- HTML ---")
print(html)

facts = parse_tony_html(html, topic_hint="Test Topic")
print("\n--- FACTS ---")
print(json.dumps(facts, indent=2))
