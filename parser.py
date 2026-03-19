"""
Simple recursive-descent parser for RoboScript.
Consumes tokens from the Lexer and builds an AST.

Grammar:
    program     → entity*
    entity      → 'entity' IDENTIFIER '{' statement* '}'
    statement   → assignment | event_bind | if_stmt
    assignment  → IDENTIFIER '=' expr
    event_bind  → 'on' IDENTIFIER '->' IDENTIFIER '(' ')'
    if_stmt     → 'if' expr '{' statement* '}'
    expr        → IDENTIFIER | literal | expr BINOP expr
    literal     → INTEGER | FLOAT | STRING | BOOLEAN | 'nil'
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from lexer import Lexer, Token, TokenType


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class ASTNode:
    pass

@dataclass
class LiteralNode(ASTNode):
    value: Any
    kind: str  # 'int', 'float', 'string', 'bool', 'nil'

@dataclass
class IdentifierNode(ASTNode):
    name: str

@dataclass
class BinOpNode(ASTNode):
    left: ASTNode
    op: str
    right: ASTNode

@dataclass
class AssignmentNode(ASTNode):
    name: str
    value: ASTNode

@dataclass
class EventBindNode(ASTNode):
    event: str
    handler: str

@dataclass
class IfNode(ASTNode):
    condition: ASTNode
    body: List[ASTNode]

@dataclass
class EntityNode(ASTNode):
    name: str
    body: List[ASTNode] = field(default_factory=list)

@dataclass
class ProgramNode(ASTNode):
    entities: List[EntityNode] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

BINOPS = {
    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
    TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT,
    TokenType.LTE, TokenType.GTE, TokenType.AND, TokenType.OR,
}

class Parser:
    def __init__(self, tokens: List[Token]):
        # Strip newlines and comments — parser doesn't need them
        self.tokens = [t for t in tokens if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)]
        self.pos = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset=1) -> Token:
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return self.tokens[-1]  # EOF

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _expect(self, ttype: TokenType, value: str = None) -> Token:
        tok = self._current()
        if tok.type != ttype:
            raise SyntaxError(f"L{tok.line}: expected {ttype.name}, got {tok.type.name} ({tok.value!r})")
        if value and tok.value != value:
            raise SyntaxError(f"L{tok.line}: expected {value!r}, got {tok.value!r}")
        return self._advance()

    def _match(self, ttype: TokenType, value: str = None) -> bool:
        tok = self._current()
        if tok.type != ttype:
            return False
        if value and tok.value != value:
            return False
        return True

    # ------------------------------------------------------------------
    # Grammar rules
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        program = ProgramNode()
        while self._current().type != TokenType.EOF:
            program.entities.append(self._parse_entity())
        return program

    def _parse_entity(self) -> EntityNode:
        self._expect(TokenType.KEYWORD, 'entity')
        name = self._expect(TokenType.IDENTIFIER).value
        self._expect(TokenType.LBRACE)
        body = self._parse_body()
        self._expect(TokenType.RBRACE)
        return EntityNode(name=name, body=body)

    def _parse_body(self) -> List[ASTNode]:
        stmts = []
        while not self._match(TokenType.RBRACE) and self._current().type != TokenType.EOF:
            stmts.append(self._parse_statement())
        return stmts

    def _parse_statement(self) -> ASTNode:
        tok = self._current()

        # event binding: on <event> -> <handler>()
        if tok.type == TokenType.KEYWORD and tok.value == 'on':
            return self._parse_event_bind()

        # if statement
        if tok.type == TokenType.KEYWORD and tok.value == 'if':
            return self._parse_if()

        # assignment: IDENTIFIER = expr
        if tok.type == TokenType.IDENTIFIER and self._peek().type == TokenType.ASSIGN:
            return self._parse_assignment()

        # skip unknown tokens gracefully
        self._advance()
        return LiteralNode(value=None, kind='nil')

    def _parse_assignment(self) -> AssignmentNode:
        name = self._advance().value   # IDENTIFIER
        self._advance()                # '='
        value = self._parse_expr()
        return AssignmentNode(name=name, value=value)

    def _parse_event_bind(self) -> EventBindNode:
        self._advance()                          # 'on'
        event = self._advance().value            # event name
        self._expect(TokenType.ARROW)            # '->'
        handler = self._advance().value          # handler name
        self._expect(TokenType.LPAREN)
        self._expect(TokenType.RPAREN)
        return EventBindNode(event=event, handler=handler)

    def _parse_if(self) -> IfNode:
        self._advance()                # 'if'
        condition = self._parse_expr()
        self._expect(TokenType.LBRACE)
        body = self._parse_body()
        self._expect(TokenType.RBRACE)
        return IfNode(condition=condition, body=body)

    def _parse_expr(self) -> ASTNode:
        left = self._parse_primary()
        # Binary operator?
        if self._current().type in BINOPS:
            op = self._advance().value
            right = self._parse_primary()
            return BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_primary(self) -> ASTNode:
        tok = self._current()
        if tok.type == TokenType.INTEGER:
            self._advance()
            return LiteralNode(value=int(tok.value), kind='int')
        if tok.type == TokenType.FLOAT:
            self._advance()
            return LiteralNode(value=float(tok.value), kind='float')
        if tok.type == TokenType.STRING:
            self._advance()
            return LiteralNode(value=tok.value, kind='string')
        if tok.type == TokenType.BOOLEAN:
            self._advance()
            return LiteralNode(value=tok.value == 'true', kind='bool')
        if tok.type == TokenType.KEYWORD and tok.value == 'nil':
            self._advance()
            return LiteralNode(value=None, kind='nil')
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentifierNode(name=tok.value)
        # fallback
        self._advance()
        return LiteralNode(value=tok.value, kind='nil')


# ---------------------------------------------------------------------------
# AST pretty-printer
# ---------------------------------------------------------------------------

def print_ast(node: ASTNode, indent: int = 0):
    pad = '  ' * indent
    if isinstance(node, ProgramNode):
        print(f"{pad}Program")
        for e in node.entities:
            print_ast(e, indent + 1)
    elif isinstance(node, EntityNode):
        print(f"{pad}Entity: {node.name}")
        for s in node.body:
            print_ast(s, indent + 1)
    elif isinstance(node, AssignmentNode):
        print(f"{pad}Assign: {node.name} =")
        print_ast(node.value, indent + 1)
    elif isinstance(node, EventBindNode):
        print(f"{pad}EventBind: on {node.event} -> {node.handler}()")
    elif isinstance(node, IfNode):
        print(f"{pad}If:")
        print(f"{pad}  condition:")
        print_ast(node.condition, indent + 2)
        print(f"{pad}  body:")
        for s in node.body:
            print_ast(s, indent + 2)
    elif isinstance(node, BinOpNode):
        print(f"{pad}BinOp: {node.op}")
        print_ast(node.left, indent + 1)
        print_ast(node.right, indent + 1)
    elif isinstance(node, LiteralNode):
        print(f"{pad}Literal({node.kind}): {node.value!r}")
    elif isinstance(node, IdentifierNode):
        print(f"{pad}Identifier: {node.name}")


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    from lexer import SAMPLE_SOURCE

    tokens = Lexer(SAMPLE_SOURCE).tokenize()
    parser = Parser(tokens)
    ast = parser.parse()
    print_ast(ast)