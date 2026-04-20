"""
Chomsky Normal Form (CNF) Converter
Course: Formal Languages & Finite Automata
Student: Strunga Daniel-Ioan, FAF-242
"""

from itertools import product
import copy


class Grammar:
    """
    Represents a Context-Free Grammar and provides CNF normalization.
    Productions are stored as: dict[str, list[list[str]]]
    e.g. {'S': [['A', 'B'], ['a']], 'A': [['a']]}
    """

    def __init__(self, variables: set, terminals: set, productions: dict, start: str):
        self.variables = set(variables)
        self.terminals = set(terminals)
        self.productions = {k: [list(p) for p in v] for k, v in productions.items()}
        self.start = start

    # ------------------------------------------------------------------ #
    #  Step 0 – ensure start symbol never appears on the RHS              #
    # ------------------------------------------------------------------ #
    def _eliminate_start_from_rhs(self):
        new_start = self.start + "0"
        while new_start in self.variables:
            new_start += "0"
        self.productions[new_start] = [[self.start]]
        self.variables.add(new_start)
        self.start = new_start

    # ------------------------------------------------------------------ #
    #  Step 1 – remove ε-productions                                      #
    # ------------------------------------------------------------------ #
    def _nullable_symbols(self) -> set:
        nullable = set()
        # direct ε-producers
        for v, rules in self.productions.items():
            for rhs in rules:
                if rhs == ['ε'] or rhs == []:
                    nullable.add(v)
        # closure
        changed = True
        while changed:
            changed = False
            for v, rules in self.productions.items():
                if v in nullable:
                    continue
                for rhs in rules:
                    if all(sym in nullable for sym in rhs):
                        nullable.add(v)
                        changed = True
        return nullable

    def _eliminate_epsilon(self):
        nullable = self._nullable_symbols()
        new_prods = {}
        for v, rules in self.productions.items():
            new_rules = []
            for rhs in rules:
                if rhs == ['ε'] or rhs == []:
                    continue
                # generate all combinations with nullable symbols omitted
                positions = [i for i, sym in enumerate(rhs) if sym in nullable]
                for mask in range(1 << len(positions)):
                    omit = {positions[j] for j in range(len(positions)) if mask & (1 << j)}
                    new_rhs = [sym for i, sym in enumerate(rhs) if i not in omit]
                    if new_rhs and new_rhs not in new_rules:
                        new_rules.append(new_rhs)
            if new_rules:
                new_prods[v] = new_rules
        # keep start → ε if start was nullable
        if self.start in nullable:
            new_prods.setdefault(self.start, [])
            if ['ε'] not in new_prods[self.start]:
                new_prods[self.start].append(['ε'])
        self.productions = new_prods

    # ------------------------------------------------------------------ #
    #  Step 2 – remove unit productions  A → B                           #
    # ------------------------------------------------------------------ #
    def _unit_closure(self, v: str) -> set:
        reachable = {v}
        queue = [v]
        while queue:
            cur = queue.pop()
            for rhs in self.productions.get(cur, []):
                if len(rhs) == 1 and rhs[0] in self.variables and rhs[0] not in reachable:
                    reachable.add(rhs[0])
                    queue.append(rhs[0])
        return reachable

    def _eliminate_unit_productions(self):
        new_prods = {}
        for v in self.variables:
            closure = self._unit_closure(v)
            rules = []
            for u in closure:
                for rhs in self.productions.get(u, []):
                    # skip unit productions themselves
                    if len(rhs) == 1 and rhs[0] in self.variables:
                        continue
                    if rhs not in rules:
                        rules.append(rhs)
            new_prods[v] = rules
        self.productions = new_prods

    # ------------------------------------------------------------------ #
    #  Step 3 – remove inaccessible symbols                               #
    # ------------------------------------------------------------------ #
    def _eliminate_inaccessible(self):
        reachable = set()
        queue = [self.start]
        reachable.add(self.start)
        while queue:
            cur = queue.pop()
            for rhs in self.productions.get(cur, []):
                for sym in rhs:
                    if sym in self.variables and sym not in reachable:
                        reachable.add(sym)
                        queue.append(sym)
        self.variables = reachable
        self.productions = {v: r for v, r in self.productions.items() if v in reachable}

    # ------------------------------------------------------------------ #
    #  Step 4 – remove non-productive symbols                             #
    # ------------------------------------------------------------------ #
    def _productive_symbols(self) -> set:
        productive = set()
        changed = True
        while changed:
            changed = False
            for v, rules in self.productions.items():
                if v in productive:
                    continue
                for rhs in rules:
                    if all(sym in productive or sym in self.terminals for sym in rhs):
                        productive.add(v)
                        changed = True
        return productive

    def _eliminate_non_productive(self):
        productive = self._productive_symbols()
        self.variables = self.variables & productive
        new_prods = {}
        for v in self.variables:
            new_rules = [rhs for rhs in self.productions.get(v, [])
                         if all(sym in productive or sym in self.terminals for sym in rhs)]
            if new_rules:
                new_prods[v] = new_rules
        self.productions = new_prods

    # ------------------------------------------------------------------ #
    #  Step 5 – convert to proper CNF                                     #
    # ------------------------------------------------------------------ #
    def _fresh_var(self, base: str) -> str:
        candidate = base
        idx = 1
        while candidate in self.variables:
            candidate = f"{base}_{idx}"
            idx += 1
        return candidate

    def _to_cnf(self):
        """
        Two sub-steps:
        (a) Replace terminals in long rules with unit variables  T_a → a
        (b) Break rules of length ≥ 3 into binary rules
        """
        terminal_map: dict[str, str] = {}  # terminal → new variable

        def var_for_terminal(t: str) -> str:
            if t not in terminal_map:
                base = f"T_{t.upper()}"
                fresh = self._fresh_var(base)
                terminal_map[t] = fresh
                self.variables.add(fresh)
                self.productions[fresh] = [[t]]
            return terminal_map[t]

        extra_prods: dict = {}   # new vars created during this step
        pair_map: dict = {}      # (X,Y) → fresh var, for deduplication
        new_prods = {}
        for v, rules in list(self.productions.items()):
            new_rules = []
            for rhs in rules:
                rhs = list(rhs)
                # (a) replace terminals in rules of length ≥ 2
                if len(rhs) >= 2:
                    new_rhs = []
                    for s in rhs:
                        if s in self.terminals:
                            if s not in terminal_map:
                                base = f"T_{s.upper()}"
                                fresh = self._fresh_var(base)
                                terminal_map[s] = fresh
                                self.variables.add(fresh)
                                extra_prods[fresh] = [[s]]
                            new_rhs.append(terminal_map[s])
                        else:
                            new_rhs.append(s)
                    rhs = new_rhs
                # (b) binarise rules of length ≥ 3
                while len(rhs) > 2:
                    pair = tuple(rhs[-2:])
                    if pair not in pair_map:
                        base = "B_" + pair[0] + "_" + pair[1]
                        fresh = self._fresh_var(base)
                        pair_map[pair] = fresh
                        self.variables.add(fresh)
                        extra_prods[fresh] = [list(pair)]
                    rhs = rhs[:-2] + [pair_map[pair]]
                new_rules.append(rhs)
            new_prods[v] = new_rules
        self.productions = new_prods
        self.productions.update(extra_prods)

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def to_cnf(self) -> "Grammar":
        """
        Returns a NEW Grammar object in Chomsky Normal Form.
        Steps applied (in order):
          0. Isolate start symbol
          1. Eliminate ε-productions
          2. Eliminate unit productions
          3. Eliminate inaccessible symbols
          4. Eliminate non-productive symbols
          5. Convert to CNF binary/terminal rules
        """
        g = copy.deepcopy(self)
        g._eliminate_start_from_rhs()
        g._eliminate_epsilon()
        g._eliminate_unit_productions()
        g._eliminate_inaccessible()
        g._eliminate_non_productive()
        g._to_cnf()
        return g

    def __str__(self) -> str:
        lines = [f"Start: {self.start}",
                 f"Variables: {sorted(self.variables)}",
                 f"Terminals: {sorted(self.terminals)}",
                 "Productions:"]
        for v in sorted(self.productions):
            for rhs in self.productions[v]:
                lines.append(f"  {v} → {' '.join(rhs) if rhs else 'ε'}")
        return "\n".join(lines)


