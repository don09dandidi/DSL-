"""
Lab 2 — Determinism in FA, NDFA→DFA, Chomsky Hierarchy
Course:  Formal Languages & Finite Automata
Student: Strunga Daniel-Ioan, FAF-242
Variant: 23
"""

from finite_automaton import FiniteAutomaton
from grammar import Grammar


def separator(title):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print('='*55)


# ----------------------------------------------------------------
# Variant 23
# Q  = {q0, q1, q2}
# Σ  = {a, b}
# F  = {q2}
# δ(q0,a) = q0
# δ(q0,a) = q1   <-- non-deterministic! same (q0,a) → two targets
# δ(q1,b) = q2
# δ(q0,b) = q0
# δ(q2,b) = q2
# δ(q1,a) = q0
# ----------------------------------------------------------------
Q     = {'q0', 'q1', 'q2'}
Sigma = {'a', 'b'}
delta = {
    'q0': {
        'a': ['q0', 'q1'],  # NDFA: two transitions on 'a'
        'b': ['q0'],
    },
    'q1': {
        'b': ['q2'],
        'a': ['q0'],
    },
    'q2': {
        'b': ['q2'],
    },
}
q0 = 'q0'
F  = {'q2'}

fa = FiniteAutomaton(Q, Sigma, delta, q0, F)
print(fa)


# ----------------------------------------------------------------
# 3b  Is it deterministic?
# ----------------------------------------------------------------
separator("3b — DFA or NDFA?")
det = fa.is_deterministic()
print(f"  The automaton is: {'DFA (Deterministic)' if det else 'NDFA (Non-Deterministic)'}")
if not det:
    print("  Reason: δ(q0,a) = q0  AND  δ(q0,a) = q1")
    print("          → same state + symbol leads to multiple states")


# ----------------------------------------------------------------
# 3a  FA → Regular Grammar
# ----------------------------------------------------------------
separator("3a — FA → Regular Grammar")
grammar = fa.to_regular_grammar()
print(f"  VN = {sorted(grammar.VN)}")
print(f"  VT = {sorted(grammar.VT)}")
print(f"  S  = {grammar.S}")
print("  Productions:")
for lhs, prods in sorted(grammar.P.items()):
    if prods:
        print(f"    {lhs} → {' | '.join(prods)}")

separator("Chomsky Classification of derived grammar")
chtype, chdesc = grammar.classify_chomsky()
print(f"  {chdesc}")

# Some accepted strings
print("\n  Sample accepted strings:")
for s in grammar.generate_strings(max_length=8, max_count=8):
    print(f"    '{s}'")


# ----------------------------------------------------------------
# 3c  NDFA → DFA  (subset construction)
# ----------------------------------------------------------------
separator("3c — NDFA → DFA  (Subset Construction)")
dfa = fa.to_dfa()
print(f"  DFA States : {sorted(dfa.Q)}")
print(f"  Start      : {dfa.q0}")
print(f"  Final      : {sorted(dfa.F)}")
print("  Transitions:")
for state in sorted(dfa.delta):
    for sym in sorted(dfa.delta[state]):
        target = dfa.delta[state][sym][0]
        print(f"    δ({state}, {sym}) = {target}")

print(f"\n  Verify DFA is now deterministic: {dfa.is_deterministic()}")


# ----------------------------------------------------------------
# Bonus 3d — DOT export
# ----------------------------------------------------------------
separator("Bonus 3d — Graphviz DOT (NDFA)")
print(fa.to_dot())

separator("Bonus 3d — Graphviz DOT (DFA after conversion)")
print(dfa.to_dot())
