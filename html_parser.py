"""
Step 1: HTML Parser (Deterministic)
Extracts structured facts from Tony AI HTML lesson pages.

Supports content types:
  mcq        - Multiple choice (FMGE medical, UPSC, English grammar)
  numerical  - Step-by-step problem solving (JEE Physics, JEE Maths)
  concept    - Pure concept explanation (JEE Chemistry, Biology)
  case_study - Analytical reasoning (MBA, UPSC essay)

Output schema (common fields):
{
    "topic": str,
    "subject": str,           # "medical" | "physics" | "maths" | "chemistry" | "english" | "upsc" | "mba" | "unknown"
    "content_type": str,      # "mcq" | "numerical" | "concept" | "case_study"
    "concept": str,           # main body text / explanation
    "sections": dict,         # {heading: body_text} for all detected sections
    --- MCQ only ---
    "options": {
        "A": {"name": str, "explanation": str},
        ...
    },
    "correct_answer": str,
    "correct_answer_name": str,
    --- numerical only ---
    "steps": list[str],       # ordered solution steps
    "formula": str,           # key formula if present
    "final_answer": str,
    --- shared ---
    "citations": list[str],
    "key_points": list[str],  # bullet facts, if any
}
"""

import re
from typing import Any
from bs4 import BeautifulSoup


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def _extract_letter(raw: str) -> str:
    m = re.search(r'\b([A-D]|[1-4])\b', raw, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def _heading_text(tag) -> str:
    return _clean(tag.get_text()).lower()


def _body_after_heading(heading_tag) -> str:
    """Collect all text between this heading and the next same-level heading."""
    parts = []
    for sib in heading_tag.next_siblings:
        if sib.name in ['h1', 'h2', 'h3', 'h4']:
            break
        if hasattr(sib, 'get_text'):
            t = _clean(sib.get_text(separator=' '))
            if t:
                parts.append(t)
    return ' '.join(parts)


# ── Subject detection ─────────────────────────────────────────────────────────

_SUBJECT_KEYWORDS = {
    "medical":   ["anatomy", "physiology", "pharmacology", "pathology", "artery", "vein",
                  "surgery", "clinical", "fmge", "usmle", "disease", "syndrome", "drug",
                  "calcium", "cardiac", "pulmonary", "hepatic", "renal", "fistula",
                  "forensic", "skull", "fracture", "trauma", "orthopedics", "bone",
                  "cardiovascular", "ventricular", "atrial", "septal", "stenosis",
                  "tetralogy", "fallot", "congenital", "heart", "defect", "cyanotic"],
    "physics":   ["velocity", "acceleration", "force", "momentum", "kinetic", "potential",
                  "newton", "thermodynamics", "wave", "optics", "circuit", "magnetic",
                  "electric", "jee", "kinematics", "displacement", "torque"],
    "maths":     ["integral", "derivative", "differentiate", "matrix", "determinant",
                  "probability", "permutation", "combination", "logarithm", "trigonometry",
                  "quadratic", "polynomial", "calculus", "limit", "series"],
    "chemistry": ["atom", "molecule", "bond", "orbital", "electron", "reaction", "acid",
                  "base", "oxidation", "reduction", "periodic", "bohr", "hybridization",
                  "equilibrium", "entropy", "enthalpy"],
    "english":   ["grammar", "verb", "noun", "tense", "sentence", "preposition", "pronoun",
                  "comprehension", "vocabulary", "synonym", "antonym", "subject-verb"],
    "upsc":      ["constitution", "parliament", "policy", "governance", "history", "geography",
                  "economy", "polity", "directive", "fundamental", "amendment", "article"],
    "mba":       ["startup", "business", "market", "strategy", "case", "revenue", "churn",
                  "customer", "operations", "stakeholder", "roi", "supply chain"],
}

def _detect_subject(text: str) -> str:
    text_lower = text.lower()
    scores = {subj: 0 for subj in _SUBJECT_KEYWORDS}
    for subj, keywords in _SUBJECT_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                scores[subj] += 1
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "unknown"


# ── Content type detection ────────────────────────────────────────────────────

def _detect_content_type(soup: BeautifulSoup, full_text: str) -> str:
    headings = [_heading_text(h) for h in soup.find_all(['h2', 'h3'])]

    # MCQ: has option analysis or A/B/C/D pattern or options list
    has_options_heading = any('option' in h or 'analysis' in h for h in headings)
    # Refined: Require at least two [A-D]. markers to avoid false positives on simple lists
    has_abcd = len(re.findall(r'\b[A-D]\.\s+\w', full_text)) >= 2
    has_correct = any('correct' in h or 'answer' in h for h in headings)
    
    # Only allow numeric options if there is also an options heading or correct answer indicator in the text
    has_numeric_options = len(re.findall(r'\b[1-4]\.\s+\w', full_text)) >= 4 and (
        has_options_heading or has_correct or "answer" in full_text.lower() or "correct" in full_text.lower()
    )
    
    if has_options_heading or has_abcd or has_correct or has_numeric_options:
        return "mcq"

    # Case study: check before numerical — business text has step words too
    has_case = any(k in full_text.lower() for k in ['case', 'analyze', 'prioritize', 'strategy', 'recommend', 'startup', 'churn', 'revenue', 'stakeholder'])
    if has_case:
        return "case_study"

    # Numerical: formula present OR multiple sentence-starting step markers
    has_formula = bool(re.search(r'[=∫∑∏√±×÷]|d\/dx|lim\s|integral', full_text))
    step_starters = re.findall(
        r'(?:^|(?<=\. ))(first,|second,|next,|then,|step \d|finally,|solving|differentiating|integrating)',
        full_text.lower()
    )
    if has_formula or len(step_starters) >= 2:
        return "numerical"

    # Default: concept explanation
    return "concept"


# ── Section extractor ─────────────────────────────────────────────────────────

def _extract_all_sections(soup: BeautifulSoup) -> dict:
    """Return {heading_text: body_text} for every h2/h3 section."""
    sections = {}
    for h in soup.find_all(['h2', 'h3']):
        heading = _clean(h.get_text())
        body = _body_after_heading(h)
        if heading and body:
            sections[heading] = body
    return sections


# ── MCQ extractors ────────────────────────────────────────────────────────────

def _extract_options(soup: BeautifulSoup) -> dict:
    options = {}

    # Format 1: <ul><li><strong>A. Name</strong> explanation</li></ul>
    for h in soup.find_all(['h2', 'h3']):
        if 'option' not in _heading_text(h):
            continue
        ul = h.find_next('ul')
        if ul:
            for li in ul.find_all('li'):
                strong = li.find('strong')
                if not strong:
                    continue
                header = _clean(strong.get_text())
                letter = _extract_letter(header)
                if not letter:
                    continue
                name = re.sub(r'^[A-D1-4][.\s]+', '', header).strip()
                strong.extract()
                explanation = _clean(li.get_text(separator=' '))
                options[letter] = {"name": name, "explanation": explanation}

    # Format 2: <p><strong>Option A: Name</strong><br>explanation</p>
    if not options:
        for h in soup.find_all(['h2', 'h3']):
            if 'option' not in _heading_text(h):
                continue
            for sib in h.next_siblings:
                if getattr(sib, 'name', None) in ['h2', 'h3']:
                    break
                if getattr(sib, 'name', None) != 'p':
                    continue
                strong = sib.find('strong')
                if not strong:
                    continue
                header = _clean(strong.get_text())
                letter = _extract_letter(header)
                if not letter:
                    continue
                name = re.sub(r'^(Option\s+)?[A-D1-4][.:\s]+', '', header, flags=re.IGNORECASE).strip()
                strong.extract()
                explanation = _clean(sib.get_text(separator=' '))
                options[letter] = {"name": name, "explanation": explanation}
    # Format 4: <h3>Option A: Name</h3> or <h3>A. Name</h3> or <h3>Option A) Name</h3>
    if not options:
        for h in soup.find_all(['h2', 'h3', 'h4']):
            header = _clean(h.get_text())
            m = re.search(r'(?i)^(?:Option\s+)?([A-D]|[1-4])[.:\)\s]+(.*)', header)
            if m:
                letter = m.group(1).upper()
                name = m.group(2).strip()
                # Explanation is the body text after this heading
                explanation = _clean(_body_after_heading(h))
                options[letter] = {"name": name, "explanation": explanation}

    # Format 3: Raw text A. B. C. D. patterns (No headings)
    if not options:
        # Look for lines starting with A., B., C., or D.
        # This handles raw text copy-pastes and avoids numbered concept lists
        matches = re.finditer(r'(?i)^\s*([A-D]|[1-4])[.\)]\s+(.+)', soup.get_text(separator="\n"), re.MULTILINE)
        for m in matches:
            letter = m.group(1).upper()
            name = _clean(m.group(2))
            options[letter] = {"name": name, "explanation": ""}

    return options


def _extract_correct_answer(soup: BeautifulSoup) -> tuple:
    # 1. High Priority: Look for dedicated headings (Final Answer, etc.)
    for h in soup.find_all(['h2', 'h3']):
        ht = _heading_text(h)
        if any(k in ht for k in ['final answer', 'conclusion', 'master answer', 'correct answer']):
            # Robustly find the next content block (skipping whitespace)
            ans_tag = h.find_next_sibling(['p', 'div', 'li', 'span'])
            if ans_tag:
                raw = _clean(ans_tag.get_text(separator=' '))
                letter = _extract_letter(raw)
                if letter:
                    # Try to get the name that follows
                    nm_name = re.search(rf'{letter}[.:\s]+(.+?)(?:\.|$)', raw, re.IGNORECASE)
                    name = _clean(nm_name.group(1)) if nm_name else ""
                    return letter, name

    # 2. Medium Priority: Look for "Correct answer is X" patterns anywhere
    for p in soup.find_all(['p', 'div', 'li']):
        raw = _clean(p.get_text(separator=' '))
        # Target specific patterns: "Answer is C", "Correct: B", "Ans: D"
        nm = re.search(r'\b(?:answer|correct|ans|is)\s+([A-D])\b', raw, re.IGNORECASE)
        if nm:
            letter = nm.group(1).upper()
            nm_name = re.search(rf'{letter}[.:\s]+(.+?)(?:\.|$)', raw, re.IGNORECASE)
            name = _clean(nm_name.group(1)) if nm_name else ""
            return letter, name

    return "", ""


# ── Numerical extractors ──────────────────────────────────────────────────────

def _extract_steps(soup: BeautifulSoup, full_text: str) -> list:
    """Extract ordered solution steps from numbered lists or sentence patterns."""
    steps = []

    # Numbered list
    for ol in soup.find_all('ol'):
        for li in ol.find_all('li'):
            t = _clean(li.get_text(separator=' '))
            if t:
                steps.append(t)
    if steps:
        return steps

    # Sentence-based: split on step indicators
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    step_markers = ['first', 'second', 'third', 'next', 'then', 'finally',
                    'step 1', 'step 2', 'step 3', 'now', 'therefore', 'thus']
    for sent in sentences:
        if any(sent.lower().startswith(m) for m in step_markers):
            steps.append(sent.strip())

    return steps if steps else sentences[:6]  # fallback: first 6 sentences


def _extract_formula(full_text: str) -> str:
    """Find the most prominent formula in the text."""
    patterns = [
        r'[a-zA-Z]\s*=\s*[^\.,;]{5,40}',           # x = something
        r'∫[^d]*d[a-z]',                             # integral expressions
        r'd/dx\s*\([^)]+\)',                          # derivatives
        r'\b[A-Z]\s*=\s*[A-Z]\s*[×x]\s*[A-Z]',      # physics: CO = HR × SV
    ]
    for pattern in patterns:
        m = re.search(pattern, full_text)
        if m:
            return _clean(m.group())
    return ""


def _extract_final_answer(soup: BeautifulSoup, full_text: str) -> str:
    for h in soup.find_all(['h2', 'h3']):
        if any(k in _heading_text(h) for k in ['answer', 'result', 'conclusion', 'final']):
            body = _body_after_heading(h)
            if body:
                return body

    # Fallback: last sentence often contains the answer
    sentences = [s.strip() for s in full_text.split('.') if s.strip()]
    return sentences[-1] if sentences else ""


# ── Key points / bullets ──────────────────────────────────────────────────────

def _extract_key_points(soup: BeautifulSoup) -> list:
    points = []
    for ul in soup.find_all('ul'):
        for li in ul.find_all('li'):
            # skip option lists (already handled)
            strong = li.find('strong')
            if strong and _extract_letter(strong.get_text()):
                continue
            t = _clean(li.get_text(separator=' '))
            if t and len(t) > 10:
                points.append(t)
    return points


def _extract_citations(soup: BeautifulSoup) -> list:
    citations = []
    in_citations = False
    for tag in soup.find_all(['h2', 'h3', 'li', 'p']):
        if tag.name in ['h2', 'h3']:
            in_citations = 'citation' in _heading_text(tag)
            continue
        if in_citations and tag.name in ['li', 'p']:
            t = _clean(tag.get_text(separator=' '))
            if t:
                citations.append(t)
    return citations


# ── Topic inference ───────────────────────────────────────────────────────────

def _infer_topic(soup: BeautifulSoup, hint: str) -> str:
    if hint:
        return hint
    if soup.title and soup.title.string:
        return _clean(soup.title.string.split(':')[0])
    for tag in soup.find_all(['h1', 'h2']):
        text = _clean(tag.get_text())
        if text and not any(k in text.lower() for k in ['concept', 'option', 'citation', 'answer']):
            return text
    return "Lesson"


# ── Concept / main body text ──────────────────────────────────────────────────

def _extract_concept(soup: BeautifulSoup) -> str:
    for h in soup.find_all(['h2', 'h3']):
        ht = _heading_text(h)
        if 'concept' in ht or 'explanation' in ht:
            return _body_after_heading(h)

    # No heading found — get all paragraph text
    paras = [_clean(p.get_text(separator=' ')) for p in soup.find_all('p')]
    return ' '.join(p for p in paras if len(p) > 40)[:1500]


# ── Public API ────────────────────────────────────────────────────────────────

def _item_to_html(item: Any) -> str:
    """Industrial Sentinel: Convert any input item to a safe HTML snippet for parsing."""
    import json
    
    if isinstance(item, dict):
        # Handle structured JSON
        t = item.get("title") or item.get("heading") or item.get("label", "")
        d = item.get("description") or item.get("content") or item.get("body", "")
        
        # ── MCQ Support: question, options, answer, explanation ──
        q = item.get("question")
        o = item.get("options")
        a = item.get("answer")
        e = item.get("explanation")
        
        res = ""
        if t: res += f"<h3>{t}</h3>\n"
        if d:
            res += _item_to_html(d)
            
        if q: res += f"<div class='question'><h3>Question</h3><p>{q}</p></div>\n"
        if isinstance(o, list):
            res += "<h3>Options</h3><ul>\n"
            for opt in o:
                if isinstance(opt, dict):
                    letter = opt.get("letter", "")
                    name = opt.get("name", "")
                    res += f"<li><strong>Option {letter}: {name}</strong></li>\n"
                else:
                    res += f"<li>{opt}</li>\n"
            res += "</ul>\n"
        elif isinstance(o, dict):
            res += "<h3>Options</h3><ul>\n"
            for letter, val in o.items():
                name = val.get("name") if isinstance(val, dict) else str(val)
                res += f"<li><strong>Option {letter}: {name}</strong></li>\n"
            res += "</ul>\n"
            
        if a: res += f"<h3>Final Answer</h3><p>Option {a}</p>\n"
        if e: res += f"<h3>Explanation</h3><p>{e}</p>\n"
        
        return res
    
    s = str(item).strip()
    
    # ── 1. Detect JSON String ──
    if (s.startswith("{") or s.startswith("[")) and (s.endswith("}") or s.endswith("]")):
        try:
            parsed_json = json.loads(s)
            return _item_to_html(parsed_json)
        except: pass

    # ── 2. Detect HTML ──
    if s.startswith("<") and ">" in s:
        return s
    
    # ── 3. Detect Markdown & LaTeX ──
    # Check for ### headers, **bold**, or $ LaTeX markers
    if "###" in s or "**" in s or "- " in s or "$" in s:
        # Simple Industrial Markdown-to-HTML converter with LaTeX preservation
        html = ""
        lines = s.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("###"):
                html += f"<h3>{line.replace('###', '').strip()}</h3>\n"
            elif line.startswith("##"):
                html += f"<h2>{line.replace('##', '').strip()}</h2>\n"
            elif line.startswith("#"):
                html += f"<h1>{line.replace('#', '').strip()}</h1>\n"
            elif line.startswith("- "):
                html += f"<li>{line[2:]}</li>\n"
            elif line:
                # Handle bolding
                line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                # Handle LaTeX: we preserve $ and $$ for the director/architect
                html += f"<p>{line}</p>\n"
        return html
    
    # ── 4. Default Text ──
    return f"<p>{s}</p>"


def parse_tony_html(input_data: Any, topic_hint: str = "") -> dict:
    """Industrial Sentinel: Universal Input Dispatcher (Handles JSON, Markdown, HTML, or Raw Text)."""
    import json
    
    # Handle solutionV2 format from Spring Boot ask-tony-ai
    options_from_v2 = {}
    if isinstance(input_data, list) and all(
        isinstance(item, dict) and "title" in item and "description" in item 
        for item in input_data
    ):
        # Convert solutionV2 sections to HTML
        html_parts = []
        for section in input_data:
            title = section.get("title", "")
            desc = section.get("description", "")
            html_parts.append(f"<h2>{title}</h2><div>{desc}</div>")
            
            # Greedy Option Extraction for MCQ
            if "Option Analysis" in title:
                # Use a robust split approach: find all [A-D]. or [A-D]) markers
                # We use ([A-D]) to capture the letter and keep it in the parts list
                parts = re.split(r'\s*([A-D])[.\)]\s*', desc)
                # parts will be [pre-text, 'A', 'text', 'B', 'text'...]
                for i in range(1, len(parts), 2):
                    if i + 1 < len(parts):
                        letter = parts[i].upper()
                        content = parts[i+1].strip()
                        
                        # Name extraction: Take text before first dash, colon or period
                        name = content
                        # Industrial refinement: Check for multiple separators and take the shortest name candidate
                        candidates = [content]
                        for sep in [" - ", ": ", ". "]:
                            if sep in content:
                                candidates.append(content.split(sep, 1)[0].strip())
                        
                        # Filter out single-character candidates that might be literal dashes
                        valid_candidates = [c for c in candidates if len(c) > 1 or c.isalnum()]
                        name = min(valid_candidates, key=len) if valid_candidates else content
                        
                        if len(name) > 40: name = name[:37] + "..."
                        options_from_v2[letter] = {"name": name, "explanation": content}

        input_data = "\n".join(html_parts)

    # ── 1. Input Normalization (Polymorphic Dispatcher) ──
    html = ""
    
    # [NEW] Handle Composite Lists (Multiple inputs appended)
    if isinstance(input_data, list):
        html = "<html><body>"
        for item in input_data:
            html += _item_to_html(item)
            html += "\n<hr/>\n" # Visual separator for the parser
        html += "</body></html>"
    elif isinstance(input_data, dict):
        # 2. STRUCTURED JSON: Direct curriculum object
        if "topic" in input_data and ("concept" in input_data or "options" in input_data):
            return input_data # Already structured
        
        # Fallback: Extract from dict fields or convert to HTML
        html = _item_to_html(input_data)
    else:
        # 3. RAW STRING: Markdown or HTML
        html = _item_to_html(input_data)

    soup = BeautifulSoup(html, 'html.parser')
    
    raw_text = soup.get_text(separator='\n')
    full_text = _clean(raw_text)

    # Extraction phase (Structure must be intact)
    topic        = _infer_topic(soup, topic_hint)
    subject      = _detect_subject(full_text)
    content_type = _detect_content_type(soup, full_text)
    
    extracted_opts = _extract_options(soup)
    # 🚨 INDUSTRIAL OVERRIDE: If we have options, it IS an MCQ.
    if options_from_v2 or extracted_opts:
        content_type = "mcq"


    
    # ── 2. Structural Slicing ──
    detected_options = {}
    if content_type == "mcq" and not options_from_v2:
        all_markers = []
        for m in re.finditer(r'###', raw_text):
            all_markers.append({"pos": m.start(), "end": m.end(), "type": "header", "val": "###"})
        # Refined label regex: handles A, B, C, D and 1, 2, 3, 4 even with complex prefixes
        for m in re.finditer(r'(?i)(?:Option\s+)?([A-D]|[1-4])[.\)]', raw_text):
            all_markers.append({"pos": m.start(), "end": m.end(), "type": "label", "val": m.group(1).upper()})
        
        all_markers.sort(key=lambda x: x["pos"])
        
        current_header = ""
        for i, marker in enumerate(all_markers):
            start_idx = marker["end"]
            end_idx = all_markers[i+1]["pos"] if i + 1 < len(all_markers) else len(raw_text)
            chunk = raw_text[start_idx:end_idx].strip()
            
            if marker["type"] == "header":
                current_header = "### " + chunk.split('\n')[0].strip()
            elif marker["type"] == "label":
                letter = marker["val"]
                # This chunk is the clinical name/text for this label
                # We stop if we hit a newline followed by a block marker
                content = re.split(r'\n\n|###', chunk)[0].strip()
                full_name = f"{current_header}\n{content}" if current_header else content
                detected_options[letter] = {"name": full_name, "explanation": ""}

    concept      = _extract_concept(soup)
    sections     = _extract_all_sections(soup)
    citations    = _extract_citations(soup)
    key_points   = _extract_key_points(soup)

    result = {
        "topic":        topic,
        "subject":      subject,
        "content_type": content_type,
        "concept":      concept,
        "sections":     sections,
        "citations":    citations,
        "key_points":   key_points,
    }

    if content_type == "mcq":
        options = extracted_opts
        
        # INDUSTRIAL OVERRIDE: Prioritize solutionV2 extraction absolutely
        if options_from_v2:
            options = options_from_v2

        if not options:
            options = detected_options
        else:
            for letter, data in detected_options.items():
                if letter not in options or not options[letter].get("name"):
                    options[letter] = data
        
        correct_answer, correct_answer_name = _extract_correct_answer(soup)
        if correct_answer and not correct_answer_name and correct_answer in options:
            correct_answer_name = options[correct_answer]["name"]
        result.update({
            "options":             options,
            "correct_answer":      correct_answer,
            "correct_answer_name": correct_answer_name,
        })

    elif content_type == "numerical":
        result.update({
            "steps":        _extract_steps(soup, full_text),
            "formula":      _extract_formula(full_text),
            "final_answer": _extract_final_answer(soup, full_text),
        })

    elif content_type in ("concept", "case_study"):
        result.update({
            "final_answer": _extract_final_answer(soup, full_text),
        })

    # ── [NEW] Preservation Layer: Re-inject Markdown markers into HTML for the Director ──
    # This ensures that even after HTML parsing, bolding and headers are visible as text.
    for tag in soup.find_all(['strong', 'b']):
        tag.replace_with(f"**{tag.get_text()}**")
    for tag in soup.find_all(['h1', 'h2', 'h3']):
        tag.replace_with(f"\n### {tag.get_text()}\n")
    
    # Final metadata assembly
    result["html_content"] = str(soup)

    return result



# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, sys

    path = sys.argv[1] if len(sys.argv) > 1 else "bpf_source.html"
    topic = sys.argv[2] if len(sys.argv) > 2 else ""

    # Support plain .txt files for testing JEE content
    with open(path) as f:
        raw = f.read()

    if path.endswith(".txt"):
        html = f"<html><body><p>{raw}</p></body></html>"
    else:
        html = raw

    result = parse_tony_html(html, topic_hint=topic)
    print(json.dumps(result, indent=2))
