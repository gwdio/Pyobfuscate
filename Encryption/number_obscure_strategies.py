import ast
import random
from typing import Optional, Union, List
from NameTracker.naming import Naming  # or wherever your Naming lives


class NumberObscureStrategy:
    """
    Base interface for number‐obscuring strategies.
    Subclasses must implement `obscure(value)` and may override `get_decoder()`.
    """

    def __init__(self, naming: Naming):
        self.naming = naming

    def obfuscate(self, value: int) -> ast.expr:
        """
        Given an integer literal `value`, return an ast.expr
        that evaluates to the same integer in an obfuscated form.
        """
        raise NotImplementedError

    def get_decoder(self) -> Optional[Union[ast.FunctionDef, List[ast.FunctionDef]]]:
        """
        Return the AST node(s) for any helper/decoder functions that must be
        injected at module top, or None if no decoder is needed.
        """
        return None


class TemplateNumberStrategy(NumberObscureStrategy):
    """
    TEMPLATE: Clones the literal directly (no-op).
    Use this as a starting point for your own strategies.
    """

    def __init__(self, naming: Naming):
        super().__init__(naming)
        # If you need a decoder helper, generate its name here:
        # self.decoder_name = naming.get_name("decode_num")

    def obfuscate(self, value: int) -> ast.expr:
        # Simple pass‐through:
        return ast.Constant(value=value)

    def get_decoder(self) -> Optional[Union[ast.FunctionDef, List[ast.FunctionDef]]]:
        return None



class SimpleFeistelNumberStrategy(NumberObscureStrategy):
    """
    Simple 4-round Feistel using the same bijective round function and a preset key.
    """
    MASK32 = 0xFFFFFFFF

    def __init__(self, naming: Naming):
        super().__init__(naming)
        self.rounds = 4
        # Preset 16-bit key
        self.key16 = 0b1011001011001011  # example fixed key
        self.decoder_name = naming.get_name("decode_num")

    def obfuscate(self, value: int) -> ast.expr:
        # only handle 32-bit ints
        if not (0 <= value < (1 << 32)):
            return ast.Constant(value=value)

        # 1) unpack into halves
        L = value >> 16
        R = value & 0xffff

        # 2) Feistel rounds with bijective function F(x) = rotate3(x ^ key)
        mask16 = 0xFFFF
        for _ in range(self.rounds):
            x = R ^ self.key16
            # left rotate by 3
            F = ((x << 3) | (x >> (16 - 3))) & mask16
            L, R = R, (L ^ F) & mask16

        # 3) re-interleave into 32 bits
        encoded = L << 16 | R

        # 4) wrap in decoder call
        return ast.Call(
            func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
            args=[ast.Constant(value=encoded)],
            keywords=[]
        )

    def get_decoder(self) -> Optional[Union[ast.FunctionDef, List[ast.FunctionDef]]]:
        # Decoder must undo the Feistel rounds in reverse order
        src = f'''

def {self.decoder_name}(x):
    # 1) unpack
    L = x >> 16
    R = x & 0xffff

    # 2) inverse Feistel: reverse round order
    mask16 = 0xFFFF
    for _ in range({self.rounds}):
        # compute F using the same key and rotation on L
        tmp = L ^ {hex(self.key16)}
        F = ((tmp << 3) | (tmp >> (16 - 3))) & mask16
        # undo: previous L = R ^ F(L)
        prevL = R ^ F
        # previous R = L
        prevR = L
        L, R = prevL, prevR

    # 3) pack back to original
    v = (L << 16) | R
    return v & {hex(self.MASK32)}
'''
        module = ast.parse(src)
        return module.body[0]



