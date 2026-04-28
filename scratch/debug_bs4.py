from bs4 import BeautifulSoup
import re

html_numeric = "<html><body><p>1. Alpha<br/>2. Beta</p></body></html>"
soup = BeautifulSoup(html_numeric, "html.parser")
text = soup.get_text(separator="\n")
print(f"TEXT: {repr(text)}")

matches = list(re.finditer(r'(?i)^\s*([A-D1-4])[.\)]\s+(.+)', text, re.MULTILINE))
print(f"MATCHES: {matches}")
