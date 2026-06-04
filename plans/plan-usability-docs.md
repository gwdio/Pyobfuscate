# Plan: Usability, Docs, and Credits

**Depends on:** `plan-randomness.md` and any code cleanup that stabilises the
public-facing API surface before documentation is written.

## Goals

1. Welcome modal with usage guide, repo link, and project description.
2. In-app help for custom strategies, including starter code templates.

---

## 1. Welcome Modal

Shown on first visit (and on revisit unless dismissed with "don't show again").

**Content:**
- One-line pitch: "Pyobfuscate is the first static, logic-level Python
  obfuscator that runs entirely in your browser."
- Brief how-to: paste code → configure pipeline → run → copy output.
- Link to the GitHub repo.
- "Don't show this again" checkbox that sets a `localStorage` key.

**Behaviour:**
- Appears automatically on page load if the `localStorage` key is absent.
- Accessible at any time via a Help / ? button in the header.
- Dismissible with Escape or a close button; "Don't show again" only persists
  when the user explicitly checks it and then closes.

---

## 2. Custom Strategy Help

Custom strategies are the most powerful but least discoverable feature. Add
contextual help that makes them approachable.

**Help panel / tooltip per phase card:**
- Brief description of what the strategy interface for that phase does.
- Starter code template pre-filled in the editor when the user selects
  "Custom" — a minimal valid implementation with the required method signature,
  type annotations, and a `pass`-body comment explaining what to return.
- Link to the relevant section of the README / repo wiki for full docs.

**Starter templates to write (one per strategy family):**

```python
# JunkInjectionStrategy
import ast
from typing import List

class MyJunkStrategy:
    def get_junk(self, rng) -> List[ast.stmt]:
        # Return a list of AST statement nodes to inject as junk.
        # rng is a random.Random instance — use it instead of the global random.
        return []
```

```python
# IdentityFuncStrategy
import ast

class MyIdentityStrategy:
    def wrap(self, expr: ast.expr, rng) -> ast.expr:
        # Wrap expr in an operation that always evaluates to expr.
        # Must return a valid ast.expr node.
        return expr
```

```python
# NumberObscureStrategy
import ast

class MyNumberStrategy:
    def obfuscate(self, value: int, rng) -> ast.expr:
        # Return an AST expression that evaluates to value.
        return ast.Constant(value=value)
```

```python
# LoopObfuscationStrategy
import ast
from typing import List

class MyLoopStrategy:
    def get_loop_index_setup(self, rng) -> List[ast.stmt]:
        # Return statements that initialise the loop index variable.
        return []

    def get_loop_condition(self, rng) -> ast.expr:
        # Return an expression that is the while-loop condition.
        return ast.Constant(value=True)

    def get_loop_index_update(self, rng) -> List[ast.stmt]:
        # Return statements to update the loop index at the end of each iteration.
        return []
```

---

## Files Affected

- Frontend: welcome modal component (new), help panel / tooltip per card
  (new or extension of existing card component)
- Starter code templates: stored as constants in the frontend (strings) or as
  small `.py` template files fetched at runtime
- README / wiki: written separately; the in-app links point to it

## Branch

`plan/usability-docs`
