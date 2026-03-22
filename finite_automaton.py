from grammar import Grammar


class FiniteAutomaton:
    """
    Finite Automaton (FA) implementation.

    Supports:
    - Conversion to Regular Grammar
    - Determinism check (DFA vs NDFA)
    - NDFA to DFA conversion (subset construction)
    - Optional: Graphviz DOT export for visualization
    """

    def __init__(self, Q, Sigma, delta, q0, F):
        """
        Q     : set of states
        Sigma : input alphabet
        delta : transition dict  {state: {symbol: [list_of_states]}}
        q0    : initial state
        F     : set of final/accepting states
        """
        self.Q = set(Q)
        self.Sigma = set(Sigma)
        self.delta = delta
        self.q0 = q0
        self.F = set(F)

    # ------------------------------------------------------------------
    # 3a  Convert FA → Regular Grammar
    # ------------------------------------------------------------------
    def to_regular_grammar(self):
        """
        Right-linear grammar construction:
          For each transition  q --a--> p :
            production  q -> a p
          For each transition  q --a--> f  where f ∈ F :
            also add  q -> a
          Add  f -> ε  for each final state f (allows accepting).
        """
        VN = list(self.Q)
        VT = list(self.Sigma)
        P = {q: [] for q in self.Q}
        S = self.q0

        for state, transitions in self.delta.items():
            for symbol, targets in transitions.items():
                for target in targets:
                    # q -> a B  (non-final target keeps non-terminal)
                    P[state].append(f"{symbol}{target}")
                    # q -> a  (if target is accepting, can also stop here)
                    if target in self.F:
                        P[state].append(symbol)

        # ε-production for start state if it is also accepting
        if self.q0 in self.F:
            P[self.q0].append('ε')

        # Remove duplicate productions
        for q in P:
            P[q] = list(dict.fromkeys(P[q]))

        return Grammar(VN, VT, P, S)

    # ------------------------------------------------------------------
    # 3b  Determine DFA vs NDFA
    # ------------------------------------------------------------------
    def is_deterministic(self):
        """
        An FA is deterministic (DFA) if and only if:
          - For every (state, symbol) pair, there is AT MOST one transition.
          - There are no ε-transitions.
        """
        for state, transitions in self.delta.items():
            for symbol, targets in transitions.items():
                if symbol == 'ε':
                    return False
                if len(targets) > 1:
                    return False
        return True

    # ------------------------------------------------------------------
    # 3c  NDFA → DFA  (Subset / Powerset construction)
    # ------------------------------------------------------------------
    def to_dfa(self):
        """
        Classic subset construction algorithm.
        Returns a new FiniteAutomaton that is deterministic.
        """
        # Each DFA state is a frozenset of NDFA states
        start = frozenset([self.q0])
        dfa_states = {}     # frozenset -> string label
        dfa_delta = {}
        worklist = [start]
        visited = set()

        def label(fs):
            """Create a readable label like '{q0,q1}'."""
            return '{' + ','.join(sorted(fs)) + '}'

        dfa_states[start] = label(start)

        while worklist:
            current = worklist.pop()
            if current in visited:
                continue
            visited.add(current)

            cur_label = label(current)
            dfa_delta[cur_label] = {}

            for symbol in self.Sigma:
                # Compute the set of NDFA states reachable via `symbol`
                reachable = frozenset(
                    t
                    for state in current
                    for t in self.delta.get(state, {}).get(symbol, [])
                )
                if not reachable:
                    continue  # Dead state — omit (implicit rejection)

                reach_label = label(reachable)
                dfa_delta[cur_label][symbol] = [reach_label]

                if reachable not in dfa_states:
                    dfa_states[reachable] = reach_label
                    worklist.append(reachable)

        # Build DFA components
        dfa_Q = set(dfa_states.values())
        dfa_q0 = label(start)
        dfa_F = {
            lbl
            for fs, lbl in dfa_states.items()
            if fs & self.F  # Any NDFA accepting state in the subset
        }

        return FiniteAutomaton(dfa_Q, self.Sigma, dfa_delta, dfa_q0, dfa_F)

    # ------------------------------------------------------------------
    # Bonus 3d  — Graphviz DOT export
    # ------------------------------------------------------------------
    def to_dot(self):
        """
        Export the automaton as a Graphviz DOT string.
        Render with:  echo "<dot>" | dot -Tpng -o fa.png
        Or use graphviz Python package: graphviz.Source(fa.to_dot()).render(...)
        """
        lines = ['digraph FA {', '    rankdir=LR;']
        lines.append('    node [shape=doublecircle]; ' +
                     ' '.join(f'"{s}"' for s in self.F) + ';')
        lines.append('    node [shape=circle];')
        lines.append(f'    __start__ [shape=none label=""];')
        lines.append(f'    __start__ -> "{self.q0}";')

        for state, transitions in self.delta.items():
            # Group labels for parallel edges
            edge_labels = {}
            for symbol, targets in transitions.items():
                for t in targets:
                    key = (state, t)
                    edge_labels.setdefault(key, []).append(symbol)
            for (src, tgt), symbols in edge_labels.items():
                label = ','.join(sorted(symbols))
                lines.append(f'    "{src}" -> "{tgt}" [label="{label}"];')

        lines.append('}')
        return '\n'.join(lines)

    def __repr__(self):
        return (
            f"FA(\n  Q={sorted(self.Q)},\n  Σ={sorted(self.Sigma)},\n"
            f"  q0={self.q0},\n  F={sorted(self.F)}\n)"
        )
