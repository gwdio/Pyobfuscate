import ast
import random

from NameTracker.naming import Naming


class ImportObfuscator(ast.NodeTransformer):
    def __init__(self, naming: Naming, rng: random.Random):
        self.naming = naming
        self.rng = rng

    def _make_import_call(self, name: str, fromlist: list | None = None) -> ast.Call:
        keywords = []
        if fromlist:
            keywords = [ast.keyword(
                arg='fromlist',
                value=ast.List(elts=[ast.Constant(value=s) for s in fromlist], ctx=ast.Load()),
            )]
        return ast.Call(
            func=ast.Name(id='__import__', ctx=ast.Load()),
            args=[ast.Constant(value=name)],
            keywords=keywords,
        )

    def visit_Import(self, node: ast.Import) -> list:
        stmts = []
        for alias in node.names:
            if alias.asname:
                target = alias.asname
                # Non-empty fromlist returns the submodule (needed for dotted names)
                fromlist = [''] if '.' in alias.name else None
                call = self._make_import_call(alias.name, fromlist)
            else:
                # __import__('foo.bar') returns top-level 'foo' — correct binding
                target = alias.name.split('.')[0]
                call = self._make_import_call(alias.name)
            stmts.append(ast.copy_location(
                ast.Assign(
                    targets=[ast.Name(id=target, ctx=ast.Store())],
                    value=call,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                ),
                node,
            ))
        return stmts

    def visit_ImportFrom(self, node: ast.ImportFrom) -> list | ast.AST:
        if node.level > 0:  # relative imports — leave unchanged
            return node
        if any(a.name == '*' for a in node.names):  # star imports — leave unchanged
            return node

        module = node.module or ''
        stmts = []

        if len(node.names) == 1:
            alias = node.names[0]
            target = alias.asname if alias.asname else alias.name
            call = self._make_import_call(module, fromlist=[alias.name])
            value = ast.Attribute(value=call, attr=alias.name, ctx=ast.Load())
            stmts.append(ast.copy_location(
                ast.Assign(
                    targets=[ast.Name(id=target, ctx=ast.Store())],
                    value=value,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                ),
                node,
            ))
        else:
            # Multiple names: one __import__ call stored in a temp var
            tmp = self.naming.get_name('_imp')
            all_names = [a.name for a in node.names]
            call = self._make_import_call(module, fromlist=all_names)
            stmts.append(ast.copy_location(
                ast.Assign(
                    targets=[ast.Name(id=tmp, ctx=ast.Store())],
                    value=call,
                    lineno=node.lineno,
                    col_offset=node.col_offset,
                ),
                node,
            ))
            for alias in node.names:
                target = alias.asname if alias.asname else alias.name
                value = ast.Attribute(
                    value=ast.Name(id=tmp, ctx=ast.Load()),
                    attr=alias.name,
                    ctx=ast.Load(),
                )
                stmts.append(ast.copy_location(
                    ast.Assign(
                        targets=[ast.Name(id=target, ctx=ast.Store())],
                        value=value,
                        lineno=node.lineno,
                        col_offset=node.col_offset,
                    ),
                    node,
                ))

        return stmts

    def apply(self, tree: ast.AST) -> ast.AST:
        new_tree = self.visit(tree)
        return ast.fix_missing_locations(new_tree)
