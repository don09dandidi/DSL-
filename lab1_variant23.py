import random


class Grammar:
    def __init__(self):
        self.VN = {'S', 'B', 'C'}
        self.VT = {'a', 'b', 'c'}
        self.S = 'S'
        
        
        self.P = {
            'S': [('a', 'B')],
            'B': [('a', 'C'), ('b', 'B')],
            'C': [('b', 'B'), ('c', None), ('a', 'S')]
        }

    def generate_string(self):
        #generate a valid string by randomly applying productions.

        result = ''
        current = self.S
        while current is not None:
            productions = self.P[current]
            terminal, next_state = random.choice(productions)
            result += terminal
            current = next_state
        return result

    def to_finite_automaton(self):
        #convert this grammar to an equivalent Finite Automaton.
        transitions = {}
        final_states = set()

        for state, prods in self.P.items():
            for (terminal, next_state) in prods:
                if next_state is None:
                    final_states.add('F')
                    transitions[(state, terminal)] = 'F'
                else:
                    transitions[(state, terminal)] = next_state

        return FiniteAutomaton(
            states={'S', 'B', 'C', 'F'},
            alphabet={'a', 'b', 'c'},
            transitions=transitions,
            start='S',
            final_states=final_states
        )


class FiniteAutomaton:
    def __init__(self, states, alphabet, transitions, start, final_states):
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start = start
        self.final_states = final_states

    def accepts(self, string):
        #Check if the input string is accepted by the automaton.
        current = self.start
        for ch in string:
            key = (current, ch)
            if key not in self.transitions:
                return False
            current = self.transitions[key]
        return current in self.final_states


if __name__ == "__main__":
    g = Grammar()
    fa = g.to_finite_automaton()

    print("=== Generated Strings ===")
    for i in range(5):
        s = g.generate_string()
        print(f"  {i+1}. '{s}' -> accepted by FA: {fa.accepts(s)}")

    print("\n=== Additional Validation Tests ===")
    tests = ["aac", "abac", "aabac", "ac", "xyz", "aaaac", "c"]
    for t in tests:
        print(f"  '{t}' -> {fa.accepts(t)}")
