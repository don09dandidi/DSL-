import random
import re

MAX_REPEAT = 5  # limit for * and + operators


def parse_and_generate(pattern: str, trace: bool = False) -> tuple[str, list[str]]:
    """
    Dynamically parse and generate a string from a regex-like pattern.
    Returns (generated_string, trace_steps).
    """
    steps = []
    result = _generate(pattern, steps, trace)
    return result, steps


def _generate(pattern: str, steps: list, trace: bool) -> str:
    """Recursive generator that processes the pattern left-to-right."""
    result = []
    i = 0
    n = len(pattern)

    while i < n:
        # Skip spaces in pattern
        if pattern[i] == ' ':
            i += 1
            continue

        # Group: (A|B|C)
        if pattern[i] == '(':
            # Find matching closing paren
            depth = 0
            j = i
            while j < n:
                if pattern[j] == '(':
                    depth += 1
                elif pattern[j] == ')':
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            group_content = pattern[i+1:j]
            quantifier, skip = _get_quantifier(pattern, j+1)
            chosen = _apply_quantifier(group_content, quantifier, steps, trace, is_group=True)
            result.append(chosen)
            i = j + 1 + skip

        # Single char with possible quantifier
        else:
            char = pattern[i]
            quantifier, skip = _get_quantifier(pattern, i+1)
            chosen = _apply_quantifier(char, quantifier, steps, trace, is_group=False)
            result.append(chosen)
            i = i + 1 + skip

    return ''.join(result)


def _get_quantifier(pattern: str, pos: int) -> tuple[str, int]:
    """
    Read quantifier starting at pos. Returns (quantifier_string, chars_consumed).
    Quantifiers: *, +, ?, ^N or {N} where N is a digit.
    """
    if pos >= len(pattern):
        return ('1', 0)

    ch = pattern[pos]

    if ch == '*':
        return ('*', 1)
    elif ch == '+':
        return ('+', 1)
    elif ch == '?':
        return ('?', 1)
    elif ch == '^':
        # ^N  – caret followed by one or more digits
        j = pos + 1
        while j < len(pattern) and pattern[j].isdigit():
            j += 1
        num = pattern[pos+1:j]
        if num:
            return (num, j - pos)
        return ('1', 0)
    elif ch.isdigit() and pos > 0 and pattern[pos-1] == ')':
        # digit after closing paren treated as exact repeat
        j = pos
        while j < len(pattern) and pattern[j].isdigit():
            j += 1
        num = pattern[pos:j]
        return (num, j - pos)
    else:
        return ('1', 0)


def _apply_quantifier(token: str, quantifier: str, steps: list, trace: bool, is_group: bool) -> str:
    """Generate repetitions of token according to quantifier."""

    if quantifier == '*':
        count = random.randint(0, MAX_REPEAT)
        label = f"'{token}'" if not is_group else f"group({token})"
        if trace:
            steps.append(f"* operator on {label}: repeat {count} times (0..{MAX_REPEAT})")
    elif quantifier == '+':
        count = random.randint(1, MAX_REPEAT)
        label = f"'{token}'" if not is_group else f"group({token})"
        if trace:
            steps.append(f"+ operator on {label}: repeat {count} times (1..{MAX_REPEAT})")
    elif quantifier == '?':
        count = random.randint(0, 1)
        label = f"'{token}'" if not is_group else f"group({token})"
        if trace:
            steps.append(f"? operator on {label}: {'include' if count else 'omit'}")
    else:
        # exact count (digit or default '1')
        count = int(quantifier)
        label = f"'{token}'" if not is_group else f"group({token})"
        if trace and count != 1:
            steps.append(f"Exact repeat {count}x on {label}")

    parts = []
    for _ in range(count):
        if is_group:
            # Pick one alternative from A|B|C
            alternatives = _split_alternatives(token)
            chosen_alt = random.choice(alternatives)
            if trace:
                steps.append(f"  Group alternatives: {alternatives} → chose '{chosen_alt}'")
            parts.append(_generate(chosen_alt, steps, trace))
        else:
            parts.append(token)

    return ''.join(parts)


def _split_alternatives(group_content: str) -> list[str]:
    """Split 'A|B|C' respecting nested parens."""
    alternatives = []
    depth = 0
    current = []
    for ch in group_content:
        if ch == '(':
            depth += 1
            current.append(ch)
        elif ch == ')':
            depth -= 1
            current.append(ch)
        elif ch == '|' and depth == 0:
            alternatives.append(''.join(current))
            current = []
        else:
            current.append(ch)
    if current:
        alternatives.append(''.join(current))
    return alternatives


# ──────────────────────────────────────────────
# Variant 3 regular expressions
# ──────────────────────────────────────────────
VARIANT_3_REGEXES = [
    "O(P|Q|R)+ 2(3|4)",
    "A* B(C|D|E) F(G|H|I)^2",
    "J+ K(L|M|N)* O?(P|Q)^3",
]


def generate_examples(pattern: str, n: int = 5) -> list[str]:
    return [parse_and_generate(pattern)[0] for _ in range(n)]


def show_trace(pattern: str) -> None:
    result, steps = parse_and_generate(pattern, trace=True)
    print(f"\nPattern : {pattern}")
    print(f"Result  : {result}")
    print("Trace   :")
    if steps:
        for idx, step in enumerate(steps, 1):
            print(f"  {idx}. {step}")
    else:
        print("  (no special operators – literal concatenation)")


if __name__ == "__main__":
    print("=" * 60)
    print("Variant 3 – Regular Expression String Generator")
    print("=" * 60)

    for regex in VARIANT_3_REGEXES:
        print(f"\nRegex: {regex}")
        examples = generate_examples(regex, n=6)
        print("Generated:", examples)

    print("\n" + "=" * 60)
    print("BONUS – Processing Trace")
    print("=" * 60)
    for regex in VARIANT_3_REGEXES:
        show_trace(regex)
