from Encrpytion.number_obscure_strategies import *
from Encrpytion.number_obscurer import NumberObscurerInjector
from Injectors.conditional_injector import ConditionalInjector
from Injectors.identity_injector import IdentityFuncInjector
from Injectors.identity_strategies import MixedIdentityStrategy
from Injectors.inject_junk import JunkInjector
from Injectors.junk_conditional_strategies import RandomConditionalStrategy
from Injectors.junk_strategies import *
from LoopObfuscation.ob_for import Ob_For
from LoopObfuscation.obfuscation_strategies import *
from Renaming.renamer import Renamer

def main():
    with open('IO/input.py', 'r', encoding='utf-8') as f:
        code = f.read()
        tree = ast.parse(code, mode='exec')

        naming = Naming()
        naming.analyze(tree)


        tree = JunkInjector(naming, [BitwiseStrategy, NonConstantTimeStrategy, ArithmeticStrategy], 2).apply(tree)
        tree = Ob_For(naming, CollatzStrategy).apply(tree)
        tree = ConditionalInjector(naming, [RandomConditionalStrategy], 1).apply(tree)
        tree = IdentityFuncInjector(MixedIdentityStrategy(), 0.2).apply(tree)
        tree = NumberObscurerInjector(naming, FeistelNumberStrategy).apply(tree)
        tree = NumberObscurerInjector(naming, XorStringNumberStrategy).apply(tree)
        tree = Renamer(naming.get_namespace()).apply(tree)
        tree = ast.fix_missing_locations(tree)
    # Write to output.py
    with open('IO/output.py', 'w', encoding='utf-8') as out_file:
        out_file.write(ast.unparse(tree))

if __name__ == "__main__":
    main()
