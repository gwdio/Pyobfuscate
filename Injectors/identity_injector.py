import ast
import random
from .identity_strategies import IdentityFuncStrategy


class IdentityFuncInjector(ast.NodeTransformer):
    """
    Inject identity-function junk around variable and constant expressions.

    Args:
      strategy: an instance of IdentityFuncStrategy
      chance: float between 0 and 1, probability to wrap each expr
    """
    def __init__(self, strategy: IdentityFuncStrategy, chance: float, rng: random.Random):
        self.strategy = strategy
        self.chance = chance
        self.rng = rng

    def visit_Name(self, node: ast.Name) -> ast.AST:
        # Leave assignments alone; only wrap loads and constants
        if isinstance(node.ctx, ast.Load) and self.rng.random() < self.chance:
            return self.strategy.wrap(node, self.rng)
        return node

    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        # Wrap literal constants (numbers, strings) as well
        if self.rng.random() < self.chance:
            return self.strategy.wrap(node, self.rng)
        return node

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
