import ast
import math
import random
from typing import List, Type

from .junk_strategies import JunkInjectionStrategy


class BogusFunctionInjector(ast.NodeTransformer):
    def __init__(self, naming, strategy_classes: List[Type[JunkInjectionStrategy]], density: int, rng: random.Random):
        self.naming = naming
        self.strategy_classes = strategy_classes
        self.density = density
        self.rng = rng

    def _build_bogus_function(self) -> ast.FunctionDef:
        func_name = self.naming.get_name('bogus')
        param_names = [self.naming.get_name('p') for _ in range(self.rng.randint(1, 3))]
        junk_vars = [self.naming.get_name('jv') for _ in range(max(2, self.rng.randint(2, 4)))]

        strategies = [cls(junk_vars) for cls in self.strategy_classes]

        body: List[ast.stmt] = []
        for var in junk_vars:
            body.append(ast.Assign(
                targets=[ast.Name(id=var, ctx=ast.Store())],
                value=ast.Constant(value=1),
            ))

        for _ in range(self.rng.randint(3, 7)):
            body.extend(self.rng.choice(strategies).get_junk(self.rng))

        body.append(ast.Return(value=ast.Constant(value=None)))

        return ast.FunctionDef(
            name=func_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg=name) for name in param_names],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[],
            ),
            body=body,
            decorator_list=[],
            returns=None,
        )

    def visit_Module(self, node: ast.Module) -> ast.AST:
        real_count = sum(1 for n in node.body if isinstance(n, ast.FunctionDef))
        inject_count = max(1, math.ceil(real_count * self.density))

        for _ in range(inject_count):
            pos = self.rng.randint(0, len(node.body))
            node.body.insert(pos, self._build_bogus_function())

        return node

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
