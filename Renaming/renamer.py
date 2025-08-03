import ast
import random
import string
from typing import Set, Dict


class Renamer(ast.NodeTransformer):
    """
    1) Collect every user-defined name (defs, args, store-context Names).
    2) Generate a garbage name for each.
    3) Rewrite the entire AST, replacing all occurrences.
    """

    def __init__(self, namespace: Set[str]):
        # avoid colliding with any existing names
        self.namespace = set(namespace)
        self.to_rename: Set[str] = set()
        self.mapping: Dict[str, str] = {}

    def _generate_name(self) -> str:
        """Produce a valid Python identifier not in self.namespace or already mapped."""
        while True:
            name = random.choice(string.ascii_letters + "_") + \
                   "".join(random.choices(string.ascii_letters + string.digits + "_", k=7))
            if name.isidentifier() and name not in self.namespace and name not in self.mapping.values():
                self.namespace.add(name)
                return name

    # ——— PASS 1: COLLECT ———

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.to_rename.add(node.name)
        for arg in node.args.args:
            self.to_rename.add(arg.arg)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.to_rename.add(node.name)
        return self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda):
        for arg in node.args.args:
            self.to_rename.add(arg.arg)
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # any name *defined* (Store) should be collected
        if isinstance(node.ctx, ast.Store):
            self.to_rename.add(node.id)
        return node

    # ——— APPLY builds mapping then does a second pass ———

    def apply(self, tree: ast.AST) -> ast.AST:
        # First pass: collect
        self.visit(tree)

        # Build mapping
        for old in self.to_rename:
            self.mapping[old] = self._generate_name()

        # Second pass: rewrite
        return self._rewrite(tree)

    # ——— PASS 2: REWRITE via a fresh transformer ———

    def _rewrite(self, tree: ast.AST) -> ast.AST:
        return _Rewriter(self.mapping).visit(tree)


class _Rewriter(ast.NodeTransformer):
    """Helper for the second pass—just applies the mapping everywhere."""

    def __init__(self, mapping: Dict[str, str]):
        self.mapping = mapping

    def visit_FunctionDef(self, node: ast.FunctionDef):
        node.name = self.mapping.get(node.name, node.name)
        for arg in node.args.args:
            arg.arg = self.mapping.get(arg.arg, arg.arg)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        node.name = self.mapping.get(node.name, node.name)
        return self.generic_visit(node)

    def visit_Lambda(self, node: ast.Lambda):
        for arg in node.args.args:
            arg.arg = self.mapping.get(arg.arg, arg.arg)
        return self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node
