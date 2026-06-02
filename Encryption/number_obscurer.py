# number_obscurer.py
import ast
from typing import Type
from .number_obscure_strategies import NumberObscureStrategy

class NumberObscurerInjector(ast.NodeTransformer):
    """
    AST transformer that replaces every integer literal with an obfuscated
    expression provided by a NumberObscureStrategy, and then injects the
    strategy's decoder if it has one.
    """
    def __init__(self, naming, strategy_class: Type[NumberObscureStrategy]):
        """
        naming: your shared Naming instance
        strategy_class: a subclass of NumberObscureStrategy
                        which will be instantiated with naming
        """
        self.naming = naming
        # injector is now responsible for instantiation
        self.strategy = strategy_class(naming)

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        # Only replace integer literals
        if isinstance(node.value, int):
            new_expr = self.strategy.obfuscate(node.value)
            return ast.copy_location(new_expr, node)
        return node

    def apply(self, tree: ast.Module) -> ast.Module:
        """
        Apply obfuscation and inject decoder if provided.
        """
        # 1) Obfuscate all constants
        new_tree = self.visit(tree)

        # 2) Inject decoder, if strategy provides one
        get_decoder = getattr(self.strategy, "get_decoder", None)
        if callable(get_decoder):
            dec_nodes = get_decoder()
            if dec_nodes:
                # Normalize to list
                if isinstance(dec_nodes, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    dec_nodes = [dec_nodes]
                new_tree.body = dec_nodes + new_tree.body

        # 3) Fix locations and return
        return ast.fix_missing_locations(new_tree)
