import sympy
import re

def parse_latex_math(expr):
    expr = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r'((\1)/(\2))', expr)
    expr = expr.replace(r'\times', '*')
    expr = expr.replace(r'\cdot', '*')
    expr = expr.replace(r'\%', '/100')
    expr = re.sub(r'\\text\{[^}]+\}', '', expr)
    expr = re.sub(r'[a-zA-Z]+', '', expr) # Drop letters for pure number eval
    return expr

steps = [
    r"EF = \frac{120-50}{120} = 0.65"
]

def check_numerical_sanity(steps):
    last_num = None
    for s in steps:
        parts = s.split('=')
        for part in parts:
            parsed = parse_latex_math(part.strip())
            if not parsed: continue
            try:
                expr = sympy.sympify(parsed)
                if expr.is_number:
                    val = float(expr.evalf())
                    if last_num is not None:
                        if abs(val - last_num) > 0.02:
                            return f"MATH ERROR: {val} != {last_num}"
                    last_num = val
                else:
                    last_num = None
            except:
                last_num = None
    return "Sanity Check Passed"

print(check_numerical_sanity(steps))
