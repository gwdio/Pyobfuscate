import ast
from math import ceil
from typing import List, Optional
from .for_to_while_generic import parse_constant_range_args

class ComplexLoopUnwrapper(ast.NodeTransformer):
    """
    Normalize any for-range loops with start/stop/step into a simple 0-based for-loop.

    Transforms:
        for VAR in range(start, stop, step):
            BODY
    Into:
        for __idx in range(count):
            VAR = start + __idx * step
            BODY

    Uses the shared Naming instance to generate unique index names.
    """
    def __init__(self, naming):
        self.naming = naming

    def visit_For(self, node: ast.For) -> ast.AST:
        self.generic_visit(node)

        # Parse literal range args (supports negative step)
        parsed = parse_constant_range_args(node.iter)
        if parsed is None:
            return node
        start, stop, step = parsed
        if step == 0:
            return node

        # Compute iteration count
        count = max(0, ceil((stop - start) / step))

        # Generate unique index variable
        idx_var = self.naming.get_name('__idx')
        orig_var = node.target.id if isinstance(node.target, ast.Name) else None

        # Build new for loop: for __idx in range(count):
        new_for = ast.For(
            target=ast.Name(id=idx_var, ctx=ast.Store()),
            iter=ast.Call(
                func=ast.Name(id='range', ctx=ast.Load()),
                args=[ast.Constant(value=count)],
                keywords=[]
            ),
            body=[],
            orelse=node.orelse
        )

        # Build loop body: assign original var then original body
        new_body: List[ast.stmt] = []
        if orig_var:
            compute_orig = ast.Assign(
                targets=[ast.Name(id=orig_var, ctx=ast.Store())],
                value=ast.BinOp(
                    left=ast.Constant(value=start),
                    op=ast.Add(),
                    right=ast.BinOp(
                        left=ast.Name(id=idx_var, ctx=ast.Load()),
                        op=ast.Mult(),
                        right=ast.Constant(value=step)
                    )
                )
            )
            new_body.append(compute_orig)
        new_body.extend(node.body)
        new_for.body = new_body

        return new_for
