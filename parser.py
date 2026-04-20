"""
Parser & AST for RoboScript  (Lab 4 — Formal Languages & Finite Automata)
Student: Strunga Daniel-Ioan, FAF-242

Grammar (EBNF):
    program     → entity*
    entity      → 'entity' IDENTIFIER '{' statement* '}'
    statement   → assignment
                | event_bind
                | if_stmt
                | while_stmt
                | return_stmt
                | expr_stmt
    assignment  → IDENTIFIER '=' expr
    event_bind  → 'on' IDENTIFIER '->' call_expr
    if_stmt     → 'if' expr '{' statement* '}' ('else' '{' statement* '}')?
    while_stmt  → 'while' expr '{' statement* '}'
    return_stmt → 'return' expr?
    expr_stmt   → expr
    expr        → or_expr
    or_expr     → and_expr ('||' and_expr)*
    and_expr    → equality ('&&' equality)*
    equality    → comparison (('==' | '!=') comparison)*
    comparison  → addition (('<' | '>' | '<=' | '>=') addition)*
    addition    → multiply (('+' | '-') multiply)*
    multiply    → unary (('*' | '/' | '%') unary)*
    unary       → ('!' | '-') unary | primary
    primary     → call_expr | IDENTIFIER | literal | '(' expr ')'
    call_expr   → IDENTIFIER '(' arg_list? ')'
    arg_list    → expr (',' expr)*
    literal     → INTEGER | FLOAT | STRING | BOOLEAN | 'nil'
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any, Union
from lexer import Lexer, Token, TokenType, SAMPLE_SOURCE


# ===========================================================================
# AST node hierarchy
# ===========================================================================

@dataclass
class ASTNode:
    """Base class for every node in the Abstract Syntax Tree."""

    def node_type(self) -> str:
        return self.__class__.__name__

    def to_dict(self) -> dict:
        """Recursively convert the node to a plain dict (for JSON output)."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Leaf / value nodes
# ---------------------------------------------------------------------------

@dataclass
class LiteralNode(ASTNode):
    """A constant value: integer, float, string, boolean, or nil."""
    value: Any
    kind: str  # 'int' | 'float' | 'string' | 'bool' | 'nil'

    def to_dict(self):
        return {"node": "Literal", "kind": self.kind, "value": self.value}


@dataclass
class IdentifierNode(ASTNode):
    """A reference to a named symbol (variable, function, …)."""
    name: str

    def to_dict(self):
        return {"node": "Identifier", "name": self.name}


# ---------------------------------------------------------------------------
# Expression nodes
# ---------------------------------------------------------------------------

@dataclass
class BinOpNode(ASTNode):
    """A binary infix operation: left <op> right."""
    left: ASTNode
    op: str
    right: ASTNode

    def to_dict(self):
        return {
            "node": "BinOp", "op": self.op,
            "left": self.left.to_dict(), "right": self.right.to_dict(),
        }


@dataclass
class UnaryOpNode(ASTNode):
    """A unary prefix operation: <op> operand."""
    op: str
    operand: ASTNode

    def to_dict(self):
        return {"node": "UnaryOp", "op": self.op, "operand": self.operand.to_dict()}


@dataclass
class CallNode(ASTNode):
    """A function/handler call: name(arg1, arg2, …)."""
    name: str
    args: List[ASTNode] = field(default_factory=list)

    def to_dict(self):
        return {
            "node": "Call", "name": self.name,
            "args": [a.to_dict() for a in self.args],
        }


# ---------------------------------------------------------------------------
# Statement nodes
# ---------------------------------------------------------------------------

@dataclass
class AssignmentNode(ASTNode):
    """Property / variable assignment: name = value."""
    name: str
    value: ASTNode

    def to_dict(self):
        return {"node": "Assignment", "name": self.name, "value": self.value.to_dict()}


