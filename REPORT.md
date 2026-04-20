# Lab 5 – Chomsky Normal Form

**Course:** Formal Languages & Finite Automata  
**Student:** Strunga Daniel-Ioan  
**Group:** FAF-242  
---

## Theory

A **Context-Free Grammar (CFG)** G = (V_N, V_T, P, S) is in **Chomsky Normal Form (CNF)** if every production rule is of exactly one of two forms:

- **A → BC** — a non-terminal produces exactly two non-terminals
- **A → a**  — a non-terminal produces exactly one terminal

The sole allowed exception: if the empty string ε is in the language, the start symbol may have the production **S → ε**, and S must not appear on any right-hand side.

Any CFG (without ε, unless ε ∈ L(G)) can be converted to CNF. CNF is useful because:
1. It provides a uniform structure that simplifies many proofs about CFLs.
2. It is the canonical form used in the **CYK parsing algorithm** (O(n³)).
3. It is the basis for most tableau-style proofs of the Pumping Lemma.

---

## Objectives

1. Learn about Chomsky Normal Form (CNF).
2. Get familiar with the approaches for normalizing a grammar.
3. Implement a method for normalizing an input grammar by the rules of CNF.
   - Encapsulated in a `Grammar` class with a `.to_cnf()` method.
   - Tested on Variant 23 and on a custom grammar (BONUS).

---

## Implementation

### Class Structure

All logic is encapsulated in a single `Grammar` class in `src/cnf.py`:

```
Grammar
├── __init__(variables, terminals, productions, start)
├── to_cnf() → Grammar          # public API, returns new CNF grammar
│
├── _eliminate_start_from_rhs() # Step 0
├── _eliminate_epsilon()        # Step 1
├── _nullable_symbols()         # helper for step 1
├── _eliminate_unit_productions()# Step 2
├── _unit_closure()             # helper for step 2
├── _eliminate_inaccessible()   # Step 3
├── _eliminate_non_productive() # Step 4
├── _productive_symbols()       # helper for step 4
├── _to_cnf()                   # Step 5 – terminal lift + binarization
├── _fresh_var()                # name generator for new variables
└── __str__()
```

The method `to_cnf()` performs a **deep copy** first and applies five transformation passes to the copy, leaving the original grammar untouched.

---

### Transformation Steps

#### Step 0 — Isolate Start Symbol

A new start symbol S₀ → S is introduced so that S never appears on any right-hand side. This guarantees that the CNF property for the start symbol is not violated by later steps.

```python
new_start = self.start + "0"
self.productions[new_start] = [[self.start]]
self.start = new_start
```

#### Step 1 — Eliminate ε-Productions

First, the set of **nullable** symbols is computed: any non-terminal that can derive ε either directly or transitively. Then, for every production containing a nullable symbol, all subsets of those occurrences are omitted to generate new rules, effectively "pre-expanding" the ε derivations.

```python
# every subset of nullable positions in a rule
for mask in range(1 << len(positions)):
    omit = {positions[j] for j in range(len(positions)) if mask & (1 << j)}
    new_rhs = [sym for i, sym in enumerate(rhs) if i not in omit]
    if new_rhs:
        new_rules.append(new_rhs)
```

#### Step 2 — Eliminate Unit Productions

A **unit production** is A → B where B is a single non-terminal. For each variable A, the **unit closure** (all variables reachable via unit chains) is computed via BFS. Every non-unit rule of any reachable variable is then added to A's rule set directly.

#### Step 3 — Eliminate Inaccessible Symbols

Starting from the start symbol, a BFS marks every variable reachable through the production rules. Variables and their rules that are never reachable are removed.

#### Step 4 — Eliminate Non-Productive Symbols

A variable is **productive** if it can eventually derive a string of terminals. The productive set is grown iteratively (a terminal is trivially productive; A is productive if some rule's RHS consists entirely of productive symbols/terminals). Non-productive variables and any rule containing them are removed.

#### Step 5 — Convert to CNF

Two sub-steps are applied:

**(a) Terminal lifting** — In any rule of length ≥ 2, each terminal `a` is replaced by a new variable `T_A` with the sole rule `T_A → a`.

**(b) Binarization** — Any rule of length ≥ 3 is broken down right-to-left: the last two symbols are replaced by a fresh binary variable. A `pair_map` ensures identical symbol pairs reuse the same variable across all rules (deduplication).

```python
while len(rhs) > 2:
    pair = tuple(rhs[-2:])
    if pair not in pair_map:
        fresh = self._fresh_var("B_" + pair[0] + "_" + pair[1])
        pair_map[pair] = fresh
        extra_prods[fresh] = [list(pair)]
    rhs = rhs[:-2] + [pair_map[pair]]
```

---

## Variant 23 Grammar

**Input:**

```
S → aB | bA | B
A → b | aD | AS | bAAB | ε
B → a | bS | A
C → AB
D → BB
```

**Output (CNF):**

```
S0 → T_A B | a | T_B A | b | T_B S | T_A D | A S | T_B B_A_B_A_B | T_B B_A_B | T_B B | T_B B_A_A
S  → (same as S0)
A  → T_A B | a | T_B A | b | T_B S | T_A D | A S | T_B B_A_B_A_B | T_B B_A_B | T_B B | T_B B_A_A
B  → (same as A)
D  → B B | (inherited from A)
T_A    → a
T_B    → b
B_A_A  → A A
B_A_B  → A B
B_A_B_A_B → A B_A_B
```

**Validation:** every rule satisfies `A → BC` or `A → a` ✓

---

## BONUS — Custom Grammar

```
S → XY | 1
X → 0 | XX | ε
Y → 1 | SY
```

After CNF conversion (ε eliminated, unit chains collapsed):

```
S0 → XY | 1 | SY
S  → XY | 1 | SY
X  → 0 | XX
Y  → 1 | SY
```

All rules valid CNF ✓

---

## Conclusions

The five-step CNF normalization pipeline was implemented cleanly in a single `Grammar` class. Key design decisions:

- **Immutability**: `to_cnf()` deep-copies the grammar so the original is never mutated.
- **Generality (BONUS)**: The implementation accepts any CFG passed as constructor arguments, not just the variant grammar.
- **Deduplication**: A `pair_map` ensures that identical binary pairs produce only one new variable, keeping the output compact.
- **Validation**: After conversion a simple loop confirms every rule conforms to CNF.

The implementation correctly handles all edge cases: nullable symbols that appear multiple times in a rule, chains of unit productions, inaccessible/non-productive symbols introduced as side-effects of earlier steps, and grammars where the start symbol is itself nullable.

---

## References

1. Formal Languages and Automata Theory — Course materials, UTM FCIM
2. Hopcroft, Motwani, Ullman — *Introduction to Automata Theory, Languages, and Computation* (3rd ed.), §7.1
3. Sipser, M. — *Introduction to the Theory of Computation*, §2.1
