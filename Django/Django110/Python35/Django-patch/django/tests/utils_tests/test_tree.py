import copy
import unittest

from django.utils.tree import Node


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.node1_children = [('a', 1), ('b', 2)]
        self.node1 = Node(self.node1_children)
        self.node2 = Node()

    def test_str(self):
        self.assertEqual(str(self.node1), "(DEFAULT: ('a', 1), ('b', 2))")
        self.assertEqual(str(self.node2), "(DEFAULT: )")

    def test_repr(self):
        self.assertEqual(repr(self.node1),
                         "<Node: (DEFAULT: ('a', 1), ('b', 2))>")
        self.assertEqual(repr(self.node2), "<Node: (DEFAULT: )>")

    def test_len(self):
        self.assertEqual(len(self.node1), 2)
        self.assertEqual(len(self.node2), 0)

    def test_bool(self):
        self.assertTrue(self.node1)
        self.assertFalse(self.node2)

    def test_contains(self):
        self.assertIn(('a', 1), self.node1)
        self.assertNotIn(('a', 1), self.node2)

    def test_add(self):
        # start with the same children of node1 then add an item
        node3 = Node(self.node1_children)
        node3_added_child = ('c', 3)
        # add() returns the added data
        self.assertEqual(node3.add(node3_added_child, Node.default),
                         node3_added_child)
        # we added exactly one item, len() should reflect that
        self.assertEqual(len(self.node1) + 1, len(node3))
        self.assertEqual(str(node3), "(DEFAULT: ('a', 1), ('b', 2), ('c', 3))")

    def test_negate(self):
        # negated is False by default
        self.assertFalse(self.node1.negated)
        self.node1.negate()
        self.assertTrue(self.node1.negated)
        self.node1.negate()
        self.assertFalse(self.node1.negated)

    def test_deepcopy(self):
        node4 = copy.copy(self.node1)
        node5 = copy.deepcopy(self.node1)
        self.assertIs(self.node1.children, node4.children)
        self.assertIsNot(self.node1.children, node5.children)
