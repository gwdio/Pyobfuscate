# Obfuscate.py

A modular Python code obfuscation toolkit that transforms input scripts into functionally equivalent but harder-to-read output. Designed for safety and extensibility, it applies a sequence of injectors and renaming passes to obscure logic, control flow, and numeric constants. Can be made much harder through injections of `exec`s and other statements but from pure logical obfuscation almost as far as you can take it.

## 📁 Project Structure

```
project-root/
├── Encrpytion/number_obscure_strategies.py   # Numeric obfuscation strategy implementations
├── Encrpytion/number_obscurer.py             # Injector for number-obscuring transformations
├── Injectors/conditional_injector.py         # Wraps statements in conditional branches
├── Injectors/identity_injectors.py           # Applies identity-function wrappers
├── Injectors/junk_injector.py                # Inserts junk code like dead branches or no-ops
├── Injectors/junk_conditional_strategies.py  # Strategies for conditional junk code
├── Injectors/junk_strategies.py              # Generic junk-injection approaches
├── Injectors/identity_strategies.py          # Strategies for identity-function injection
├── LoopObfuscation/ob_for.py                 # Loops → convoluted while loops converter
├── LoopObfuscation/obfuscation_strategies.py # Loop transformation strategies
├── Renaming/renamer.py                       # Namespace analysis and identifier renaming
├── NameTracker/naming.py                     # Global name tracker to ensure no collisions
├── IO/input.py                               # Sample input script (user-provided)
├── IO/output.py                              # Generated obfuscated script
└── obfuscate.py                              # Orchestrator: ties injectors into a pipeline
```

## 🚀 Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/obfuscate.py.git
   cd obfuscate.py
   ```
2. Install dependencies (if any):

   ```bash
   pip install -r requirements.txt
   ```

## 🔧 Usage

Place your target Python script at `IO/input.py`. Then run:

```bash
python obfuscate.py
```

The obfuscated result will be written to `IO/output.py`.

### Command-Line Options

* **`IO/input.py`**: Path to the source file to obfuscate
* **`IO/output.py`**: Path to write the obfuscated script

## 🛠 Customizing the Obfuscation Pipeline

The `main()` function in `obfuscate.py` shows the default pipeline sequence. You can adjust:

1. **Injector order**: Change the transform sequence to apply injectors in a different order.
2. **Thresholds and weights**: Many injectors accept parameters (e.g., junk probability, identity-factor) to tune aggressiveness.
3. **Strategy lists**: Swap in or out specific strategies for junk injection, identity functions, numeric obfuscation, or loop transformations.

Example: Swap out `CollatzStrategy` for `ModularMultiplicativeStrategy` in loop obfuscation:

```python
from LoopObfuscation.obfuscation_strategies import ModularMultiplicativeStrategy

# Replace:
tree = Ob_For(naming, CollatzStrategy).apply(tree)
# With:
tree = Ob_For(naming, ModularMultiplicativeStrategy).apply(tree)
```

## ⚙️ Core Components

### 1. `JunkInjector`

* **Location**: `Injectors/junk_injector.py`
* **Purpose**: Inserts dead code branches, no-ops, and opaque predicates.
* **Key Strategies**: `BitwiseStrategy`, `ArithmeticStrategy`, `NonConstantTimeStrategy`, etc.

### 2. `Ob_For`

* **Location**: `LoopObfuscation/ob_for.py`
* **Purpose**: Converts `for` loops into `while` loops
### 3. `ConditionalInjector`

* **Location**: `Injectors/conditional_injector.py`
* **Purpose**: Wraps statements in always-true/false conditionals with dummy branches.
* **Key Strategy**: `RandomConditionalStrategy`

### 4. `IdentityFuncInjector`

* **Location**: `Injectors/identity_injectors.py`
* **Purpose**: Wraps expressions or statements with harmless identity functions to confuse analysis.
* **Key Strategy**: `MixedIdentityStrategy`

### 5. `NumberObscurerInjector`

* **Location**: `Encrpytion/number_obscurer.py`
* **Purpose**: Encodes numeric literals using reversible schemes.
* **Key Strategies**:

  * `FeistelNumberStrategy` (bit-level mixing via Feistel network)
  * `XorStringNumberStrategy` (XOR with random string key)

### 6. `Renamer`

* **Location**: `Renaming/renamer.py`
* **Purpose**: Performs namespace analysis and replaces identifiers with non-meaningful names.

## 📈 Extending the Toolkit

1. **Add new strategies**: Implement a new class inheriting from the appropriate `*Strategy` interface (e.g., `JunkConditionalStrategy`, `NumberObscureStrategy`).
2. **Register your strategy**: Pass it into the injector in `obfuscate.py`.
3. **Test for correctness**: Ensure `IO/output.py` still executes with identical behavior.

## 🧪 Testing & Validation

* Compare behavior of `IO/input.py` vs. `IO/output.py`:

  ```bash
  python IO/input.py > original.out
  python IO/output.py > obfuscated.out
  diff original.out obfuscated.out
  ```
* Use CI to automate pipeline runs and output validation.

## 📄 License

MIT License. See [LICENSE](./LICENSE) for details.

---

*Happy Obfuscating!*
