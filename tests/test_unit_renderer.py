import pytest
from template_renderer import tex, math, DesignTokens, _option_position

def test_tex_sanitization():
    # Test bold conversion
    result = tex("**Bold Text**")
    assert "\\textbf{Bold Text}" in result
    
    # Test special character escaping
    result = tex("Price is $10 & 100% discount")
    assert "\\\\$" in result
    assert "\\\\&" in result
    assert "\\\\%" in result

def test_tex_wrapping():
    # Test long text wrapping into VGroup
    long_text = "This is a very long sentence that should definitely trigger the wrapping logic in our template renderer to prevent screen overflow."
    result = tex(long_text, width=20)
    assert "VGroup" in result
    assert "arrange(DOWN" in result

def test_math_scaling():
    result = math("a^2 + b^2 = c^2")
    assert "MathTex" in result
    assert "scale(1.2)" in result

def test_option_positions():
    # Ensure numeric and letter positions match
    pos_a = _option_position("A")
    pos_1 = _option_position("1")
    assert pos_a == pos_1
    assert "np.array([-3.2,  1.2, 0])" in pos_a
    
    pos_unknown = _option_position("Z")
    assert "np.array([0, 0, 0])" in pos_unknown