# ------------------------------------------------------------------ #
#  Variant-specific grammar (Variant 23)                             #
# ------------------------------------------------------------------ #
def get_variant_grammar() -> Grammar:
    """
    Variant 23 grammar from the lab assignment.
    VN = {S, A, B, C, D}
    VT = {a, b}
    Productions:
      S → aB | bA | B
      A → b | aD | AS | bAAB | ε
      B → a | bS | A
      C → AB
      D → BB
    """
    variables = {'S', 'A', 'B', 'C', 'D'}
    terminals = {'a', 'b'}
    productions = {
        'S': [['a', 'B'], ['b', 'A'], ['B']],
        'A': [['b'], ['a', 'D'], ['A', 'S'], ['b', 'A', 'A', 'B'], ['ε']],
        'B': [['a'], ['b', 'S'], ['A']],
        'C': [['A', 'B']],
        'D': [['B', 'B']],
    }
    return Grammar(variables, terminals, productions, 'S')


# ------------------------------------------------------------------ #
#  Main / demo                                                        #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    print("=" * 60)
    print("VARIANT 23 GRAMMAR")
    print("=" * 60)
    g = get_variant_grammar()
    print(g)

    print("\n" + "=" * 60)
    print("CONVERTING TO CNF …")
    print("=" * 60)
    cnf = g.to_cnf()
    print(cnf)

    # Verify every rule is CNF-valid
    print("\n" + "=" * 60)
    print("CNF VALIDATION")
    print("=" * 60)
    ok = True
    for v, rules in cnf.productions.items():
        for rhs in rules:
            if v == cnf.start and rhs == ['ε']:
                continue  # allowed if start was nullable
            if len(rhs) == 1 and rhs[0] in cnf.terminals:
                continue  # A → a  ✓
            if len(rhs) == 2 and all(s in cnf.variables for s in rhs):
                continue  # A → B C  ✓
            print(f"  ✗ NOT CNF: {v} → {' '.join(rhs)}")
            ok = False
    if ok:
        print("  ✓ All productions are in Chomsky Normal Form!")

    # ----------------------------------------------------------------
    # BONUS: test on a custom grammar
    # ----------------------------------------------------------------
    print("\n" + "=" * 60)
    print("BONUS – CUSTOM GRAMMAR TEST")
    print("=" * 60)
    custom = Grammar(
        variables={'S', 'X', 'Y'},
        terminals={'0', '1'},
        productions={
            'S': [['X', 'Y'], ['1']],
            'X': [['0'], ['X', 'X'], ['ε']],
            'Y': [['1'], ['S', 'Y']],
        },
        start='S'
    )
    print("Original:")
    print(custom)
    print("\nCNF:")
    print(custom.to_cnf())
