import ast

# Import strategy modules so subclasses register via __init_subclass__
import Encryption.number_obscure_strategies as _num_strats
import Injectors.junk_strategies as _junk_strats
import Injectors.junk_conditional_strategies as _cond_strats
import Injectors.identity_strategies as _id_strats
import LoopObfuscation.obfuscation_strategies as _loop_strats

from Encryption.number_obscure_strategies import NumberObscureStrategy
from Encryption.number_obscurer import NumberObscurerInjector
from Injectors.conditional_injector import ConditionalInjector
from Injectors.identity_injector import IdentityFuncInjector
from Injectors.identity_strategies import IdentityFuncStrategy, MixedIdentityStrategy
from Injectors.inject_junk import JunkInjector
from Injectors.junk_conditional_strategies import JunkConditionalStrategy
from Injectors.junk_strategies import JunkInjectionStrategy
from LoopObfuscation.ob_for import Ob_For
from LoopObfuscation.obfuscation_strategies import LoopObfuscationStrategy
from Renaming.renamer import Renamer
from NameTracker.naming import Naming

_R = {
    "junk": JunkInjectionStrategy._registry,
    "cond": JunkConditionalStrategy._registry,
    "loop": LoopObfuscationStrategy._registry,
    "number": NumberObscureStrategy._registry,
}


def main():
    with open("IO/input.py", "r", encoding="utf-8") as f:
        code = f.read()
        tree = ast.parse(code, mode="exec")

        naming = Naming()
        naming.analyze(tree)

        tree = JunkInjector(
            naming,
            [_R["junk"]["BitwiseStrategy"], _R["junk"]["NonConstantTimeStrategy"], _R["junk"]["ArithmeticStrategy"]],
            2,
        ).apply(tree)
        tree = Ob_For(naming, _R["loop"]["CollatzStrategy"]).apply(tree)
        tree = ConditionalInjector(naming, [_R["cond"]["RandomConditionalStrategy"]], 1).apply(tree)
        tree = IdentityFuncInjector(MixedIdentityStrategy(), 0.2).apply(tree)
        tree = NumberObscurerInjector(naming, _R["number"]["FeistelNumberStrategy"]).apply(tree)
        tree = NumberObscurerInjector(naming, _R["number"]["XorStringNumberStrategy"]).apply(tree)
        tree = Renamer(naming.get_namespace()).apply(tree)
        tree = ast.fix_missing_locations(tree)

    with open("IO/output.py", "w", encoding="utf-8") as out_file:
        out_file.write(ast.unparse(tree))


if __name__ == "__main__":
    main()
