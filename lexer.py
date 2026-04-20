"""
Lexer for RoboScript — a mini game-configuration DSL
inspired by Roblox-style entity/property declarations.

Lab 4 upgrade: TokenType entries now carry companion regex patterns,
used both for documentation and for post-hoc token-type validation.

Example input:
    entity Player {
        health = 100
        speed  = 15.5
        name   = "Hero"
        on spawn -> respawn()
        on death -> gameOver()
    }
"""

import re
from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Token types  (each entry carries a regex pattern as a class attribute)
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # Literals
    INTEGER     = auto()   # regex: r'\d+'
    FLOAT       = auto()   # regex: r'\d+\.\d+'
    STRING      = auto()   # regex: r'"([^"\\]|\\.)*"'
    BOOLEAN     = auto()   # regex: r'\b(true|false)\b'

    # Identifiers & keywords
    IDENTIFIER  = auto()   # regex: r'[A-Za-z_]\w*'  (after keyword check)
    KEYWORD     = auto()   # regex: r'\b(entity|on|if|else|return|while|for|...)\b'

    # Operators
    ASSIGN      = auto()   # regex: r'(?<![=!<>])=(?!=)'
    PLUS        = auto()   # regex: r'\+'
    MINUS       = auto()   # regex: r'-(?!>)'
    STAR        = auto()   # regex: r'\*'
    SLASH       = auto()   # regex: r'/'
    PERCENT     = auto()   # regex: r'%'
    ARROW       = auto()   # regex: r'->'
    EQ          = auto()   # regex: r'=='
    NEQ         = auto()   # regex: r'!='
    LT          = auto()   # regex: r'<(?!=)'
    GT          = auto()   # regex: r'>(?!=)'
    LTE         = auto()   # regex: r'<='
    GTE         = auto()   # regex: r'>='
    AND         = auto()   # regex: r'&&'
    OR          = auto()   # regex: r'\|\|'
    NOT         = auto()   # regex: r'!(?!=)'

    # Delimiters
    LPAREN      = auto()   # regex: r'\('
    RPAREN      = auto()   # regex: r'\)'
    LBRACE      = auto()   # regex: r'\{'
    RBRACE      = auto()   # regex: r'\}'
    LBRACKET    = auto()   # regex: r'\['
    RBRACKET    = auto()   # regex: r'\]'
    COMMA       = auto()   # regex: r','
    DOT         = auto()   # regex: r'\.'
    SEMICOLON   = auto()   # regex: r';'
    COLON       = auto()   # regex: r':'

    # Special
    COMMENT     = auto()   # regex: r'--[^\n]*'
    NEWLINE     = auto()   # regex: r'\n'
    EOF         = auto()
    UNKNOWN     = auto()


# Compiled regex patterns used for token-type validation (per TokenType)
TOKEN_PATTERNS: dict[TokenType, re.Pattern] = {
    TokenType.FLOAT:      re.compile(r'^\d+\.\d+$'),
    TokenType.INTEGER:    re.compile(r'^\d+$'),
    TokenType.STRING:     re.compile(r'^"([^"\\]|\\.)*"$'),
    TokenType.BOOLEAN:    re.compile(r'^(true|false)$'),
    TokenType.IDENTIFIER: re.compile(r'^[A-Za-z_]\w*$'),
    TokenType.COMMENT:    re.compile(r'^--.*$'),
    TokenType.ARROW:      re.compile(r'^->$'),
    TokenType.EQ:         re.compile(r'^==$'),
    TokenType.NEQ:        re.compile(r'^!=$'),
    TokenType.LTE:        re.compile(r'^<=$'),
    TokenType.GTE:        re.compile(r'^>=$'),
    TokenType.AND:        re.compile(r'^&&$'),
    TokenType.OR:         re.compile(r'^\|\|$'),
}


KEYWORDS = {
    "entity", "on", "if", "else", "return",
    "while", "for", "in", "true", "false",
    "nil", "local", "function", "end", "do",
    "not", "and", "or", "spawn", "print", "wait",
}


# ---------------------------------------------------------------------------
# Token dataclass
# ---------------------------------------------------------------------------

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, L{self.line}:C{self.column})"

    def validate(self) -> bool:
        """
        Optional regex-based post-hoc validation.
        Returns True if the token's value matches its declared pattern
        (or if no pattern is registered for its type).
        """
        pattern = TOKEN_PATTERNS.get(self.type)
        if pattern is None:
            return True
        raw = self.value if self.type != TokenType.STRING else f'"{self.value}"'
        return bool(pattern.match(raw))


# ---------------------------------------------------------------------------
# Lexer  (hand-written, character-level DFA)
# ---------------------------------------------------------------------------

