import ast
import random
from typing import List

class JunkConditionalStrategy:
    """
    Interface for junk conditional strategies.
    Must implement wrap(stmt: ast.stmt) -> List[ast.stmt].
    """
    def wrap(self, stmt: ast.stmt) -> List[ast.stmt]:
        raise NotImplementedError

class ConstantTrueStrategy(JunkConditionalStrategy):
    """
    Wraps a statement in `if True: ...`.
    """
    def wrap(self, stmt: ast.stmt) -> List[ast.stmt]:
        return [
            ast.If(
                test=ast.Constant(value=True),
                body=[stmt],
                orelse=[]
            )
        ]

class ConstantFalseStrategy(JunkConditionalStrategy):
    """
    Wraps a statement in `if False: <garbage> else: <stmt>`.
    Uses a dummy garbage pass.
    """
    def wrap(self, stmt: ast.stmt) -> List[ast.stmt]:
        garbage = ast.Pass()
        return [
            ast.If(
                test=ast.Constant(value=False),
                body=[garbage],
                orelse=[stmt]
            )
        ]


class RandomConditionalStrategy(JunkConditionalStrategy):
    """
    Wraps a statement in a random but semantically constant conditional.
    Generates either a complex truthy or falsy expression randomly.
    """

    def wrap(self, stmt: ast.stmt) -> List[ast.stmt]:
        truth = random.random() < 0.5
        test = self._make_test(truth)
        if truth:
            return [ast.If(test=test, body=[stmt], orelse=[])]
        else:
            return [ast.If(test=test, body=[ast.Pass()], orelse=[stmt])]

    def _make_test(self, truth: bool) -> ast.expr:
        # Always-truthy patterns
        nested_list = ast.List(
            elts=[ast.List(elts=[ast.Constant(1)], ctx=ast.Load()),
                  ast.List(elts=[], ctx=ast.Load())],
            ctx=ast.Load()
        )
        bit_xor = ast.BinOp(
            left=ast.Constant(12),
            op=ast.BitXor(),
            right=ast.Constant(4)
        )  # 12 ^ 4 == 8 → truthy
        compare_simple = ast.Compare(
            left=ast.Constant(3),
            ops=[ast.GtE()],
            comparators=[ast.Constant(2)]
        )  # 3 >= 2 → True
        bool_chain = ast.BoolOp(
            op=ast.And(),
            values=[nested_list, bit_xor]
        )  # nested_list and bit_xor → 8 → truthy
        unary_not = ast.UnaryOp(
            op=ast.Not(),
            operand=ast.Constant(value=not truth)
        )  # not (not truth) → truth

        if truth:
            options = [nested_list, bit_xor, compare_simple, bool_chain, unary_not]
        else:
            # Only produce definitely-falsy tests:
            const_false = ast.Constant(False)
            compare_false = ast.Compare(
                left=ast.Constant(1),
                ops=[ast.Lt()],
                comparators=[ast.Constant(0)]
            )  # 1 < 0 → False
            # not (not False) → not True → False
            unary_false = ast.UnaryOp(
                op=ast.Not(),
                operand=ast.Constant(value=not False)
            )
            options = [const_false, compare_false, unary_false]

        return random.choice(options)