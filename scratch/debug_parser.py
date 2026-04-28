
import json
from html_parser import parse_tony_html

raw_text = """A male was brought unconscious to the hospital with external injuries. CT brain showed no midline shift, but basal cisterns were compressed with multiple small hemorrhages. What is the diagnosis?
A. cortical contusion
B. Cerebral laceration
C. Multiple infarcts
D. Diffuse axonal injuries"""

result = parse_tony_html(raw_text)
print(json.dumps(result, indent=2))
