import pytest
import os
import sys
import json
import markdown
from html_parser import parse_tony_html

def test_parse_html_mcq():
    html = """
    <html><body>
    <h2>Option Analysis</h2>
    <ul>
        <li><strong>A. Heart</strong> pumps blood</li>
        <li><strong>B. Lung</strong> breathes air</li>
    </ul>
    <h3>Correct Answer</h3>
    <p>The correct answer is A. Heart.</p>
    </body></html>
    """
    facts = parse_tony_html(html)
    assert facts["content_type"] == "mcq"
    assert facts["options"]["A"]["name"] == "Heart"
    assert facts["correct_answer"] == "A"

def test_parse_markdown_polymorphism():
    md = """
### Physics Lesson
A. 10 m/s
B. 20 m/s

Correct: B
"""
    html = markdown.markdown(md)
    facts = parse_tony_html(html)
    assert facts["content_type"] == "mcq"
    assert "B" in facts["options"]
    assert facts["options"]["B"]["name"] == "20 m/s"

def test_parse_json_direct_support():
    # Test the new direct JSON support in html_parser
    data = {
        "topic": "Direct JSON",
        "options": {"1": {"name": "First"}, "2": {"name": "Second"}},
        "content_type": "mcq"
    }
    facts = parse_tony_html(data)
    assert facts["topic"] == "Direct JSON"
    assert facts["options"]["1"]["name"] == "First"

def test_mcq_label_regex_variants():
    # Test numeric and letter variants
    html_numeric = "<html><body><p>1. Alpha<br/>2. Beta</p></body></html>"
    facts = parse_tony_html(html_numeric)
    assert facts["options"]["1"]["name"] == "Alpha"
    
    html_dots = "<html><body><p>A. Apple<br/>B. Banana</p></body></html>"
    facts_dots = parse_tony_html(html_dots)
    assert facts_dots["options"]["A"]["name"] == "Apple"
