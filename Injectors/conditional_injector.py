import ast
import random
from typing import List, Type
from .junk_conditional_strategies import JunkConditionalStrategy

class ConditionalInjector(ast.NodeTransformer):
    """
    Framework for injecting constant conditional wrappers around AST statements.

    Process:
    1. Receive a list of `JunkConditionalStrategy` classes.
    2. For each statement in Module and FunctionDef bodies, with chance (30%/passes):
         - Choose a strategy, call `wrap(stmt)` to get a new AST node(s).
         - Replace the original statement with the returned wrapper.
    3. Provides `apply(tree)` to visit and fix locations.
    """
    def __init__(self, naming, strategy_classes: List[Type[JunkConditionalStrategy]], passes: int = 1):
        self.naming = naming
        self.passes = passes
        # instantiate strategies
        self.strategies = [cls() for cls in strategy_classes]

    def _inject_in_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        chance = 30 / self.passes / 100
        for stmt in body:
            if random.random() < chance:
                strat = random.choice(self.strategies)
                wrapped = strat.wrap(stmt)
                # wrap returns a list of statements
                new_body.extend(wrapped)
            else:
                new_body.append(stmt)
        return new_body

    # def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
    #     self.generic_visit(node)
    #     node.body = self._inject_in_body(node.body)
    #     return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self.generic_visit(node)
        node.body = self._inject_in_body(node.body)
        return node

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
