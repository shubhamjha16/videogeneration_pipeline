import re

def test_slash_conversion():
    test_cases = [
        ("If f(e) + f(1/e):", "If f(e) + f(\\frac{1}{e}):"),
        ("Option C: 1/2", "Option C: \\frac{1}{2}"),
        ("x/y", "\\frac{x}{y}"),
        ("1 / 2", "\\frac{1}{2}"),
    ]
    
    pattern = r'\b([0-9a-zA-Zα-ωΑ-Ω]+)\s*/\s*([0-9a-zA-Zα-ωΑ-Ω]+)\b'
    
    for inp, expected in test_cases:
        output = re.sub(pattern, r'\\frac{\1}{\2}', inp)
        if output == expected:
            print(f"✅ Success: '{inp}' -> '{output}'")
        else:
            print(f"❌ Failure!")
            print(f"  Input:    {inp}")
            print(f"  Output:   {output}")
            print(f"  Expected: {expected}")

if __name__ == "__main__":
    test_slash_conversion()
