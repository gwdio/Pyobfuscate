import ast
from typing import List
import random

class LoopObfuscationStrategy:
    """
    Abstract base for obfuscation strategies for ForToWhileGeneric.
    Provides default loop_var generation and hooks for AST snippet generation and helper injection.
    """
    def __init__(self, naming, start: int, stop: int, step: int):
        self.naming = naming
        self.start = start
        self.stop = stop
        self.step = step
        # Every strategy gets its own unique loop variable name
        self.loop_var = naming.get_name('i')

    def get_initial(self) -> List[ast.stmt]:
        raise NotImplementedError

    def get_condition(self) -> ast.expr:
        raise NotImplementedError

    def get_advance(self) -> List[ast.stmt]:
        raise NotImplementedError

    def get_loop_index_setup(self) -> List[ast.stmt]:
        return []  # Optional, empty by default

    def inject_functions(self, tree: ast.Module) -> ast.Module:
        """
        Hook to inject any module-level helper functions or imports.
        """
        return tree


class PlainStrategy(LoopObfuscationStrategy):
    """
    Implements a clean, non-obfuscated for->while strategy.
    """
    def __init__(self, naming, start: int, stop: int, step: int):
        super().__init__(naming, start, stop, step)
        # loop_var provided by base class

    def get_initial(self) -> List[ast.stmt]:
        return [
            ast.Assign(
                targets=[ast.Name(id=self.loop_var, ctx=ast.Store())],
                value=ast.Constant(value=self.start)
            )
        ]

    def get_condition(self) -> ast.expr:
        return ast.Compare(
            left=ast.Name(id=self.loop_var, ctx=ast.Load()),
            ops=[ast.Lt() if self.step > 0 else ast.Gt()],
            comparators=[ast.Constant(value=self.stop)]
        )

    def get_advance(self) -> List[ast.stmt]:
        return [
            ast.AugAssign(
                target=ast.Name(id=self.loop_var, ctx=ast.Store()),
                op=ast.Add() if self.step > 0 else ast.Sub(),
                value=ast.Constant(value=abs(self.step))
            )
        ]

    def get_loop_index_setup(self) -> List[ast.stmt]:
        return []  # Plain mode doesn’t need any index setup

    def inject_functions(self, tree: ast.Module) -> ast.Module:
        # No helpers needed here
        return tree