class FeistelNumberStrategy(NumberObscureStrategy):
    MASK32 = 0xFFFFFFFF

    def __init__(self, naming: Naming, rounds: int = 3):
        super().__init__(naming)
        self.rounds = rounds
        # 16-bit random odd multiplier (bijective mod 2^16)
        self.salt_mul = random.getrandbits(16) | 1
        # 16-bit random XOR salt
        self.salt_xor = random.getrandbits(16) & 0xFFFF
        # modular inverse of salt_mul mod 2^16
        self.salt_mul_inv = pow(self.salt_mul, -1, 1 << 16)
        self.decoder_name = naming.get_name("decode_num")

    def obfuscate(self, value: int) -> ast.expr:
        if not (0 <= value < (1 << 32)):
            return ast.Constant(value=value)
        # unpack even/odd bits
        L = 0
        R = 0
        for i in range(16):
            L |= ((value >> (2 * i)) & 1) << i
            R |= ((value >> (2 * i + 1)) & 1) << i
        mask16 = 0xFFFF
        for _ in range(self.rounds):
            # multiply and then XOR salt_xor
            y = (R * self.salt_mul) & mask16
            z = y ^ self.salt_xor
            # rotate
            F = ((z << 3) | (z >> (16 - 3))) & mask16
            L, R = R, (L ^ F) & mask16
        # re-interleave
        encoded = 0
        for i in range(16):
            encoded |= ((L >> i) & 1) << (2 * i)
            encoded |= ((R >> i) & 1) << (2 * i + 1)
        encoded &= self.MASK32
        return ast.Call(
            func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
            args=[ast.Constant(value=encoded)],
            keywords=[]
        )

    def get_decoder(self) -> Optional[Union[ast.FunctionDef, List[ast.FunctionDef]]]:
        src = f'''

def {self.decoder_name}(x):
    # unpack even/odd bits (inverse of re-interleave)
    L = 0
    R = 0
    for i in range(16):
        L |= ((x >> (2 * i)) & 1) << i
        R |= ((x >> (2 * i + 1)) & 1) << i
    # reverse the rounds
    for _ in range({self.rounds}):
        # Note: reverse order of swap: we now treat R as new left
        F_input = L
        y = (F_input * {self.salt_mul}) & {0xffff}
        z = y ^ {self.salt_xor}
        F = ((z << 3) | (z >> (16 - 3))) & {0xffff}

        # undo XOR and swap
        L, R = (R ^ F) & {0xffff}, F_input

    # re-interleave into original number
    original = 0
    for i in range(16):
        original |= ((L >> i) & 1) << (2 * i)
        original |= ((R >> i) & 1) << (2 * i + 1)

    return original & 0xffffffff
'''
        module = ast.parse(src)
        return module.body[0]


class XorStringNumberStrategy(NumberObscureStrategy):
    """
    Obfuscates an n-digit number by XORing each digit character with a random key string of equal length.
    The encoded format is <xor_result><key>, where key is appended so the decoder can extract it.
    """
    def __init__(self, naming: Naming):
        super().__init__(naming)
        self.decoder_name = naming.get_name("decode_num")

    def obfuscate(self, value: int) -> ast.expr:
        s = str(value)
        n = len(s)
        # generate random key string of same length
        key_chars = [chr(random.getrandbits(8)) for _ in range(n)]
        key = ''.join(key_chars)
        # xor each char
        xor_chars = [chr(ord(s[i]) ^ ord(key_chars[i])) for i in range(n)]
        xor_str = ''.join(xor_chars)
        encoded = xor_str + key
        return ast.Call(
            func=ast.Name(id=self.decoder_name, ctx=ast.Load()),
            args=[ast.Constant(value=encoded)],
            keywords=[]
        )

    def get_decoder(self) -> Optional[ast.FunctionDef]:
        src = f'''

def {self.decoder_name}(encoded):
    # split into xor_str and key
    n = len(encoded) // 2
    xor_str = encoded[:n]
    key = encoded[n:]
    # reconstruct original digits
    chars = [chr(ord(xor_str[i]) ^ ord(key[i])) for i in range(n)]
    return int(''.join(chars))
'''
        module = ast.parse(src)
        return module.body[0]