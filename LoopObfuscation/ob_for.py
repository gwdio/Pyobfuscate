import ast
from .for_to_while_generic import ForToWhileGeneric
from .loop_simplifier import ComplexLoopUnwrapper
from .obfuscation_strategies import PlainStrategy, CollatzStrategy


class Ob_For:
    def __init__(self, naming, strategy_class):
        """
        naming: your Naming instance
        strategy_class: the strategy class to use (e.g., PlainStrategy, CollatzStrategy)
        """
        self.naming = naming
        self.passes = []

        # Create your transformation units with naming context
        self.loop_unwrapper = LoopUnwrapper(naming)
        self.iterable_conversion = ForToWhileGeneric(naming, strategy_class)

        # Append in order: transform first, then inject (if applicable)
        self.passes.append(self.loop_unwrapper)
        if strategy_class is CollatzStrategy:
            self.complex_loop_unwrapper = ComplexLoopUnwrapper(naming)
            self.passes.append(self.complex_loop_unwrapper)
        self.passes.append(self.iterable_conversion)

    def apply(self, tree):
        for unit in self.passes:
            # Apply transformation
            tree = unit.visit(tree)

            # Then inject helper functions if the unit supports it
            func = getattr(unit, "inject_functions", None)
            if callable(func):
                tree = func(tree)

        return ast.fix_missing_locations(tree)


class LoopUnwrapper(ast.NodeTransformer):
    def __init__(self, naming):
        self.func_counter = 0
        self.new_funcs = []
        self.naming = naming

    def visit_For(self, node):
        self.generic_visit(node)

        new_body = []
        for stmt in node.body:
            if isinstance(stmt, ast.For):
                func_name = self.naming.get_name("__unwrapped_loop")

                args = [node.target.id] if isinstance(node.target, ast.Name) else []

                func_def = ast.FunctionDef(
                    name=func_name,
                    args=ast.arguments(
                        posonlyargs=[],
                        args=[ast.arg(arg=a) for a in args],
                        kwonlyargs=[],
                        kw_defaults=[],
                        defaults=[]
                    ),
                    body=[stmt],
                    decorator_list=[]
                )

                self.new_funcs.append(func_def)

                call = ast.Expr(
                    value=ast.Call(
                        func=ast.Name(id=func_name, ctx=ast.Load()),
                        args=[ast.Name(id=a, ctx=ast.Load()) for a in args],
                        keywords=[]
                    )
                )
                new_body.append(call)
            else:
                new_body.append(stmt)

        node.body = new_body
        return node

    def inject_functions(self, tree):
        tree.body = self.new_funcs + tree.body
        return tree

