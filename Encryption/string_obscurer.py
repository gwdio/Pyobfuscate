import ast
from typing import Set, Type

from .string_obscure_strategies import StringObscureStrategy


def _collect_docstring_ids(tree: ast.AST) -> Set[int]:
    ids: Set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                ids.add(id(node.body[0].value))
    return ids


class StringObfuscatorInjector(ast.NodeTransformer):

    def __init__(self, naming, strategy_class: Type[StringObscureStrategy], rng):
        self.strategy = strategy_class(naming, rng)
        self._docstring_ids: Set[int] = set()

    def visit_JoinedStr(self, node: ast.JoinedStr) -> ast.AST:
        # Do not descend into f-string internals — the Constant nodes inside
        # are format fragments, not independent string values.
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        if not isinstance(node.value, str):
            return node
        if id(node) in self._docstring_ids:
            return node
        new_expr = self.strategy.obfuscate(node.value)
        return ast.copy_location(new_expr, node)

    def apply(self, tree: ast.Module) -> ast.Module:
        self._docstring_ids = _collect_docstring_ids(tree)

        new_tree = self.visit(tree)

        get_decoder = getattr(self.strategy, "get_decoder", None)
        if callable(get_decoder):
            dec_nodes = get_decoder()
            if dec_nodes:
                if isinstance(dec_nodes, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    dec_nodes = [dec_nodes]
                new_tree.body = dec_nodes + new_tree.body

        return ast.fix_missing_locations(new_tree)
