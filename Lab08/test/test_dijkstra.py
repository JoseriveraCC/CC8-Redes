import unittest
from pathlib import Path

import dijkstra
import read


HERE = Path(__file__).parent


def steps(number):
    source, graph = read.routingFile(HERE / f"topo{number}.txt")
    return dijkstra.init(source, graph)


class DijkstraTests(unittest.TestCase):
    def test_document_examples(self):
        self.assertEqual(steps(1), [
            (0, "1, u", "1, u", "∞, -", "u"),
            (1, "1, u", "1, u", "3, v", "v"),
            (2, "1, u", "1, u", "2, w", "w"),
            (3, "1, u", "1, u", "2, w", "x"),
        ])
        self.assertEqual(steps(2)[1], (1, "5, f", "6, g", "9, g", "g"))
        self.assertEqual(steps(2)[-1], (3, "5, f", "6, g", "8, h", "i"))
        self.assertEqual(steps(3)[-1], (3, "6, d", "3, a", "5, c", "b"))

    def test_topo7_and_tie_order(self):
        result = steps(7)
        self.assertEqual([row[-1] for row in result],
                         list("hopijtmnsrqkl"))
        self.assertEqual(result[-1], (
            12, "3, p", "3, p", "9, q", "10, k", "5, t", "6, m",
            "1, h", "2, o", "8, r", "7, s", "6, m", "4, i", "l"
        ))

    def test_disconnected_node(self):
        self.assertEqual(dijkstra.init("a", {"a": {}, "b": {}}),
                         [(0, "∞, -", "a"), (1, "∞, -", "b")])


if __name__ == "__main__":
    unittest.main()
