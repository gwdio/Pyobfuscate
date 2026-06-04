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

    def __init__(self, namespace: Set[str], rng: random.Random):
        # avoid colliding with any existing names
        self.namespace = set(namespace)
        self.rng = rng
        self.to_rename: Set[str] = set()
        self.method_names: Set[str] = set()
        self.mapping: Dict[str, str] = {}

    def _generate_name(self) -> str:
        """Produce a valid Python identifier not in self.namespace or already mapped."""
        while True:
            name = self.rng.choice(string.ascii_letters + "_") + \
                   "".join(self.rng.choices(string.ascii_letters + string.digits + "_", k=7))
            if name.isidentifier() and name not in self.namespace and name not in self.mapping.values():
                self.namespace.add(name)
                return name

    # ——— PASS 1: COLLECT ———

    def visit_FunctionDef(self, node: ast.FunctionDef):
        if not (node.name.startswith('__') and node.name.endswith('__')):
            self.to_rename.add(node.name)
        for arg in node.args.args:
            self.to_rename.add(arg.arg)
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        self.to_rename.add(node.name)
        # Track direct method names separately so visit_Attribute only renames
        # user-defined method call sites, not same-named stdlib attributes.
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = item.name
                if not (name.startswith('__') and name.endswith('__')):
                    self.method_names.add(name)
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

        # Build mapping (sorted for deterministic RNG consumption order)
        for old in sorted(self.to_rename):
            self.mapping[old] = self._generate_name()

        # Restrict attribute rewriting to user-defined method names only,
        # to avoid incorrectly renaming stdlib attribute accesses (e.g. collections.deque).
        method_mapping = {k: v for k, v in self.mapping.items() if k in self.method_names}

        # Second pass: rewrite
        return self._rewrite(tree, method_mapping)

    # ——— PASS 2: REWRITE via a fresh transformer ———

    def _rewrite(self, tree: ast.AST, method_mapping: Dict[str, str]) -> ast.AST:
        return _Rewriter(self.mapping, method_mapping).visit(tree)


class _Rewriter(ast.NodeTransformer):
    """Helper for the second pass—just applies the mapping everywhere."""

    def __init__(self, mapping: Dict[str, str], method_mapping: Dict[str, str]):
        self.mapping = mapping
        self.method_mapping = method_mapping

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

    def visit_Global(self, node: ast.Global):
        # ast.Global stores plain strings, not ast.Name nodes — rename them explicitly.
        node.names = [self.mapping.get(n, n) for n in node.names]
        return node

    def visit_Name(self, node: ast.Name):
        if node.id in self.mapping:
            node.id = self.mapping[node.id]
        return node

    def visit_Attribute(self, node: ast.Attribute):
        # Use method_mapping (not full mapping) to avoid renaming stdlib attribute
        # accesses that happen to share a name with a user-defined variable.
        node.attr = self.method_mapping.get(node.attr, node.attr)
        return self.generic_visit(node)
