class Grammar:
    """
    Regular Grammar from Lab 1, extended with Chomsky hierarchy classification.
    Productions format: {'S': ['aB', 'bA'], 'A': ['a', 'aS'], 'B': ['b']}
    """

    def __init__(self, VN, VT, P, S):
        self.VN = set(VN)   # Non-terminals
        self.VT = set(VT)   # Terminals
        self.P = P          # Productions dict
        self.S = S          # Start symbol

    def classify_chomsky(self):
        """
        Classify this grammar according to the Chomsky hierarchy.
        Returns (type_number, description).
        """
        # Check Type 3 — Regular
        if self._is_type3():
            return 3, "Type 3 - Regular Grammar"

        # Check Type 2 — Context-Free
        if self._is_type2():
            return 2, "Type 2 - Context-Free Grammar"

        # Check Type 1 — Context-Sensitive
        if self._is_type1():
            return 1, "Type 1 - Context-Sensitive Grammar"

        return 0, "Type 0 - Unrestricted Grammar"

    def _parse_rhs(self, prod):
        """
        Parse a production RHS string into a list of symbols (terminals or non-terminals).
        Non-terminals are matched greedily from self.VN (supports multi-char names like q0, q1).
        """
        symbols = []
        i = 0
        # Sort VN by length descending so longer names match first
        vn_sorted = sorted(self.VN, key=len, reverse=True)
        while i < len(prod):
            matched = False
            for nt in vn_sorted:
                if prod[i:].startswith(nt):
                    symbols.append(('NT', nt))
                    i += len(nt)
                    matched = True
                    break
            if not matched:
                symbols.append(('T', prod[i]))
                i += 1
        return symbols

    def _is_type3(self):
        """
        Right-linear: A -> tB or A -> t  (t ∈ VT, B ∈ VN)
        Left-linear:  A -> Bt or A -> t
        LHS must be a single non-terminal (possibly multi-char like q0).
        """
        right_linear = True
        left_linear = True

        for lhs, prods in self.P.items():
            if lhs not in self.VN:
                return False
            for prod in prods:
                if prod == 'ε':
                    continue
                symbols = self._parse_rhs(prod)
                types = [s[0] for s in symbols]
                # Right-linear: [T] or [T, NT]
                if not (types == ['T'] or types == ['T', 'NT']):
                    right_linear = False
                # Left-linear: [T] or [NT, T]
                if not (types == ['T'] or types == ['NT', 'T']):
                    left_linear = False

        return right_linear or left_linear

    def _is_type2(self):
        """
        Context-Free: LHS is always a single non-terminal (any length).
        RHS can be anything.
        """
        for lhs in self.P:
            if lhs not in self.VN:
                return False
        return True

    def _is_type1(self):
        """
        Context-Sensitive: |LHS| <= |RHS| for all productions,
        except possibly S -> ε if S doesn't appear on any RHS.
        """
        for lhs, prods in self.P.items():
            for prod in prods:
                if prod == 'ε':
                    # Allowed only for start symbol if it doesn't appear in any RHS
                    if lhs != self.S:
                        return False
                    s_in_rhs = any(
                        self.S in p
                        for rhs_list in self.P.values()
                        for p in rhs_list
                    )
                    if s_in_rhs:
                        return False
                else:
                    if len(lhs) > len(prod):
                        return False
        return True

    def generate_strings(self, max_length=6, max_count=10):
        """BFS generation of strings from the grammar."""
        from collections import deque
        results = set()
        queue = deque([self.S])

        while queue and len(results) < max_count:
            current = queue.popleft()
            # Find first non-terminal
            nt_pos = next(
                (i for i, c in enumerate(current) if c in self.VN),
                None
            )
            if nt_pos is None:
                if current != 'ε' and len(current) <= max_length:
                    results.add(current)
                continue
            nt = current[nt_pos]
            for prod in self.P.get(nt, []):
                expanded = current[:nt_pos] + ('' if prod == 'ε' else prod) + current[nt_pos+1:]
                if len(expanded) <= max_length + len(self.VN):
                    queue.append(expanded)

        return sorted(results)
