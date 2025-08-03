import ast
from typing import List, Optional, Tuple


class ForToWhileGeneric(ast.NodeTransformer):
    def __init__(self, naming, strategy_class):
        """
        naming: your Naming instance for unique name generation
        strategy_class: a class inheriting from LoopObfuscationStrategy
        """
        self.naming = naming
        self.strategy_class = strategy_class
        # Keep track of strategy instances to inject helpers later
        self._strategies: List = []

    def visit_For(self, node: ast.For):
        self.generic_visit(node)

        parsed = parse_constant_range_args(node.iter)
        if parsed is None:
            return node
        start, stop, step = parsed

        # Instantiate the obfuscation strategy for this loop
        strategy = self.strategy_class(self.naming, start, stop, step)
        self._strategies.append(strategy)

        # Rename original loop variable to strategy.loop_var throughout the body
        original = node.target.id if isinstance(node.target, ast.Name) else None
        new_name = strategy.loop_var

        if original:
            class VarRenamer(ast.NodeTransformer):
                def __init__(self, orig, new):
                    self.orig = orig
                    self.new = new
                def visit_Name(self, nm: ast.Name):
                    if nm.id == self.orig and isinstance(nm.ctx, (ast.Load, ast.Store)):
                        return ast.copy_location(ast.Name(id=self.new, ctx=nm.ctx), nm)
                    return nm
            renamer = VarRenamer(original, new_name)
            body_block = [renamer.visit(stmt) for stmt in node.body]
        else:
            body_block = node.body

        # Build the while loop
        while_node = ast.While(
            test=strategy.get_condition(),
            body=strategy.get_loop_index_setup() + body_block + strategy.get_advance(),
            orelse=node.orelse
        )

        return strategy.get_initial() + [while_node]

    def inject_functions(self, tree: ast.Module) -> ast.Module:
        """
        Inject any helper functions required by strategies at module level.
        """
        for strategy in self._strategies:
            inject = getattr(strategy, "inject_functions", None)
            if callable(inject):
                tree = inject(tree)
        return tree




def parse_constant_range_args(call: ast.Call) -> Optional[Tuple[int, int, int]]:
    """
    Parse an AST Call node representing a range() call with literal integer arguments,
    including negatives, and return a tuple (start, stop, step). Returns None otherwise.

    Supports:
      - range(stop)
      - range(start, stop)
      - range(start, stop, step)
    """
    # Only handle for loops over range() with literal integer args (including negatives)
    def is_int_literal(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return True
        if (
            isinstance(n, ast.UnaryOp)
            and isinstance(n.op, ast.USub)
            and isinstance(n.operand, ast.Constant)
            and isinstance(n.operand.value, int)
        ):
            return True
        return False

    if not (
        isinstance(call, ast.Call)
        and isinstance(call.func, ast.Name)
        and call.func.id == 'range'
        and 1 <= len(call.args) <= 3
        and all(is_int_literal(arg) for arg in call.args)
    ):
        return None

    # Extract integer values manually
    def eval_int(expr):
        if isinstance(expr, ast.Constant):
            return expr.value
        # Unary minus
        return -expr.operand.value

    values = [eval_int(arg) for arg in call.args]

    if len(values) == 1:
        return (0, values[0], 1)
    elif len(values) == 2:
        return (values[0], values[1], 1)
    else:
        return (values[0], values[1], values[2])
