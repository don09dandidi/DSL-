"""
Lexer for RoboScript — a mini game-configuration DSL
inspired by Roblox-style entity/property declarations.

Example input:
    entity Player {
        health = 100
        speed = 15.5
        name = "Hero"
        on spawn -> respawn()
        on death -> gameOver()
    }
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


# ---------------------------------------------------------------------------
# Token types
# ---------------------------------------------------------------------------

class TokenType(Enum):
    # Literals
    INTEGER     = auto()   # 42
    FLOAT       = auto()   # 3.14
    STRING      = auto()   # "hello"
    BOOLEAN     = auto()   # true | false

    # Identifiers & keywords
    IDENTIFIER  = auto()   # player, speed, myVar
    KEYWORD     = auto()   # entity, on, if, else, return, while

    # Operators
    ASSIGN      = auto()   # =
    PLUS        = auto()   # +
    MINUS       = auto()   # -
    STAR        = auto()   # *
    SLASH       = auto()   # /
    PERCENT     = auto()   # %
    ARROW       = auto()   # ->
    EQ          = auto()   # ==
    NEQ         = auto()   # !=
    LT          = auto()   # <
    GT          = auto()   # >
    LTE         = auto()   # <=
    GTE         = auto()   # >=
    AND         = auto()   # &&
    OR          = auto()   # ||
    NOT         = auto()   # !

    # Delimiters
    LPAREN      = auto()   # (
    RPAREN      = auto()   # )
    LBRACE      = auto()   # {
    RBRACE      = auto()   # }
    LBRACKET    = auto()   # [
    RBRACKET    = auto()   # ]
    COMMA       = auto()   # ,
    DOT         = auto()   # .
    SEMICOLON   = auto()   # ;
    COLON       = auto()   # :

    # Special
    COMMENT     = auto()   # -- single-line comment
    NEWLINE     = auto()   # \n
    EOF         = auto()   # end of input
    UNKNOWN     = auto()   # unrecognized character


KEYWORDS = {
    "entity", "on", "if", "else", "return",
    "while", "for", "in", "true", "false",
    "nil", "local", "function", "end", "do",
    "not", "and", "or", "spawn", "print", "wait"
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


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class Lexer:
    """
    Hand-written character-by-character lexer for RoboScript.

    Tracks line and column numbers for every emitted token.
    Skips whitespace (except newlines which are emitted as NEWLINE tokens).
    Supports:
        - Integer and float literals
        - Double-quoted string literals with escape sequences
        - Single-line comments starting with --
        - All common operators including -> and compound comparisons
        - Keywords vs identifiers distinction
    """

    def __init__(self, source: str):
        self.source: str = source
        self.pos: int = 0
        self.line: int = 1
        self.column: int = 1
        self.tokens: List[Token] = []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _current(self) -> Optional[str]:
        """Return the character at the current position, or None at EOF."""
        if self.pos < len(self.source):
            return self.source[self.pos]
        return None

    def _peek(self, offset: int = 1) -> Optional[str]:
        """Look ahead without consuming."""
        idx = self.pos + offset
        if idx < len(self.source):
            return self.source[idx]
        return None

    def _advance(self) -> str:
        """Consume and return the current character, updating position tracking."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return ch

    def _make_token(self, ttype: TokenType, value: str, line: int, col: int) -> Token:
        return Token(ttype, value, line, col)

    # ------------------------------------------------------------------
    # Scanning routines
    # ------------------------------------------------------------------

    def _skip_whitespace(self):
        """Consume spaces and tabs (not newlines)."""
        while self._current() in (' ', '\t', '\r'):
            self._advance()

    def _scan_comment(self, start_line: int, start_col: int) -> Token:
        """Consume everything after -- until end of line."""
        text = '--'
        self._advance(); self._advance()  # consume both '-'
        while self._current() is not None and self._current() != '\n':
            text += self._advance()
        return self._make_token(TokenType.COMMENT, text, start_line, start_col)

    def _scan_string(self, start_line: int, start_col: int) -> Token:
        """Consume a double-quoted string, handling basic escape sequences."""
        self._advance()  # opening "
        result = ''
        while True:
            ch = self._current()
            if ch is None:
                # Unterminated string — emit what we have
                break
            if ch == '"':
                self._advance()  # closing "
                break
            if ch == '\\':
                self._advance()
                esc = self._advance()
                result += {'n': '\n', 't': '\t', '\\': '\\', '"': '"'}.get(esc, esc)
            else:
                result += self._advance()
        return self._make_token(TokenType.STRING, result, start_line, start_col)

    def _scan_number(self, start_line: int, start_col: int) -> Token:
        """Consume an integer or float literal."""
        num = ''
        is_float = False
        while self._current() is not None and self._current().isdigit():
            num += self._advance()
        if self._current() == '.' and self._peek() is not None and self._peek().isdigit():
            is_float = True
            num += self._advance()  # '.'
            while self._current() is not None and self._current().isdigit():
                num += self._advance()
        ttype = TokenType.FLOAT if is_float else TokenType.INTEGER
        return self._make_token(ttype, num, start_line, start_col)

    def _scan_identifier_or_keyword(self, start_line: int, start_col: int) -> Token:
        """Consume an identifier; classify as KEYWORD, BOOLEAN, or IDENTIFIER."""
        word = ''
        while self._current() is not None and (self._current().isalnum() or self._current() == '_'):
            word += self._advance()
        if word in ('true', 'false'):
            ttype = TokenType.BOOLEAN
        elif word in KEYWORDS:
            ttype = TokenType.KEYWORD
        else:
            ttype = TokenType.IDENTIFIER
        return self._make_token(ttype, word, start_line, start_col)

    def _scan_operator_or_delimiter(self, start_line: int, start_col: int) -> Token:
        """Consume a single or multi-character operator/delimiter."""
        ch = self._advance()
        nxt = self._current()

        # Two-character operators
        two = ch + (nxt or '')
        two_map = {
            '->': TokenType.ARROW,
            '==': TokenType.EQ,
            '!=': TokenType.NEQ,
            '<=': TokenType.LTE,
            '>=': TokenType.GTE,
            '&&': TokenType.AND,
            '||': TokenType.OR,
        }
        if two in two_map:
            self._advance()
            return self._make_token(two_map[two], two, start_line, start_col)

        # Single-character
        one_map = {
            '=': TokenType.ASSIGN,
            '+': TokenType.PLUS,
            '-': TokenType.MINUS,
            '*': TokenType.STAR,
            '/': TokenType.SLASH,
            '%': TokenType.PERCENT,
            '<': TokenType.LT,
            '>': TokenType.GT,
            '!': TokenType.NOT,
            '(': TokenType.LPAREN,
            ')': TokenType.RPAREN,
            '{': TokenType.LBRACE,
            '}': TokenType.RBRACE,
            '[': TokenType.LBRACKET,
            ']': TokenType.RBRACKET,
            ',': TokenType.COMMA,
            '.': TokenType.DOT,
            ';': TokenType.SEMICOLON,
            ':': TokenType.COLON,
        }
        if ch in one_map:
            return self._make_token(one_map[ch], ch, start_line, start_col)

        return self._make_token(TokenType.UNKNOWN, ch, start_line, start_col)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def tokenize(self) -> List[Token]:
        """
        Main tokenization loop.
        Returns the complete list of Token objects, ending with EOF.
        """
        while self.pos < len(self.source):
            self._skip_whitespace()
            if self.pos >= len(self.source):
                break

            ch = self._current()
            start_line, start_col = self.line, self.column

            # Newline
            if ch == '\n':
                self._advance()
                self.tokens.append(self._make_token(TokenType.NEWLINE, '\\n', start_line, start_col))

            # Comment: --
            elif ch == '-' and self._peek() == '-':
                self.tokens.append(self._scan_comment(start_line, start_col))

            # String literal
            elif ch == '"':
                self.tokens.append(self._scan_string(start_line, start_col))

            # Number
            elif ch.isdigit():
                self.tokens.append(self._scan_number(start_line, start_col))

            # Identifier / keyword
            elif ch.isalpha() or ch == '_':
                self.tokens.append(self._scan_identifier_or_keyword(start_line, start_col))

            # Operators and delimiters
            else:
                self.tokens.append(self._scan_operator_or_delimiter(start_line, start_col))

        self.tokens.append(Token(TokenType.EOF, '', self.line, self.column))
        return self.tokens


# ---------------------------------------------------------------------------
# Demo
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
}
"""

if __name__ == '__main__':
    lexer = Lexer(SAMPLE_SOURCE)
    tokens = lexer.tokenize()

    # Pretty-print — skip NEWLINEs for readability
    print(f"{'TYPE':<15} {'VALUE':<20} {'LINE':>4}  {'COL':>3}")
    print('-' * 50)
    for tok in tokens:
        if tok.type == TokenType.NEWLINE:
            continue
        print(f"{tok.type.name:<15} {tok.value!r:<20} {tok.line:>4}  {tok.column:>3}")

    total = len(tokens)
    meaningful = sum(1 for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.EOF, TokenType.COMMENT))
    print(f"\nTotal tokens: {total} | Meaningful: {meaningful}")
