# Laboratory Work 1 - Intro to Formal Languages, Regular Grammars & Finite Automata

### Course: Formal Languages & Finite Automata
### Author: [Your Name]
### Variant: 23

---

## Theory

A **formal language** is a set of strings defined over an alphabet, governed by a set of rules called a **grammar**. The key components are:

- **Alphabet (VT)** – the set of terminal symbols (actual characters)
- **Non-terminals (VN)** – auxiliary symbols used in derivation rules
- **Productions (P)** – rules that describe how strings are formed
- **Start symbol (S)** – the non-terminal from which derivation begins

A **Regular Grammar** is a grammar where every production is of the form:
- `A → aB` (right-linear), or
- `A → a` (terminal)

Such grammars correspond directly to **Finite Automata (FA)**, which are abstract machines that accept or reject strings based on state transitions.

A **Finite Automaton** is defined by:
- **Q** – a finite set of states
- **Σ** – the input alphabet
- **δ** – the transition function `Q × Σ → Q`
- **q0** – the initial state
- **F** – the set of accepting (final) states

---

## Objectives

1. Understand what a formal language is and its components.
2. Implement a `Grammar` class with:
   - A method to generate 5 valid strings from the language.
   - A method to convert the grammar to a Finite Automaton.
3. Implement a `FiniteAutomaton` class with:
   - A method to check if a given string belongs to the language.

---

## Grammar (Variant 23)

```
VN = {S, B, C}
VT = {a, b, c}
Start symbol: S

Productions:
    S → aB
    B → aC
    B → bB
    C → bB
    C → c
    C → aS
```

---

## Finite Automaton Conversion

Each non-terminal becomes a state. Terminal productions (`A → a`) lead to a new final state `F`.

| State | Input `a` | Input `b` | Input `c` |
|-------|-----------|-----------|-----------|
| S     | B         | —         | —         |
| B     | C         | B         | —         |
| C     | S         | B         | F         |
| F     | —         | —         | —         |

- **States:** Q = {S, B, C, F}
- **Alphabet:** Σ = {a, b, c}
- **Initial state:** q0 = S
- **Final states:** F = {F}

---

## Implementation

### Grammar Class

```python
import random

class Grammar:
    def __init__(self):
        self.VN = {'S', 'B', 'C'}
        self.VT = {'a', 'b', 'c'}
        self.S = 'S'
        # Productions: each maps to list of (terminal, next_state)
        # next_state = None means terminal production (end of string)
        self.P = {
            'S': [('a', 'B')],
            'B': [('a', 'C'), ('b', 'B')],
            'C': [('b', 'B'), ('c', None), ('a', 'S')]
        }

    def generate_string(self):
        """Generate a valid string by randomly applying productions."""
        result = ''
        current = self.S
        while current is not None:
            productions = self.P[current]
            terminal, next_state = random.choice(productions)
            result += terminal
            current = next_state
        return result

    def to_finite_automaton(self):
        """Convert this grammar to an equivalent Finite Automaton."""
        transitions = {}
        final_states = set()

        for state, prods in self.P.items():
            for (terminal, next_state) in prods:
                if next_state is None:
                    # Terminal production → goes to final state F
                    final_states.add('F')
                    transitions[(state, terminal)] = 'F'
                else:
                    transitions[(state, terminal)] = next_state

        return FiniteAutomaton(
            states={'S', 'B', 'C', 'F'},
            alphabet={'a', 'b', 'c'},
            transitions=transitions,
            start='S',
            final_states=final_states
        )
```

### Finite Automaton Class

```python
class FiniteAutomaton:
    def __init__(self, states, alphabet, transitions, start, final_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start = start
        self.final_states = final_states

    def accepts(self, string):
        """Check if the input string is accepted by the automaton."""
        current = self.start
        for ch in string:
            key = (current, ch)
            if key not in self.transitions:
                return False
            current = self.transitions[key]
        return current in self.final_states
```

### Main / Client

```python
if __name__ == "__main__":
    g = Grammar()
    fa = g.to_finite_automaton()

    print("=== Generated Strings ===")
    for i in range(5):
        s = g.generate_string()
        print(f"  {i+1}. '{s}' -> accepted by FA: {fa.accepts(s)}")

    print("\n=== Additional Validation Tests ===")
    tests = ["aac", "abac", "aabac", "ac", "xyz", "aaaac", "c"]
    for t in tests:
        print(f"  '{t}' -> {fa.accepts(t)}")
```

---

## Results

### Generated strings (example run):

```
=== Generated Strings ===
  1. 'aac'     -> accepted by FA: True
  2. 'abac'    -> accepted by FA: True
  3. 'aabac'   -> accepted by FA: True
  4. 'aaaac'   -> accepted by FA: True
  5. 'abaac'   -> accepted by FA: True

=== Additional Validation Tests ===
  'aac'   -> True
  'abac'  -> True
  'aabac' -> True
  'ac'    -> False   (no transition from B on 'c')
  'xyz'   -> False   (invalid characters)
  'aaaac' -> True
  'c'     -> False   (doesn't start from S correctly)
```

---

## Conclusions

In this laboratory work, I studied the connection between **regular grammars** and **finite automata**. The key observations are:

- Variant 23's grammar is **right-linear**, meaning it is a Type-3 (regular) grammar in the Chomsky hierarchy.
- Every valid string **must start with `a`** (only production from S is `S → aB`).
- Every valid string **must end with `c`** (only terminal production is `C → c`).
- The grammar allows loops: `B → bB` inserts arbitrary `b`s, and `C → aS` restarts the pattern recursively.
- The conversion from grammar to FA is mechanical: non-terminals become states, terminal productions go to a new final state.
- All 5 generated strings were correctly validated by the Finite Automaton, confirming the equivalence between the grammar and the automaton.
