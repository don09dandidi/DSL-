# Lexer & Scanner

### Course: Formal Languages & Finite Automata
### Author: Strunga Daniel-Ioan, FAF-242
### Date: March 2026

---

## Theory

Lexical analysis is the first phase of a compiler or interpreter pipeline. It reads a raw stream of characters and groups them into meaningful units called **tokens**. Each token carries a **type** (its category) and the original **lexeme** (the raw text that was matched).

The distinction between lexeme and token is important:

- A **lexeme** is the raw substring extracted from source text (e.g., `15.5`).
- A **token** is the categorised representation of that lexeme (e.g., `FLOAT "15.5"`).

A lexer (also called a scanner or tokenizer) is typically implemented either with regular expressions or as a hand-written finite automaton. In both cases the underlying mechanism is equivalent to a Deterministic Finite Automaton (DFA): the lexer transitions between states based on incoming characters and emits a token when it reaches an accepting state.

---

## Objectives

1. Understand what lexical analysis is.
2. Get familiar with the inner workings of a lexer/scanner/tokenizer.
3. Implement a sample lexer and demonstrate how it works.

---

## Implementation

### Language Choice — RoboScript

Instead of a standard calculator, the lexer targets **RoboScript** — a fictional game-configuration DSL inspired by the structure used in Roblox game development. This domain was chosen because it:

- Contains a richer token vocabulary than a simple arithmetic calculator.
- Includes entity blocks, event bindings (`on spawn -> respawn()`), typed literals, and control flow.
- Has practical relevance to actual game scripting patterns.

A sample RoboScript program:

```
-- RoboScript: Player entity definition
entity Player {
    health = 100
    speed = 15.5
    name = "Hero"
    invincible = false

    on spawn -> respawn()
    on death -> gameOver()

    if health <= 0 {
        return nil
    }
}
```

---

### Token Types

The lexer recognises the following token categories, defined in the `TokenType` enum:

| Category | Tokens |
|---|---|
| **Literals** | `INTEGER`, `FLOAT`, `STRING`, `BOOLEAN` |
| **Identifiers** | `IDENTIFIER`, `KEYWORD` |
| **Operators** | `ASSIGN`, `PLUS`, `MINUS`, `STAR`, `SLASH`, `PERCENT`, `ARROW`, `EQ`, `NEQ`, `LT`, `GT`, `LTE`, `GTE`, `AND`, `OR`, `NOT` |
| **Delimiters** | `LPAREN`, `RPAREN`, `LBRACE`, `RBRACE`, `LBRACKET`, `RBRACKET`, `COMMA`, `DOT`, `SEMICOLON`, `COLON` |
| **Special** | `COMMENT`, `NEWLINE`, `EOF`, `UNKNOWN` |

Keywords are stored in a set and distinguished from identifiers at classification time:

```python
KEYWORDS = {
    "entity", "on", "if", "else", "return",
    "while", "for", "in", "true", "false",
    "nil", "local", "function", "end", "do",
    "not", "and", "or", "spawn", "print", "wait"
}
```

`true` and `false` are further specialised into `BOOLEAN` rather than `KEYWORD` to make downstream parsing simpler.

---

### Token Dataclass

Every emitted token carries its type, raw value, and source location:

```python
@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int
```

Line and column tracking is maintained through the `_advance()` method, which increments the line counter on every `\n` character.

---

### Lexer Architecture

The `Lexer` class operates as a hand-written character-by-character scanner:

```
Source string
     │
     ▼
 _skip_whitespace()   ← spaces & tabs only (newlines are tokens)
     │
     ▼
  peek at ch
     │
  ┌──┴──────────────────────────────────────────────────────┐
  │   \n        → NEWLINE token                             │
  │   --        → _scan_comment()                          │
  │   "         → _scan_string()                           │
  │   [0-9]     → _scan_number()                           │
  │   [a-zA-Z_] → _scan_identifier_or_keyword()            │
  │   else      → _scan_operator_or_delimiter()            │
  └─────────────────────────────────────────────────────────┘
     │
     ▼
  Token appended to self.tokens
     │
     ▼
  Loop until EOF → append EOF token → return list
```

#### Key scanning routines

**`_scan_number`** — reads digit characters, then checks for a `.` followed by more digits to determine if the result is `FLOAT` or `INTEGER`. This implements a simple two-state DFA: `INT_STATE → FLOAT_STATE` on `.`.

**`_scan_string`** — consumes everything between double quotes, resolving escape sequences (`\n`, `\t`, `\\`, `\"`). Unterminated strings emit the partial value rather than crashing.

**`_scan_identifier_or_keyword`** — reads `[a-zA-Z0-9_]+`, then classifies the result against `KEYWORDS`. `true`/`false` get `BOOLEAN`; other keywords get `KEYWORD`; everything else gets `IDENTIFIER`.

**`_scan_operator_or_delimiter`** — advances one character, then peeks at the next to assemble two-character operators (`->`, `==`, `!=`, `<=`, `>=`, `&&`, `||`) before falling back to single-character tokens.

**`_scan_comment`** — triggered by `--`, consumes until end of line without emitting a `NEWLINE` token for the `--` characters themselves.

---

### Results

Running the lexer on the sample RoboScript source above produces 88 tokens (61 meaningful, excluding newlines and EOF). A formatted excerpt:

```
TYPE            VALUE                LINE  COL
--------------------------------------------------
COMMENT         '-- RoboScript: ...'    1    1
KEYWORD         'entity'                2    1
IDENTIFIER      'Player'                2    8
LBRACE          '{'                     2   15
IDENTIFIER      'health'                3    5
ASSIGN          '='                     3   12
INTEGER         '100'                   3   14
IDENTIFIER      'speed'                 4    5
ASSIGN          '='                     4   11
FLOAT           '15.5'                  4   13
IDENTIFIER      'name'                  5    5
ASSIGN          '='                     5   10
STRING          'Hero'                  5   12
IDENTIFIER      'invincible'            6    5
ASSIGN          '='                     6   16
BOOLEAN         'false'                 6   18
KEYWORD         'on'                    8    5
KEYWORD         'spawn'                 8    8
ARROW           '->'                    8   14
IDENTIFIER      'respawn'               8   17
LPAREN          '('                     8   24
RPAREN          ')'                     8   25
...
EOF             ''                     25    1
```

Every token carries the correct line and column, enabling meaningful error messages in a future parser stage.

---

## Conclusions

The implemented lexer demonstrates the core mechanics of lexical analysis:

1. **Character-by-character scanning** with a single-pass, O(n) algorithm — no backtracking.
2. **Source location tracking** (line + column) attached to every token, essential for error reporting.
3. **Keyword vs. identifier disambiguation** done at classification time rather than requiring separate DFA states.
4. **Multi-character operator assembly** handled by a single-lookahead peek, keeping the scanner simple.
5. **Robust string scanning** with escape sequence support and graceful handling of unterminated strings.

The RoboScript domain provided a rich-enough token set to exercise all major lexer concerns without the overhead of a full production language, while remaining directly relevant to practical game scripting use cases.

---

## References

1. Cretu Dumitru et al., *Lab 3 — Lexer & Scanner* assignment, FLFA course, UTM, 2026.
2. [Lexical analysis — Wikipedia](https://en.wikipedia.org/wiki/Lexical_analysis)
3. [My First Language Frontend with LLVM — LLVM Project](https://llvm.org/docs/tutorial/MyFirstLanguageFrontend/LangImpl01.html)
