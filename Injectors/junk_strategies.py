import ast
from typing import List
import random

class JunkInjectionStrategy:
    """
    Interface for junk injection strategies.
    Strategies are constructed with the list of generated junk variable names and
    must implement get_junk() to return AST statements referencing those names.
    """
    def __init__(self, junk_vars: List[str]):
        self.junk_vars = junk_vars

    def get_junk(self) -> List[ast.stmt]:
        """
        Return a list of AST statements to inject. Use self.junk_vars as needed.
        """
        raise NotImplementedError

class TestStrategy(JunkInjectionStrategy):
    """
    A test junk strategy that always inserts a single statement assigning
    the first junk variable to zero.
    """
    def __init__(self, junk_vars: List[str]):
        super().__init__(junk_vars)
        # No extra state needed

    def get_junk(self) -> List[ast.stmt]:
        # Use the first junk var for test injection
        var = self.junk_vars[0]
        return [
            ast.Assign(
                targets=[ast.Name(id=var, ctx=ast.Store())],
                value=ast.Constant(value=0)
            )
        ]

class ArithmeticStrategy(JunkInjectionStrategy):
    """
    Inserts random arithmetic expressions combining junk vars and varied operations.
    """
    OPS = [ast.Add, ast.Sub, ast.Mult, ast.FloorDiv]

    def __init__(self, junk_vars: List[str]):
        super().__init__(junk_vars)

    def _wrap(self, node: ast.expr) -> ast.expr:
        choice = random.choice(['none', 'neg', 'double'])
        if choice == 'neg':
            return ast.UnaryOp(op=ast.USub(), operand=node)
        if choice == 'double':
            return ast.BinOp(left=node, op=ast.Mult(), right=ast.Constant(value=2))
        return node

    def get_junk(self) -> List[ast.stmt]:
        v1, v2 = random.sample(self.junk_vars, 2)
        op1 = random.choice(self.OPS)()
        op2 = random.choice(self.OPS)()
        left = self._wrap(ast.Name(id=v1, ctx=ast.Load()))
        right = self._wrap(ast.Name(id=v2, ctx=ast.Load()))
        expr = ast.BinOp(
            left=ast.BinOp(left=left, op=op1, right=right),
            op=op2,
            right=ast.Constant(value=random.randint(1, 5))
        )
        return [ast.Assign(targets=[ast.Name(id=v1, ctx=ast.Store())], value=expr)]

class LambdaStrategy(JunkInjectionStrategy):
    """
    Inserts operations with lambda functions using junk vars.
    """
    def __init__(self, junk_vars: List[str]):
        super().__init__(junk_vars)

    def get_junk(self) -> List[ast.stmt]:
        v = random.choice(self.junk_vars)
        lam = ast.Lambda(
            args=ast.arguments(posonlyargs=[], args=[ast.arg(arg='x')], kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=ast.BinOp(
                left=ast.Name(id='x', ctx=ast.Load()),
                op=random.choice([ast.Add(), ast.Sub(), ast.Mult()]),
                right=ast.Constant(value=random.randint(1, 5))
            )
        )
        call = ast.Call(func=lam, args=[ast.Name(id=v, ctx=ast.Load())], keywords=[])
        return [ast.Assign(targets=[ast.Name(id=v, ctx=ast.Store())], value=call)]

class BitwiseStrategy(JunkInjectionStrategy):
    """
    Inserts random bit-based operations on junk vars.
    """
    OPS = [ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift]

    def __init__(self, junk_vars: List[str]):
        super().__init__(junk_vars)

    def get_junk(self) -> List[ast.stmt]:
        v1, v2 = random.sample(self.junk_vars, 2)
        op = random.choice(self.OPS)()
        amount = random.randint(1, 3)
        expr = ast.BinOp(
            left=ast.Name(id=v1, ctx=ast.Load()),
            op=op,
            right=ast.Constant(value=amount)
        )
        return [ast.Assign(targets=[ast.Name(id=v1, ctx=ast.Store())], value=expr)]

class NonConstantTimeStrategy(JunkInjectionStrategy):
    """
    Inserts a small loop for non-constant-time operations.
    """
    def __init__(self, junk_vars: List[str]):
        super().__init__(junk_vars)

    def get_junk(self) -> List[ast.stmt]:
        v1, v2 = random.sample(self.junk_vars, 2)
        loop_var = self.junk_vars[0] + '_cnt'
        loop = ast.For(
            target=ast.Name(id=loop_var, ctx=ast.Store()),
            iter=ast.Call(func=ast.Name(id='range', ctx=ast.Load()), args=[ast.Constant(value=random.randint(3, 6))], keywords=[]),
            body=[ast.AugAssign(target=ast.Name(id=v2, ctx=ast.Store()), op=random.choice([ast.Add()]), value=ast.Constant(value=1))],
            orelse=[]
        )
        return [loop]