@dataclass
class EventBindNode(ASTNode):
    """Event handler binding: on <event> -> handler(args…)."""
    event: str
    handler: CallNode

    def to_dict(self):
        return {"node": "EventBind", "event": self.event, "handler": self.handler.to_dict()}


@dataclass
class ReturnNode(ASTNode):
    """Return statement, optionally carrying a value."""
    value: Optional[ASTNode] = None

    def to_dict(self):
        return {"node": "Return", "value": self.value.to_dict() if self.value else None}


@dataclass
class IfNode(ASTNode):
    """If / else conditional block."""
    condition: ASTNode
    then_body: List[ASTNode] = field(default_factory=list)
    else_body: List[ASTNode] = field(default_factory=list)

    def to_dict(self):
        return {
            "node": "If",
            "condition": self.condition.to_dict(),
            "then": [s.to_dict() for s in self.then_body],
            "else": [s.to_dict() for s in self.else_body],
        }


@dataclass
class WhileNode(ASTNode):
    """While loop."""
    condition: ASTNode
    body: List[ASTNode] = field(default_factory=list)

    def to_dict(self):
        return {
            "node": "While",
            "condition": self.condition.to_dict(),
            "body": [s.to_dict() for s in self.body],
        }


@dataclass
class ExprStmtNode(ASTNode):
    """An expression used as a standalone statement (e.g. a bare call)."""
    expr: ASTNode

    def to_dict(self):
        return {"node": "ExprStmt", "expr": self.expr.to_dict()}


# ---------------------------------------------------------------------------
# Top-level nodes
# ---------------------------------------------------------------------------

@dataclass
class EntityNode(ASTNode):
    """An entity block: entity <Name> { … }."""
    name: str
    body: List[ASTNode] = field(default_factory=list)

    def to_dict(self):
        return {
            "node": "Entity", "name": self.name,
            "body": [s.to_dict() for s in self.body],
        }


@dataclass
class ProgramNode(ASTNode):
    """Root of the AST — a sequence of entity declarations."""
    entities: List[EntityNode] = field(default_factory=list)

    def to_dict(self):
        return {"node": "Program", "entities": [e.to_dict() for e in self.entities]}


# ===========================================================================
# Parser
# ===========================================================================

_BINOPS = {
    TokenType.PLUS, TokenType.MINUS, TokenType.STAR, TokenType.SLASH,
    TokenType.PERCENT, TokenType.EQ, TokenType.NEQ, TokenType.LT,
    TokenType.GT, TokenType.LTE, TokenType.GTE, TokenType.AND, TokenType.OR,
}

_STMT_END_TYPES = {TokenType.RBRACE, TokenType.EOF}


class ParseError(Exception):
    def __init__(self, token: Token, message: str):
        super().__init__(f"L{token.line}:C{token.column} — {message} (got {token.type.name} {token.value!r})")
        self.token = token