# -- Collatz Strategy --
class CollatzStrategy(LoopObfuscationStrategy):
    """
    Implements Collatz-based loop obfuscation: transforms for->while with Collatz index resolution.
    """
    def __init__(self, naming, start: int, stop: int, step: int):
        super().__init__(naming, start, stop, step)
        # Unique variables for this loop (loop_var provided by base)
        self.a_var = naming.get_name('a')
        self.b_var = naming.get_name('b')
        self.num_var = naming.get_name('num')
        # Collatz parameters
        self.a = random.choice([3, 5])
        b_choices = [x for x in [-1, 1, 3, 5, 7, 11] if x != self.a]
        self.b = random.choice(b_choices)
        self.seed = random.randint(19, 97)
        # Calculate number of iterations
        self.n = max(0, (self.stop - self.start + (self.step - 1 if self.step > 0 else -(self.step + 1))) // abs(self.step))
        # Compute target state via forward Collatz
        self.target = self._collatz_forward(self.a, self.b, self.seed, self.n)
        # Prepare helper function name
        self.resolve_name = naming.get_name('resolve_collatz')

    def _collatz_forward(self, a: int, b: int, seed: int, n: int) -> int:
        for _ in range(n):
            if ((seed - b) % a == 0
               and ((seed - b) // a) % 2 == 1
               and random.random() > 0.95
               and seed not in {2,4,8,16,32,40,1312}):
                seed = (seed - b) // a
            else:
                seed = 2 * seed
        return seed

    def get_initial(self) -> List[ast.stmt]:
        return [
            ast.Assign(targets=[ast.Name(id=self.a_var, ctx=ast.Store())], value=ast.Constant(value=self.a)),
            ast.Assign(targets=[ast.Name(id=self.b_var, ctx=ast.Store())], value=ast.Constant(value=self.b)),
            ast.Assign(targets=[ast.Name(id=self.num_var, ctx=ast.Store())], value=ast.Constant(value=self.target))
        ]

    def get_condition(self) -> ast.expr:
        return ast.Compare(
            left=ast.Name(id=self.num_var, ctx=ast.Load()),
            ops=[ast.NotEq()],
            comparators=[ast.Constant(value=self.seed)]
        )

    def get_loop_index_setup(self) -> List[ast.stmt]:
        return [
            ast.Assign(
                targets=[ast.Name(id=self.loop_var, ctx=ast.Store())],
                value=ast.Call(
                    func=ast.Name(id=self.resolve_name, ctx=ast.Load()),
                    args=[
                        ast.Name(id=self.a_var, ctx=ast.Load()),
                        ast.Name(id=self.b_var, ctx=ast.Load()),
                        ast.Name(id=self.num_var, ctx=ast.Load()),
                        ast.Constant(value=self.target)
                    ],
                    keywords=[]
                )
            )
        ]

    def get_advance(self) -> List[ast.stmt]:
        return [
            ast.If(
                test=ast.Compare(
                    left=ast.BinOp(left=ast.Name(id=self.num_var, ctx=ast.Load()), op=ast.Mod(), right=ast.Constant(value=2)),
                    ops=[ast.Eq()],
                    comparators=[ast.Constant(value=0)]
                ),
                body=[
                    ast.Assign(
                        targets=[ast.Name(id=self.num_var, ctx=ast.Store())],
                        value=ast.BinOp(left=ast.Name(id=self.num_var, ctx=ast.Load()), op=ast.FloorDiv(), right=ast.Constant(value=2))
                    )
                ],
                orelse=[
                    ast.Assign(
                        targets=[ast.Name(id=self.num_var, ctx=ast.Store())],
                        value=ast.BinOp(
                            left=ast.BinOp(left=ast.Name(id=self.a_var, ctx=ast.Load()), op=ast.Mult(), right=ast.Name(id=self.num_var, ctx=ast.Load())),
                            op=ast.Add(),
                            right=ast.Name(id=self.b_var, ctx=ast.Load())
                        )
                    )
                ]
            )
        ]

    def inject_functions(self, tree: ast.Module) -> ast.Module:
        # Inject the resolve_collatz helper at module top
        func_def = ast.FunctionDef(
            name=self.resolve_name,
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg='a'), ast.arg(arg='b'), ast.arg(arg='target'), ast.arg(arg='num')],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=[
                ast.Assign(targets=[ast.Name(id='counter', ctx=ast.Store())], value=ast.Constant(value=0)),
                ast.While(
                    test=ast.Compare(
                        left=ast.Name(id='num', ctx=ast.Load()),
                        ops=[ast.NotEq()],
                        comparators=[ast.Name(id='target', ctx=ast.Load())]
                    ),
                    body=[
                        ast.If(
                            test=ast.Compare(
                                left=ast.BinOp(left=ast.Name(id='num', ctx=ast.Load()), op=ast.Mod(), right=ast.Constant(value=2)),
                                ops=[ast.Eq()],
                                comparators=[ast.Constant(value=0)]
                            ),
                            body=[
                                ast.Assign(
                                    targets=[ast.Name(id='num', ctx=ast.Store())],
                                    value=ast.BinOp(left=ast.Name(id='num', ctx=ast.Load()), op=ast.FloorDiv(), right=ast.Constant(value=2))
                                )
                            ],
                            orelse=[
                                ast.Assign(
                                    targets=[ast.Name(id='num', ctx=ast.Store())],
                                    value=ast.BinOp(
                                        left=ast.BinOp(left=ast.Name(id='a', ctx=ast.Load()), op=ast.Mult(), right=ast.Name(id='num', ctx=ast.Load())),
                                        op=ast.Add(),
                                        right=ast.Name(id='b', ctx=ast.Load())
                                    )
                                )
                            ]
                        ),
                        ast.AugAssign(target=ast.Name(id='counter', ctx=ast.Store()), op=ast.Add(), value=ast.Constant(value=1))
                    ],
                    orelse=[]
                ),
                ast.Return(value=ast.Name(id='counter', ctx=ast.Load()))
            ],
            decorator_list=[]
        )
        tree.body.insert(0, func_def)
        return tree
