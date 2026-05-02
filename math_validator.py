import re
import sympy

def parse_latex_math(expr: str) -> str:
    """Convert basic LaTeX math into a format Sympy can evaluate."""
    # Convert fractions: \frac{A}{B} -> ((A)/(B))
    expr = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'((\1)/(\2))', expr)
    expr = expr.replace(r'\times', '*')
    expr = expr.replace(r'\cdot', '*')
    expr = expr.replace(r'\%', '/100')
    expr = re.sub(r'\\text\{[^}]+\}', '', expr)
    expr = re.sub(r'[a-zA-Z]+', '', expr)  # Aggressively strip variables for pure numerical eval
    return expr

def check_numerical_sanity(steps: list[str]) -> bool:
    """
    Validates a list of derivation steps.
    Returns True if mathematically sane, False if an explicit numerical hallucination is found.
    """
    last_num = None
    for s in steps:
        parts = s.split('=')
        for part in parts:
            parsed = parse_latex_math(part.strip())
            if not parsed:
                continue
            try:
                expr = sympy.sympify(parsed)
                if expr.is_number:
                    val = float(expr.evalf())
                    if last_num is not None:
                        # Allow 2% rounding drift
                        if abs(val - last_num) > 0.02:
                            print(f"   ❌ MATH ERROR: {val} != {last_num} (in step: '{s}')")
                            return False
                    last_num = val
                else:
                    # Reset the chain if a part is symbolic and cannot be evaluated
                    last_num = None
            except Exception:
                # Ignore unparseable parts
                last_num = None
    return True
