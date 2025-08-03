import ast
from typing import Set


class Naming(ast.NodeVisitor):
    """
    Gathers all used names in the AST and allows creation of new unique names.
    """

    def __init__(self):
        self.used_names = set()
        self.generated_names = set()

    def visit_Name(self, node):
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.used_names.add(node.name)
        for arg in node.args.args:
            self.used_names.add(arg.arg)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.used_names.add(node.name)
        self.generic_visit(node)

    def analyze(self, tree: ast.AST):
        """Call this before any transformation to populate used name set."""
        self.visit(tree)

    def get_name(self, base: str = "_tmp") -> str:
        """Returns a unique name based on `base`, and marks it as used."""
        i = 0
        while True:
            candidate = f"{base}{i}"
            if candidate not in self.used_names and candidate not in self.generated_names:
                self.generated_names.add(candidate)
                self.used_names.add(candidate)
                return candidate
            i += 1

    def get_namespace(self) -> Set[str]:
        """Returns a set of all used names"""
        return set(self.used_names)