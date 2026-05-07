from math_validator import check_numerical_sanity

print("🔍 Testing Mathematical Safety Net...")

# Case 1: Correct Derivation
correct_steps = [
    r"EF = \frac{SV}{EDV}",
    r"EF = \frac{120 - 50}{120}",
    r"EF = \frac{70}{120}",
    r"EF = 0.583"
]
is_sane = check_numerical_sanity(correct_steps)
print(f"\n[Test 1] Correct Derivation:")
print(f"   Is Sane: {is_sane}")


# Case 2: Hallucinated Derivation (The AI "guesses" the wrong result)
hallucinated_steps = [
    r"EF = \frac{SV}{EDV}",
    r"EF = \frac{120 - 50}{120}",
    r"EF = 0.95"  # <--- WRONG! 70/120 is not 0.95
]
is_sane = check_numerical_sanity(hallucinated_steps)
print(f"\n[Test 2] Hallucinated Derivation (Arithmetic Error):")
print(f"   Is Sane: {is_sane}")


if not is_sane:
    print("\n✅ Safety Net Triggered: Logic would ABORT render here.")

