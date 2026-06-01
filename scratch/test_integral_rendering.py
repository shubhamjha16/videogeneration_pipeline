import os
import sys
sys.path.append(os.path.abspath("."))

from explainer_slides_generator import format_math_for_pillow

def test_integral():
    expr = r"If f(x) = \int_{1}^{x} \frac{\ln t}{1+t}\,dt, then find the value of f(e) + f(1/e):"
    formatted = format_math_for_pillow(expr)
    print("Original LaTeX:")
    print(f"  {expr}")
    print("\nFormatted for Pillow:")
    print(f"  {formatted}")
    
    # Check if there are any backslashes or brackets that look un-academic
    if "\\" in formatted:
        print("❌ Warning: There is a residual backslash in the formatted output!")
    else:
        print("✅ Success: No backslashes found!")

if __name__ == "__main__":
    test_integral()
