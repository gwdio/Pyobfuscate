import ast
import random
from typing import Optional, Union, List

from NameTracker.naming import Naming


class StringObscureStrategy:
    _registry: dict = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        StringObscureStrategy._registry[cls.__name__] = cls

    def __init__(self, naming: Naming, rng: random.Random):
        self.naming = naming
        self.rng = rng

    def obfuscate(self, value: str) -> ast.expr:
        raise NotImplementedError

    def get_decoder(self) -> Optional[Union[ast.FunctionDef, List[ast.FunctionDef]]]:
        return None


class CharArrayStrategy(StringObscureStrategy):

    def obfuscate(self, value: str) -> ast.expr:
        if not value:
            return ast.Constant(value=value)

        chr_calls = [
            ast.Call(
                func=ast.Name(id="chr", ctx=ast.Load()),
                args=[ast.Constant(value=ord(ch))],
                keywords=[],
            )
            for ch in value
        ]

        result = chr_calls[0]
        for call in chr_calls[1:]:
            result = ast.BinOp(left=result, op=ast.Add(), right=call)
        return result


class XorStringStrategy(StringObscureStrategy):

    def __init__(self, naming: Naming, rng: random.Random):
        super().__init__(naming, rng)
        self.decoder_name = naming.get_name("_xdec")
        self._used = False

    def obfuscate(self, value: str) -> ast.expr:
        if not value:
            return ast.Constant(value=value)

        self._used = True
        data = value.encode("utf-8")
        key = bytes(self.rng.getrandbits(8) for _ in range(len(data)))
        encoded = bytes(b ^ k for b, k in zip(data, key))

        return ast.Call(
            func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
            args=[ast.Constant(value=encoded), ast.Constant(value=key)],
            keywords=[],
        )

    def get_decoder(self) -> Optional[ast.FunctionDef]:
        if not self._used:
            return None
        src = (
            f"def {self.decoder_name}(enc, key):\n"
            f"    return bytes(b ^ k for b, k in zip(enc, key)).decode('utf-8')\n"
        )
        return ast.parse(src).body[0]
