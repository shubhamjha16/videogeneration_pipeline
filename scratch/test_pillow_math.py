import os
import sys

# Add parent directory to path so we can import the local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from explainer_slides_generator import format_math_for_pillow

def run_tests():
    print("🧪 Running Pillow Unicode Math Formatter Unit Tests...")
    
    test_cases = [
        # Exponents (superscripts)
        ("x^2", "x²"),
        ("x^10", "x¹⁰"),
        ("x^{n+1}", "xⁿ⁺¹"),
        ("e^{-x}", "e⁻ˣ"),
        
        # Subscripts
        ("x_1", "x₁"),
        ("a_{ij}", "aᵢⱼ"),
        ("H_2O", "H₂O"),
        
        # Fractions
        ("\\frac{x}{y}", "x/y"),
        ("\\frac{1}{2}", "1/2"),
        ("\\frac{665}{3}", "665/3"),
        ("\\frac{a+b}{2}", "(a+b)/2"),
        
        # Math & Greek Symbols
        ("\\alpha + \\beta = \\theta", "α + β = θ"),
        ("\\sqrt{x^2 + y^2}", "√x² + y²"),
        ("x \\times y \\div z", "x × y ÷ z"),
        ("a \\pm b", "a ± b"),
        
        # Complex Combinations
        ("x^2 - 16x + 25 = 0", "x² - 16x + 25 = 0"),
        ("x_{n+1} = \\frac{x_n + a/x_n}{2}", "xₙ₊₁ = (xₙ + a/xₙ)/2")
    ]
    
    failed = 0
    for idx, (inp, expected) in enumerate(test_cases):
        output = format_math_for_pillow(inp)
        if output == expected:
            print(f"✅ Test {idx+1} Passed: '{inp}' -> '{output}'")
        else:
            print(f"❌ Test {idx+1} Failed!")
            print(f"   Input:    '{inp}'")
            # Convert string to hex values to show detailed character differences
            print(f"   Output:   '{output}'  (Hex: {[hex(ord(c)) for c in output]})")
            print(f"   Expected: '{expected}'  (Hex: {[hex(ord(c)) for c in expected]})")
            failed += 1
            
    if failed == 0:
        print("\n✨ All Unicode Math Formatter tests passed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ {failed} tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
