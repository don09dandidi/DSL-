# Lab 6 – Parser & Building an Abstract Syntax Tree

**Course:** Formal Languages & Finite Automata  
**Student:** Strunga Daniel-Ioan  
**Group:** FAF-242  
---

## Theory

### Parsing

**Parsing** (syntactic analysis) is the second major phase of a compiler or interpreter. It receives the flat token stream produced by the lexer and checks whether the sequence of tokens conforms to the grammar of the language. When it does, it simultaneously builds a hierarchical data structure that captures the syntactic relationships between the tokens.

A **recursive-descent parser** implements each grammar production rule as a function that calls other rule-functions recursively. It is the most natural hand-written parsing technique: the call stack mirrors the grammar's derivation tree.

Operator **precedence** is encoded structurally: lower-precedence rules appear higher in the call chain and call into higher-precedence rules. For RoboScript the hierarchy (weakest to strongest binding) is:

```
or → and → equality → comparison → addition → multiply → unary → primary
```

### Abstract Syntax Tree

A **parse tree** (concrete syntax tree) contains every token including punctuation, delimiters, and syntactic noise. An **Abstract Syntax Tree (AST)** strips these out and retains only semantically meaningful nodes:

- Parentheses disappear — grouping is encoded structurally.
- Delimiters (`{`, `}`, `;`) disappear.
- Keyword tokens disappear once their purpose is encoded in the node type.

Each AST node carries enough information for subsequent phases (type checking, interpretation, code generation) without requiring re-reading of the original source.

---

## Objectives

1. Get familiar with parsing and how it is implemented programmatically.
2. Get familiar with the concept of an AST and its design.
3. Extend Lab 3 by:
   - Adding regex-based token validation to `TokenType`.
   - Designing a complete AST node hierarchy for RoboScript.
   - Implementing a recursive-descent parser that builds the AST.

---

## Implementation

The implementation lives in two files — `lexer.py` (updated from Lab 3) and `parser.py` (new for Lab 4).

### TokenType with regex patterns

Lab 3 already had a `TokenType` enum. For Lab 4 a `TOKEN_PATTERNS` dictionary maps each type to a compiled `re.Pattern`:

```python
TOKEN_PATTERNS: dict[TokenType, re.Pattern] = {
    TokenType.FLOAT:      re.compile(r'^\d+\.\d+$'),
    TokenType.INTEGER:    re.compile(r'^\d+$'),
    TokenType.STRING:     re.compile(r'^"([^"\\]|\\.)*"$'),
    TokenType.BOOLEAN:    re.compile(r'^(true|false)$'),
    TokenType.IDENTIFIER: re.compile(r'^[A-Za-z_]\w*$'),
    TokenType.ARROW:      re.compile(r'^->$'),
    TokenType.EQ:         re.compile(r'^==$'),
    # …
}
```

The `Token.validate()` method uses these patterns to confirm that a token's lexeme matches its declared category. All 73 meaningful tokens in the sample program validate as ✓.

### AST Node Hierarchy

All nodes extend a common `ASTNode` base class and implement `to_dict()` for JSON serialisation:

```
ASTNode
├── LiteralNode       — integer, float, string, bool, nil constants
├── IdentifierNode    — named symbol reference
├── BinOpNode         — left <op> right
├── UnaryOpNode       — <op> operand
├── CallNode          — name(arg, …)
├── AssignmentNode    — name = value
├── EventBindNode     — on <event> -> CallNode
├── ReturnNode        — return [expr]
├── IfNode            — condition, then_body, else_body
├── WhileNode         — condition, body
├── ExprStmtNode      — expression used as statement
├── EntityNode        — name, body[]
└── ProgramNode       — entities[]
```

Nodes are plain Python `@dataclass` objects: immutable-by-convention, cheap to construct, and trivial to inspect or serialise.

### Parser

The `Parser` class implements recursive descent. Token-stream helpers:

| Method | Purpose |
|---|---|
| `_cur()` | Look at the current token without consuming |
| `_peek(n)` | Look n positions ahead |
| `_advance()` | Consume and return the current token |
| `_expect(type, val?)` | Consume expected token or raise `ParseError` |
| `_match_type(*types)` | Non-consuming type check |
| `_match_kw(*words)` | Non-consuming keyword check |

The parser strips `NEWLINE` and `COMMENT` tokens on construction so every rule ignores whitespace entirely.

#### Statement dispatch

`_parse_statement()` uses a look-ahead of 1–2 tokens to decide which rule applies:

```python
def _parse_statement(self):
    if keyword 'on'      → _parse_event_bind()
    if keyword 'if'      → _parse_if()
    if keyword 'while'   → _parse_while()
    if keyword 'return'  → _parse_return()
    if IDENTIFIER + '='  → _parse_assignment()
    else                 → ExprStmtNode(_parse_expr())
```

#### Expression precedence

Each precedence level is one method that calls the next tighter level and loops on operators at its own level:

```python
def _parse_addition(self):
    left = self._parse_multiply()
    while self._match_type(PLUS, MINUS):
        op = self._advance().value
        right = self._parse_multiply()
        left = BinOpNode(left, op, right)
    return left
```

This ensures `a + b * c` produces `BinOp(+, a, BinOp(*, b, c))` correctly.

### Pretty Printer

`print_ast()` renders the tree using Unicode box-drawing connectors. Abbreviated example:

```
Program  [2 entities]
    ├── Entity  "Player"
    │   ├── Assign  health =
    │   │   └── Literal(int)  100
    │   ├── EventBind  on spawn ->
    │   │   └── Call  respawn()
    │   └── If
    │       ├── BinOp  "<="
    │       │   ├── Identifier  "health"
    │       │   └── Literal(int)  0
    │       └── Return
    │           └── Literal(nil)  None
    └── Entity  "Enemy"
        └── While
            ├── BinOp  ">"
            │   ├── Identifier  "health"
            │   └── Literal(int)  0
            └── Assign  speed =
                └── BinOp  "+"
                    ├── Identifier  "speed"
                    └── Literal(int)  1
```

Every node also serialises to JSON via `node.to_dict()`.

---

## Results

Running `python parser.py` executes three stages:

1. **Lexer table** — 73 meaningful tokens, all regex-validated ✓
2. **AST tree-art** — full tree for the two-entity sample program
3. **AST JSON dump** — machine-readable representation

The parser correctly handles: nested binary expressions with correct precedence, compound comparisons (`<=`, `>`), `if` with and without `else`, `while` loops, `return` with and without a value, event bindings, and function calls with zero or more arguments.

---

## Conclusions

Lab 4 extends Lab 3 in three concrete ways. First, `TokenType` entries are backed by compiled regex patterns and tokens expose a `validate()` method. Second, a complete AST node hierarchy was designed using Python dataclasses, covering all statement and expression forms of RoboScript. Third, the recursive-descent parser was rewritten from a skeletal two-level structure into a seven-level expression hierarchy with proper precedence, `if/else`, `while`, `return`, and function-call support.

The separation between `lexer.py` and `parser.py` mirrors the classical compiler pipeline: the lexer produces a token stream; the parser consumes it and produces an AST. Neither component knows about the internals of the other, which makes both easy to test and replace independently.

---

## References

1. Crafting Interpreters — R. Nystrom, chapters 4–5 (https://craftinginterpreters.com)
2. Compilers: Principles, Techniques, and Tools — Aho, Lam, Sethi, Ullman (Dragon Book), §2.2–2.4
3. Formal Languages and Automata — UTM FCIM course materials
