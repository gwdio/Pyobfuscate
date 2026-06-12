import ast
import math
import random
from typing import List, Tuple, Type

from .junk_strategies import JunkInjectionStrategy


class BogusFunctionInjector(ast.NodeTransformer):
    def __init__(self, naming, strategy_classes: List[Type[JunkInjectionStrategy]], density: int, rng: random.Random):
        self.naming = naming
        self.strategy_classes = strategy_classes
        self.density = density
        self.rng = rng

    def _build_bogus_function(self, peers: List[Tuple[str, int]]) -> ast.FunctionDef:
        func_name = self.naming.get_name('bogus')
        param_names = [self.naming.get_name('p') for _ in range(self.rng.randint(1, 3))]
        junk_vars = [self.naming.get_name('jv') for _ in range(max(2, self.rng.randint(2, 4)))]

        strategies = [cls(junk_vars) for cls in self.strategy_classes]

        body: List[ast.stmt] = []

        # Initialise junk vars — tie the first N to parameters, rest to 1
        init_ops = [ast.BitXor(), ast.Add(), ast.Sub()]
        for i, var in enumerate(junk_vars):
            if i < len(param_names):
                p = ast.Name(id=param_names[i], ctx=ast.Load())
                if self.rng.random() < 0.5:
                    init_val = p
                else:
                    op = self.rng.choice(init_ops)
                    init_val = ast.BinOp(left=p, op=op, right=ast.Constant(value=1))
            else:
                init_val = ast.Constant(value=1)
            body.append(ast.Assign(
                targets=[ast.Name(id=var, ctx=ast.Store())],
                value=init_val,
            ))

        for _ in range(self.rng.randint(3, 7)):
            body.extend(self.rng.choice(strategies).get_junk(self.rng))

        # Inject calls to previously-built peer bogus functions (~50% chance)
        if peers and self.rng.random() < 0.5:
            for _ in range(self.rng.randint(1, 2)):
                callee_name, callee_arity = self.rng.choice(peers)
                args = [
                    ast.Name(id=self.rng.choice(junk_vars), ctx=ast.Load())
                    if self.rng.random() < 0.6 else ast.Constant(value=self.rng.randint(1, 9))
                    for _ in range(callee_arity)
                ]
                call = ast.Call(
                    func=ast.Name(id=callee_name, ctx=ast.Load()),
                    args=args,
                    keywords=[],
                )
                target_var = self.rng.choice(junk_vars)
                body.append(ast.Assign(
                    targets=[ast.Name(id=target_var, ctx=ast.Store())],
                    value=call,
                ))

        # Return a computed expression derived from junk vars
        ret_ops = [ast.Add(), ast.BitXor(), ast.BitOr(), ast.Sub()]
        sample = self.rng.sample(junk_vars, k=self.rng.randint(1, min(3, len(junk_vars))))
        expr: ast.expr = ast.Name(id=sample[0], ctx=ast.Load())
        for var in sample[1:]:
            expr = ast.BinOp(left=expr, op=self.rng.choice(ret_ops), right=ast.Name(id=var, ctx=ast.Load()))
        if self.rng.random() < 0.3:
            expr = ast.Call(func=ast.Name(id='abs', ctx=ast.Load()), args=[expr], keywords=[])
        body.append(ast.Return(value=expr))

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

        built_peers: List[Tuple[str, int]] = []
        for _ in range(inject_count):
            func = self._build_bogus_function(built_peers)
            built_peers.append((func.name, len(func.args.args)))
            pos = self.rng.randint(0, len(node.body))
            node.body.insert(pos, func)

        return node

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
