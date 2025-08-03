# junk_strategies.py (add this strategy)
import ast
import random

class IdentityFuncStrategy:
    """
    Strategy interface for identity-function wrapping.
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        """
        Given an expression node, return a new expr that evaluates
        to the same value but via Python short-circuit.

        E.g. wrap(x) -> ast.BoolOp(op=And, values=[Constant(1), x])
        """
        return expr


class DefaultIdentityFuncStrategy(IdentityFuncStrategy):
    """
    Wraps expressions in `1 and <expr>`, using short-circuit identity.
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        return ast.copy_location(
            ast.BoolOp(
                op=ast.And(),
                values=[
                    ast.Constant(value=1),
                    expr
                ]
            ),
            expr
        )


class OrIdentityStrategy(IdentityFuncStrategy):
    """
    Wraps an expression as:
        expr or (expr and expr)
    which always yields expr (assuming expr isn’t falsy).
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        # Build `expr and expr`
        and_node = ast.BoolOp(op=ast.And(), values=[expr, expr])
        # Build `expr or (expr and expr)`
        or_node  = ast.BoolOp(op=ast.Or(), values=[expr, and_node])
        return ast.copy_location(or_node, expr)


class TernaryIdentityStrategy(IdentityFuncStrategy):
    """
    Uses a constant-true ternary:
        (expr if True else <dummy>)
    always yields expr.
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        # dummy can be a constant or 0
        dummy = ast.Constant(value=0)
        ternary = ast.IfExp(test=ast.Constant(value=True),
                             body=expr, orelse=dummy)
        return ast.copy_location(ternary, expr)


class LambdaIdentityStrategy(IdentityFuncStrategy):
    """
    Wraps expr in a no-op lambda:
        (lambda x: x)(expr)
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        # lambda x: x
        lam = ast.Lambda(
            args=ast.arguments(posonlyargs=[], args=[ast.arg(arg="x")],
                               kwonlyargs=[], kw_defaults=[], defaults=[]),
            body=ast.Name(id="x", ctx=ast.Load())
        )
        call = ast.Call(func=lam, args=[expr], keywords=[])
        return ast.copy_location(call, expr)


class TupleIndexIdentityStrategy(IdentityFuncStrategy):
    """
    Wraps expr in a 1-tuple and then selects index 0:
        (expr,)[0]
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        tup = ast.Tuple(elts=[expr], ctx=ast.Load())
        sub = ast.Subscript(
            value=tup,
            slice=ast.Constant(value=0),
            ctx=ast.Load()
        )
        return ast.copy_location(sub, expr)


class DictLookupIdentityStrategy(IdentityFuncStrategy):
    """
    Wraps expr in a dict { 'x': expr } and looks up 'x':
        {'x': expr}['x']
    """
    def wrap(self, expr: ast.expr) -> ast.expr:
        key = ast.Constant(value="x")
        dct = ast.Dict(keys=[key], values=[expr])
        sub = ast.Subscript(
            value=dct,
            slice=key,
            ctx=ast.Load()
        )
        return ast.copy_location(sub, expr)


class MixedIdentityStrategy(IdentityFuncStrategy):
    """
    Randomly picks one of the above strategies each time.
    """
    def __init__(self):
        self._choices = [
            OrIdentityStrategy(),
            TernaryIdentityStrategy(),
            LambdaIdentityStrategy(),
            TupleIndexIdentityStrategy(),
            DictLookupIdentityStrategy(),
        ]

    def wrap(self, expr: ast.expr) -> ast.expr:
        strat = random.choice(self._choices)
        return strat.wrap(expr)