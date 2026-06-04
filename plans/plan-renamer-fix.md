# Plan: Fix Renamer — Dunder Methods and Attribute Call Sites

## Context

The `Renamer` breaks class-containing code in two ways, discovered while adding the test suite (`plan/testing`):

1. **Dunder methods get renamed.** `visit_FunctionDef` in `Renaming/renamer.py:31` unconditionally adds `node.name` to `to_rename`. This renames `__init__`, `__str__`, etc. — names Python calls implicitly by their fixed dunder spelling. After renaming, `ClassName(args)` silently skips `__init__` (falling through to `object.__init__`, which takes no arguments), causing `TypeError`.

2. **Method call sites are not updated.** `_Rewriter` rewrites `ast.FunctionDef.name` and `ast.Name` nodes but has no `visit_Attribute` handler. After obfuscation, method definitions get new random names (e.g., `def rAnDoM(self):`) but all call sites still use the original attribute spelling (`obj.method()`), causing `AttributeError`.

Together these make *any class with `__init__` or method calls* produce broken output. The `comprehensions.py` fixture was added as a workaround; after this fix, a proper `classes.py` fixture (with `__init__`, method calls, and inheritance) can be restored.

The plan also adds a `globals.py` fixture to verify that the fix does not regress global variable handling — which involves both `ast.Name(Store)` collection and the `visit_Global` rewrite path.

---

## Bugs and Fixes

### Bug 1: Dunders renamed — `Renaming/renamer.py`

**Collector (Pass 1, `Renamer.visit_FunctionDef`, line 31):**
```python
def visit_FunctionDef(self, node):
    self.to_rename.add(node.name)          # ← rename __init__ etc. — wrong
    ...
```

**Fix:** Skip dunder names:
```python
def visit_FunctionDef(self, node):
    if not (node.name.startswith('__') and node.name.endswith('__')):
        self.to_rename.add(node.name)
    ...
```

Same guard in `visit_AsyncFunctionDef` if/when added.

### Bug 2: Attribute call sites not updated — `Renaming/renamer.py`

**Rewriter (Pass 2, `_Rewriter`):** No `visit_Attribute` → method-name rewrites silently skip `obj.method()` call sites.

**Fix:** Add a handler to `_Rewriter`:
```python
def visit_Attribute(self, node):
    node.attr = self.mapping.get(node.attr, node.attr)
    return self.generic_visit(node)
```

This is safe: `self.mapping` only contains *user-defined* names (collected by Pass 1). External attribute access (`math.floor`, `dict.get`, etc.) will have attrs not in the mapping and pass through unchanged. The only edge case is if a user names a method the same as a stdlib attribute they also call on a different object — a rare collision that can be noted as a known limitation.

---

## Files to Modify

- **`Renaming/renamer.py`** — two targeted edits:
  1. Add dunder guard in `Renamer.visit_FunctionDef` (line 32)
  2. Add `visit_Attribute` to `_Rewriter` (after `visit_Name`, line 100)

---

## Files to Add / Update

### `tests/fixtures/classes.py` (new — replaces `comprehensions.py` workaround)

A class fixture that the renamer fix must keep working:

```python
class Animal:
    def __init__(self, name, sound):
        self.name = name
        self.sound = sound

    def speak(self):
        return self.name + " says " + self.sound

class Dog(Animal):
    def __init__(self, name):
        super().__init__(name, "woof")

    def fetch(self, item):
        return self.name + " fetches " + item

d = Dog("Rex")
print(d.speak())
print(d.fetch("ball"))
print(isinstance(d, Animal))
```

`comprehensions.py` stays — it provides different coverage (list/dict comprehensions).

### `tests/fixtures/globals.py` (new)

Covers the three distinct global-variable cases:

```python
LIMIT = 10           # module-level constant read inside a function
total = 0            # module-level variable mutated via `global`

def add(n):
    global total
    total += n

def is_within_limit(n):
    return n < LIMIT  # read-only reference to module global (no `global` stmt)

for i in range(1, 4):
    add(i)

print(total)                 # 6
print(is_within_limit(5))    # True
print(is_within_limit(15))   # False
```

---

## Verification

```bash
# Run existing suite — should still be 8/8
python -m pytest -v

# After adding the two new fixtures, should be 10/10
python -m pytest -v

# Manual spot-check: the classes fixture in isolation
python tests/fixtures/classes.py   # should print: Rex says woof / Rex fetches ball / True
```

After the fix, running the obfuscator on `tests/fixtures/classes.py` end-to-end with seed 42 should produce working code.