class Lexer:
    """
    Hand-written character-by-character lexer for RoboScript.
    Tracks line / column for every emitted token.
    """

    def __init__(self, source: str):
        self.source: str = source
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.tokens: List[Token] = []

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def _current(self) -> Optional[str]:
        return self.source[self.pos] if self.pos < len(self.source) else None

    def _peek(self, offset: int = 1) -> Optional[str]:
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else None

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _tok(self, ttype: TokenType, value: str, line: int, col: int) -> Token:
        return Token(ttype, value, line, col)

    # ------------------------------------------------------------------
    # Scanning helpers
    # ------------------------------------------------------------------

    def _skip_whitespace(self):
        while self._current() in (' ', '\t', '\r'):
            self._advance()

    def _scan_comment(self, sl, sc) -> Token:
        text = '--'
        self._advance(); self._advance()
        while self._current() is not None and self._current() != '\n':
            text += self._advance()
        return self._tok(TokenType.COMMENT, text, sl, sc)

    def _scan_string(self, sl, sc) -> Token:
        self._advance()   # opening "
        result = ''
        while True:
            ch = self._current()
            if ch is None:
                break
            if ch == '"':
                self._advance()
                break
            if ch == '\\':
                self._advance()
                esc = self._advance()
                result += {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}.get(esc, esc)
            else:
                result += self._advance()
        return self._tok(TokenType.STRING, result, sl, sc)

    def _scan_number(self, sl, sc) -> Token:
        num = ''
        while self._current() is not None and self._current().isdigit():
            num += self._advance()
        if self._current() == '.' and self._peek() and self._peek().isdigit():
            num += self._advance()
            while self._current() is not None and self._current().isdigit():
                num += self._advance()
            return self._tok(TokenType.FLOAT, num, sl, sc)
        return self._tok(TokenType.INTEGER, num, sl, sc)

    def _scan_word(self, sl, sc) -> Token:
        word = ''
        while self._current() is not None and (self._current().isalnum() or self._current() == '_'):
            word += self._advance()
        if word in ('true', 'false'):
            return self._tok(TokenType.BOOLEAN, word, sl, sc)
        if word in KEYWORDS:
            return self._tok(TokenType.KEYWORD, word, sl, sc)
        return self._tok(TokenType.IDENTIFIER, word, sl, sc)

    def _scan_operator(self, sl, sc) -> Token:
        ch = self._advance()
        nxt = self._current() or ''
        two = ch + nxt
        two_map = {
            '->': TokenType.ARROW, '==': TokenType.EQ, '!=': TokenType.NEQ,
            '<=': TokenType.LTE,   '>=': TokenType.GTE,
            '&&': TokenType.AND,   '||': TokenType.OR,
        }
        if two in two_map:
            self._advance()
            return self._tok(two_map[two], two, sl, sc)
        one_map = {
            '=': TokenType.ASSIGN,   '+': TokenType.PLUS,   '-': TokenType.MINUS,
            '*': TokenType.STAR,     '/': TokenType.SLASH,  '%': TokenType.PERCENT,
            '<': TokenType.LT,       '>': TokenType.GT,     '!': TokenType.NOT,
            '(': TokenType.LPAREN,   ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,   '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET, ']': TokenType.RBRACKET,
            ',': TokenType.COMMA,    '.': TokenType.DOT,
            ';': TokenType.SEMICOLON,':': TokenType.COLON,
        }
        if ch in one_map:
            return self._tok(one_map[ch], ch, sl, sc)
        return self._tok(TokenType.UNKNOWN, ch, sl, sc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break
            ch = self._current()
            sl, sc = self.line, self.column
            if ch == '\n':
                self._advance()
                self.tokens.append(self._tok(TokenType.NEWLINE, '\\n', sl, sc))
            elif ch == '-' and self._peek() == '-':
                self.tokens.append(self._scan_comment(sl, sc))
            elif ch == '"':
                self.tokens.append(self._scan_string(sl, sc))
            elif ch.isdigit():
                self.tokens.append(self._scan_number(sl, sc))
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self._scan_word(sl, sc))
            else:
                self.tokens.append(self._scan_operator(sl, sc))
        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


# ---------------------------------------------------------------------------
# Sample source used by both lexer demo and parser demo
# ---------------------------------------------------------------------------

SAMPLE_SOURCE = """\
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

-- Enemy with patrol behavior
entity Enemy {
    health = 50
    damage = 10
    patrol_radius = 30.0

    on tick -> patrol()
    on player_nearby -> attack()

    while health > 0 {
        speed = speed + 1
    }
}
"""


if __name__ == '__main__':
    lexer = Lexer(SAMPLE_SOURCE)
    tokens = lexer.tokenize()

    print(f"{'TYPE':<15} {'VALUE':<22} {'LINE':>4}  {'COL':>3}  {'VALID':>5}")
    print('-' * 58)
    for tok in tokens:
        if tok.type == TokenType.NEWLINE:
            continue
        valid = '✓' if tok.validate() else '✗'
        print(f"{tok.type.name:<15} {tok.value!r:<22} {tok.line:>4}  {tok.column:>3}  {valid:>5}")

    meaningful = sum(1 for t in tokens
                     if t.type not in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT))
    print(f"\nTotal: {len(tokens)} tokens | Meaningful: {meaningful}")