class Parser:
    """
    Recursive-descent parser that consumes a token list and builds an AST.
    Each grammar rule corresponds to one private method.
    """

    def __init__(self, tokens: List[Token]):
        # Drop noise tokens; the grammar doesn't care about whitespace or comments
        self.tokens = [
            t for t in tokens
            if t.type not in (TokenType.NEWLINE, TokenType.COMMENT)
        ]
        self.pos = 0

    # ------------------------------------------------------------------
    # Token-stream helpers
    # ------------------------------------------------------------------

    def _cur(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _expect(self, ttype: TokenType, value: str = None) -> Token:
        tok = self._cur()
        if tok.type != ttype:
            raise ParseError(tok, f"expected {ttype.name}")
        if value is not None and tok.value != value:
            raise ParseError(tok, f"expected {value!r}")
        return self._advance()

    def _match_type(self, *ttypes: TokenType) -> bool:
        return self._cur().type in ttypes

    def _match_kw(self, *words: str) -> bool:
        tok = self._cur()
        return tok.type == TokenType.KEYWORD and tok.value in words

    # ------------------------------------------------------------------
    # Grammar rules — top-level
    # ------------------------------------------------------------------

    def parse(self) -> ProgramNode:
        program = ProgramNode()
        while not self._match_type(TokenType.EOF):
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
        stmts: List[ASTNode] = []
        while not self._match_type(TokenType.RBRACE, TokenType.EOF):
            stmts.append(self._parse_statement())
        return stmts

    # ------------------------------------------------------------------
    # Statements
    # ------------------------------------------------------------------

    def _parse_statement(self) -> ASTNode:
        tok = self._cur()

        # on <event> -> handler()
        if tok.type == TokenType.KEYWORD and tok.value == 'on':
            return self._parse_event_bind()

        # if expr { … } [else { … }]
        if tok.type == TokenType.KEYWORD and tok.value == 'if':
            return self._parse_if()

        # while expr { … }
        if tok.type == TokenType.KEYWORD and tok.value == 'while':
            return self._parse_while()

        # return [expr]
        if tok.type == TokenType.KEYWORD and tok.value == 'return':
            return self._parse_return()

        # assignment: IDENTIFIER = expr  (look-ahead to distinguish from bare call)
        if (tok.type == TokenType.IDENTIFIER
                and self._peek().type == TokenType.ASSIGN):
            return self._parse_assignment()

        # expression statement  (e.g. bare function call)
        expr = self._parse_expr()
        return ExprStmtNode(expr=expr)

    def _parse_assignment(self) -> AssignmentNode:
        name = self._advance().value     # IDENTIFIER
        self._advance()                  # '='
        value = self._parse_expr()
        return AssignmentNode(name=name, value=value)

    def _parse_event_bind(self) -> EventBindNode:
        self._advance()                          # 'on'
        event = self._advance().value            # event name
        self._expect(TokenType.ARROW)            # '->'
        handler = self._parse_call()             # handler(args…)
        return EventBindNode(event=event, handler=handler)

    def _parse_if(self) -> IfNode:
        self._advance()                          # 'if'
        condition = self._parse_expr()
        self._expect(TokenType.LBRACE)
        then_body = self._parse_body()
        self._expect(TokenType.RBRACE)
        else_body: List[ASTNode] = []
        if self._match_kw('else'):
            self._advance()                      # 'else'
            self._expect(TokenType.LBRACE)
            else_body = self._parse_body()
            self._expect(TokenType.RBRACE)
        return IfNode(condition=condition, then_body=then_body, else_body=else_body)

    def _parse_while(self) -> WhileNode:
        self._advance()                          # 'while'
        condition = self._parse_expr()
        self._expect(TokenType.LBRACE)
        body = self._parse_body()
        self._expect(TokenType.RBRACE)
        return WhileNode(condition=condition, body=body)

    def _parse_return(self) -> ReturnNode:
        self._advance()                          # 'return'
        # If the next token looks like the start of an expression, parse it
        if not self._match_type(TokenType.RBRACE, TokenType.EOF):
            return ReturnNode(value=self._parse_expr())
        return ReturnNode(value=None)

    # ------------------------------------------------------------------
    # Expressions  (Pratt-style precedence climbing via recursive descent)
    # ------------------------------------------------------------------

    def _parse_expr(self) -> ASTNode:
        return self._parse_or()

    def _parse_or(self) -> ASTNode:
        left = self._parse_and()
        while self._match_type(TokenType.OR):
            op = self._advance().value
            right = self._parse_and()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_and(self) -> ASTNode:
        left = self._parse_equality()
        while self._match_type(TokenType.AND):
            op = self._advance().value
            right = self._parse_equality()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_equality(self) -> ASTNode:
        left = self._parse_comparison()
        while self._match_type(TokenType.EQ, TokenType.NEQ):
            op = self._advance().value
            right = self._parse_comparison()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_comparison(self) -> ASTNode:
        left = self._parse_addition()
        while self._match_type(TokenType.LT, TokenType.GT,
                                TokenType.LTE, TokenType.GTE):
            op = self._advance().value
            right = self._parse_addition()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_addition(self) -> ASTNode:
        left = self._parse_multiply()
        while self._match_type(TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._parse_multiply()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_multiply(self) -> ASTNode:
        left = self._parse_unary()
        while self._match_type(TokenType.STAR, TokenType.SLASH,
                                TokenType.PERCENT):
            op = self._advance().value
            right = self._parse_unary()
            left = BinOpNode(left=left, op=op, right=right)
        return left

    def _parse_unary(self) -> ASTNode:
        if self._match_type(TokenType.NOT, TokenType.MINUS):
            op = self._advance().value
            operand = self._parse_unary()
            return UnaryOpNode(op=op, operand=operand)
        return self._parse_primary()

    def _parse_primary(self) -> ASTNode:
        tok = self._cur()

        # Grouped expression
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        # Function call: IDENTIFIER ( … )
        if (tok.type == TokenType.IDENTIFIER
                and self._peek().type == TokenType.LPAREN):
            return self._parse_call()

        # Literals
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

        # Plain identifier
        if tok.type == TokenType.IDENTIFIER:
            self._advance()
            return IdentifierNode(name=tok.value)

        # Unrecognised — skip and return nil to keep parsing
        self._advance()
        return LiteralNode(value=tok.value, kind='nil')

    def _parse_call(self) -> CallNode:
        name = self._advance().value     # IDENTIFIER
        self._expect(TokenType.LPAREN)
        args: List[ASTNode] = []
        if not self._match_type(TokenType.RPAREN):
            args.append(self._parse_expr())
            while self._match_type(TokenType.COMMA):
                self._advance()
                args.append(self._parse_expr())
        self._expect(TokenType.RPAREN)
        return CallNode(name=name, args=args)


# ===========================================================================
# AST pretty-printer  (tree-art style)
# ===========================================================================

def print_ast(node: ASTNode, prefix: str = '', is_last: bool = True):
    connector = '└── ' if is_last else '├── '
    child_prefix = prefix + ('    ' if is_last else '│   ')

    def _label(n: ASTNode) -> str:
        if isinstance(n, ProgramNode):
            return f"Program  [{len(n.entities)} entit{'y' if len(n.entities)==1 else 'ies'}]"
        if isinstance(n, EntityNode):
            return f"Entity  \"{n.name}\""
        if isinstance(n, AssignmentNode):
            return f"Assign  {n.name} ="
        if isinstance(n, EventBindNode):
            return f"EventBind  on {n.event} ->"
        if isinstance(n, IfNode):
            suffix = " [+else]" if n.else_body else ""
            return f"If{suffix}"
        if isinstance(n, WhileNode):
            return "While"
        if isinstance(n, ReturnNode):
            return "Return"
        if isinstance(n, ExprStmtNode):
            return "ExprStmt"
        if isinstance(n, BinOpNode):
            return f"BinOp  \"{n.op}\""
        if isinstance(n, UnaryOpNode):
            return f"UnaryOp  \"{n.op}\""
        if isinstance(n, CallNode):
            return f"Call  {n.name}()"
        if isinstance(n, LiteralNode):
            return f"Literal({n.kind})  {n.value!r}"
        if isinstance(n, IdentifierNode):
            return f"Identifier  \"{n.name}\""
        return n.node_type()

    if prefix == '' and not isinstance(node, ProgramNode):
        print(_label(node))
    else:
        print(f"{prefix}{connector}{_label(node)}")

    def _children(n: ASTNode):
        if isinstance(n, ProgramNode):
            return n.entities
        if isinstance(n, EntityNode):
            return n.body
        if isinstance(n, AssignmentNode):
            return [n.value]
        if isinstance(n, EventBindNode):
            return [n.handler]
        if isinstance(n, IfNode):
            kids = list(n.then_body)
            if n.else_body:
                kids.append(_ElseBlock(n.else_body))
            return [n.condition] + kids
        if isinstance(n, WhileNode):
            return [n.condition] + list(n.body)
        if isinstance(n, ReturnNode):
            return [n.value] if n.value else []
        if isinstance(n, ExprStmtNode):
            return [n.expr]
        if isinstance(n, BinOpNode):
            return [n.left, n.right]
        if isinstance(n, UnaryOpNode):
            return [n.operand]
        if isinstance(n, CallNode):
            return list(n.args)
        return []

    children = _children(node)
    for i, child in enumerate(children):
        print_ast(child, child_prefix, is_last=(i == len(children) - 1))


class _ElseBlock:
    """Synthetic node for pretty-printing the else branch."""
    def __init__(self, stmts):
        self.stmts = stmts


# Patch _children to handle the synthetic node
_orig_print_ast = print_ast

def print_ast(node, prefix='', is_last=True):  # noqa: F811
    connector = '└── ' if is_last else '├── '
    child_prefix = prefix + ('    ' if is_last else '│   ')

    if isinstance(node, _ElseBlock):
        label = "Else"
        children = node.stmts
    elif isinstance(node, ProgramNode):
        label = f"Program  [{len(node.entities)} entit{'y' if len(node.entities)==1 else 'ies'}]"
        children = node.entities
    elif isinstance(node, EntityNode):
        label = f"Entity  \"{node.name}\""
        children = node.body
    elif isinstance(node, AssignmentNode):
        label = f"Assign  {node.name} ="
        children = [node.value]
    elif isinstance(node, EventBindNode):
        label = f"EventBind  on {node.event} ->"
        children = [node.handler]
    elif isinstance(node, IfNode):
        label = "If [+else]" if node.else_body else "If"
        kids: List[ASTNode] = [node.condition] + list(node.then_body)
        if node.else_body:
            kids.append(_ElseBlock(node.else_body))
        children = kids
    elif isinstance(node, WhileNode):
        label = "While"
        children = [node.condition] + list(node.body)
    elif isinstance(node, ReturnNode):
        label = "Return"
        children = [node.value] if node.value else []
    elif isinstance(node, ExprStmtNode):
        label = "ExprStmt"
        children = [node.expr]
    elif isinstance(node, BinOpNode):
        label = f"BinOp  \"{node.op}\""
        children = [node.left, node.right]
    elif isinstance(node, UnaryOpNode):
        label = f"UnaryOp  \"{node.op}\""
        children = [node.operand]
    elif isinstance(node, CallNode):
        label = f"Call  {node.name}()"
        children = list(node.args)
    elif isinstance(node, LiteralNode):
        label = f"Literal({node.kind})  {node.value!r}"
        children = []
    elif isinstance(node, IdentifierNode):
        label = f"Identifier  \"{node.name}\""
        children = []
    else:
        label = type(node).__name__
        children = []

    if prefix == '':
        print(label)
    else:
        print(f"{prefix}{connector}{label}")

    for i, child in enumerate(children):
        print_ast(child, child_prefix, is_last=(i == len(children) - 1))


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == '__main__':
    print("=" * 62)
    print("ROBOSCRIPT — LEXER OUTPUT")
    print("=" * 62)
    tokens = Lexer(SAMPLE_SOURCE).tokenize()
    print(f"{'TYPE':<15} {'VALUE':<22} {'L':>3}  {'C':>3}  {'OK':>2}")
    print('-' * 52)
    for tok in tokens:
        if tok.type == TokenType.NEWLINE:
            continue
        ok = '✓' if tok.validate() else '✗'
        print(f"{tok.type.name:<15} {tok.value!r:<22} {tok.line:>3}  {tok.column:>3}  {ok:>2}")

    print("\n" + "=" * 62)
    print("ROBOSCRIPT — ABSTRACT SYNTAX TREE")
    print("=" * 62)
    parser = Parser(tokens)
    ast = parser.parse()
    print_ast(ast)

    print("\n" + "=" * 62)
    print("ROBOSCRIPT — AST as JSON")
    print("=" * 62)
    print(json.dumps(ast.to_dict(), indent=2))
