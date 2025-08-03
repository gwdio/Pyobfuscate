import ast
import random
from typing import List, Type
from .junk_strategies import JunkInjectionStrategy

class JunkInjector(ast.NodeTransformer):
    """
    Framework for injecting junk snippets into the AST.

    Process:
    1. Generate 3–5 junk variable names via Naming.
    2. Collect valid insertion points (Module body and FunctionDef bodies).
    3. For each insertion point, with per-pass chance, call each strategy:
         junk = strat.get_junk()
         inject junk AST nodes.
    4. After all injections, declare the generated junk vars at top of module.
    """
    def __init__(self, naming, strategy_classes: List[Type[JunkInjectionStrategy]], passes: int = 1):
        self.naming = naming
        self.passes = passes
        # generate 3–5 junk variable names upfront
        num_vars = random.randint(3, 5)
        self.junk_vars = [naming.get_name('junk') for _ in range(num_vars)]
        # instantiate strategies, passing junk_vars into each
        self.strategies = [cls(self.junk_vars) for cls in strategy_classes]

    def _inject_in_body(self, body: List[ast.stmt]) -> List[ast.stmt]:
        new_body: List[ast.stmt] = []
        chance = 30 / self.passes / 100  # default 30% per pass
        for stmt in body:
            # before stmt
            for strat in self.strategies:
                if random.random() < chance:
                    junk = strat.get_junk()
                    new_body.extend(junk)
            new_body.append(stmt)
            # after stmt
            for strat in self.strategies:
                if random.random() < chance:
                    junk = strat.get_junk()
                    new_body.extend(junk)
        return new_body

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        self.generic_visit(node)
        node.body = self._inject_in_body(node.body)
        return node

    def visit_Module(self, node: ast.Module) -> ast.AST:
        self.generic_visit(node)
        # inject junk within module-level statements
        node.body = self._inject_in_body(node.body)
        # finally, declare junk vars at top
        decls = []
        for var in self.junk_vars:
            decls.append(
                ast.Assign(
                    targets=[ast.Name(id=var, ctx=ast.Store())],
                    value=ast.Constant(value=1)
                )
            )
        node.body = decls + node.body
        return node

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
