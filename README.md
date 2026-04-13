# Lab 4 – Regular Expressions

**Course:** Formal Languages & Finite Automata  
**Student:** Strunga Daniel-Ioan  
**Group:** FAF-242  
**Variant:** 3  

---

## Objectives

1. Understand what regular expressions are and what they are used for.
2. Write a program that **dynamically** generates valid strings from a given regular expression (no hardcoding).
3. Cap unlimited repetitions (`*`, `+`) at **5** to avoid extremely long strings.
4. **Bonus:** Show a step-by-step trace of how each regular expression is processed.

---

## What Are Regular Expressions?

A **regular expression** (regex) is a formal notation for describing a set (language) of strings. They are built from:

| Operator | Meaning |
|----------|---------|
| `AB`     | Concatenation – A followed by B |
| `A\|B`   | Alternation – A or B |
| `A*`     | Kleene star – zero or more repetitions of A |
| `A+`     | One or more repetitions of A |
| `A?`     | Zero or one occurrence of A |
| `A^N`    | Exactly N repetitions of A |
| `(…)`    | Grouping |

Regular expressions are used in text search, lexers/tokenizers, input validation, compiler front-ends, and many other areas.

---

## Variant 3 – Regular Expressions

```
Regex 1:  O(P|Q|R)+ 2(3|4)
Regex 2:  A* B(C|D|E) F(G|H|I)^2
Regex 3:  J+ K(L|M|N)* O?(P|Q)^3
```

### Expected output examples (from the assignment)

| Regex | Examples |
|-------|---------|
| `O(P|Q|R)+ 2(3|4)` | OPP23, OQQQQ24, ORPQ23, … |
| `A* B(C|D|E) F(G|H|I)^2` | AAABCFGG, AAAAAABDFHH, BCFGI, … |
| `J+ K(L|M|N)* O?(P|Q)^3` | JJKLOPPP, JKNQQQ, JKOPQP, … |

---

## How the Code Works

The solution is in **`regex_generator.py`** and consists of four key functions.

### 1. `parse_and_generate(pattern, trace=False)`

Entry point. Calls the internal recursive generator and returns `(result_string, trace_steps)`.

### 2. `_generate(pattern, steps, trace)`

Scans the pattern **left-to-right**, character by character:

- If it sees `(` → finds the matching `)`, extracts the group content, reads the quantifier that follows, and delegates to `_apply_quantifier`.
- Otherwise → reads a single character, reads its quantifier, delegates to `_apply_quantifier`.

### 3. `_get_quantifier(pattern, pos)`

Reads the quantifier token starting at `pos`:

| Input | Quantifier returned |
|-------|---------------------|
| `*`   | `'*'`  |
| `+`   | `'+'`  |
| `?`   | `'?'`  |
| `^N`  | `'N'` (exact integer) |
| digit after `)` | that integer as string |
| nothing | `'1'` (default – appear once) |

### 4. `_apply_quantifier(token, quantifier, …)`

Decides how many times to emit the token:

| Quantifier | Repetitions chosen |
|------------|-------------------|
| `*` | `random.randint(0, 5)` |
| `+` | `random.randint(1, 5)` |
| `?` | `random.randint(0, 1)` |
| `N` | exactly `N` |

For a **group**, it calls `_split_alternatives` to get `['A', 'B', 'C']` and picks one randomly, then recursively generates from the chosen alternative.

### 5. `_split_alternatives(group_content)`

Splits a string like `"P|Q|R"` on `|` while respecting nested parentheses, returning a list of alternatives.

### Bonus – Processing Trace

Passing `trace=True` makes every operator append a human-readable description of what it chose to a `steps` list, which is then printed line by line. Example output:

```
Pattern : A* B(C|D|E) F(G|H|I)^2
Result  : AABCFGI
Trace   :
  1. * operator on 'A': repeat 2 times (0..5)
  2.   Group alternatives: ['C', 'D', 'E'] → chose 'C'
  3. Exact repeat 2x on group(G|H|I)
  4.   Group alternatives: ['G', 'H', 'I'] → chose 'G'
  5.   Group alternatives: ['G', 'H', 'I'] → chose 'I'
```

---

## Running the Code

```bash
python regex_generator.py
```

No external dependencies – only the Python standard library (`random`).

---

## Sample Output

```
============================================================
Variant 3 – Regular Expression String Generator
============================================================

Regex: O(P|Q|R)+ 2(3|4)
Generated: ['ORPR23', 'OPRPP24', 'OQP23', 'OQRRPR24', 'OQ24', 'OQQ23']

Regex: A* B(C|D|E) F(G|H|I)^2
Generated: ['AAABCFHH', 'AABEFHG', 'AABDFGI', 'BEFGI', 'AAAABCFHI', 'BEFIG']

Regex: J+ K(L|M|N)* O?(P|Q)^3
Generated: ['JJJJJKMMNOQPP', 'JJJJKMLLLOPPQ', 'JJJJKNLMNQQQ', 'JKQQP', 'JKLLLNLQPQ', 'JJKMMNQQQ']
```

---

## Difficulties Encountered

- **Quantifier ambiguity:** A bare digit after `)` could be part of the pattern literal or a repetition count. The solution treats a digit immediately following `)` as a repetition count, which matches the assignment notation (`^N` and implicit `N`).
- **Nested groups:** `_split_alternatives` tracks parenthesis depth to avoid splitting on `|` inside a nested group.
- **Caret vs superscript:** The assignment uses both `^N` notation and superscript numbers visually; the code handles `^N` as the canonical form.

---

## Repository

[GitHub – don09dandidi/DSL- (branch: lab4/regex)](https://github.com/don09dandidi/DSL-)
