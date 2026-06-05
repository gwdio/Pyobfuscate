# Pyobfuscate

A modular Python code-obfuscation toolkit that transforms input scripts into functionally equivalent but harder-to-read output. It applies a sequence of injectors and renaming passes to obscure logic, control flow, and numeric constants. The toolkit is configurable and extensible via strategy plug-ins.

Runs entirely in your browser via Pyodide, or against a hosted API. Nothing leaves your machine unless you choose otherwise.

## Features

* **AST-level rewriting** — not just variable renaming or base64 encoding; the logic itself is restructured
* **Collatz-backed loop obfuscation** — `for` loops become `while` loops driven by a parameterized Collatz sequence; the loop condition reduces to an open mathematical conjecture
* **Feistel-encoded integer constants** — a 4-round Feistel cipher scrambles integer literals into runtime expressions
* **Opaque always-true conditionals** — statements wrapped in conditions that static analysis cannot resolve
* **Identity function injection** — expressions buried in identity wrappers (e.g. `1 and x`)
* **Junk statement injection** — dead arithmetic and bitwise noise
* **Full identifier renaming** — all user-defined names replaced with random 8-char strings
* **Composable, orderable pipeline** — toggle and reorder stages, run a stage multiple times
* **Reproducible output** — optional integer seed for deterministic runs
* **Custom strategy plug-ins** — implement your own obfuscation pass and load it from the UI
* **Concurrent-safe API** — isolated `random.Random` instance per request; no shared RNG state

## How the Collatz Loop Obfuscation Works

Each `for i in range(start, stop, step)` loop is rewritten as a `while` loop whose termination condition depends on a Collatz-like recurrence:

```
num ← target
while num ≠ seed:
    if num is even:  num ← num // 2
    else:            num ← a·num + b
    i ← idx          # plain counter, O(1) per iteration
    idx ← idx + step
    … original body …
```

The parameters `a`, `b`, `seed`, and `target` are chosen so the recurrence runs for exactly the right number of iterations. The loop condition `num ≠ seed` looks like it depends on an unsolved trajectory — to a static analyzer, it is indistinguishable from a loop that might not terminate.

### Seed determination via Chinese Remainder Theorem

Finding a valid `(seed, target)` pair efficiently is the hard part. Rather than a linear scan over candidate seeds, pyobfuscate uses the Chinese Remainder Theorem to narrow the search:

1. A random binary prefix sequence is generated (up to 10 steps). Each `1`-step in the sequence (the `a·num + b` branch) imposes a divisibility constraint and a parity constraint on the seed.
2. CRT intersects all constraints into a single residue class `seed ≡ r (mod M)`. The valid seeds are exactly `r, r+M, r+2M, …` — only a handful of candidates need to be checked.
3. For loops longer than the prefix, the remaining steps are generated probabilistically from the prefix endpoint, biasing toward the `a·num + b` branch to produce interesting trajectories.

This means seed determination is linear in the prefix length, not in the seed space. The resulting loop condition is structurally equivalent to the Collatz conjecture — an open problem with no known closed form — which limits the usefulness of symbolic execution against it.

**Runtime cost:** constant-factor overhead. Each loop iteration runs in O(1) additional work (one Collatz step, one counter increment). Total loop overhead is O(n), not O(n²) — there is no per-iteration walk of the sequence.

> This approach was developed independently. Concurrent academic work on opaque predicates and their resistance to symbolic execution is worth reading:
>
> - Cao, Y., Zhou, Z., & Zhuang, Y. (2025). Advancing code obfuscation: Novel opaque predicate techniques to counter dynamic symbolic execution. *Computers, Materials & Continua, 84*(1), 1545–1565. https://doi.org/10.32604/cmc.2025.062743
> - Xu, H., Zhou, Y., Kang, Y., Tu, F., & Lyu, M. R. (2018). Manufacturing resilient bi-opaque predicates against symbolic execution. In *2018 48th Annual IEEE/IFIP International Conference on Dependable Systems and Networks (DSN)* (pp. 666–677). IEEE. https://doi.org/10.1109/DSN.2018.00073

## Project Structure

```
project-root/
├── Encryption/number_obscure_strategies.py
├── Encryption/number_obscurer.py
├── Injectors/conditional_injector.py
├── Injectors/identity_injector.py
├── Injectors/inject_junk.py
├── Injectors/junk_conditional_strategies.py
├── Injectors/junk_strategies.py
├── Injectors/identity_strategies.py
├── LoopObfuscation/ob_for.py
├── LoopObfuscation/obfuscation_strategies.py
├── LoopObfuscation/collatz_seed.py
├── Renaming/renamer.py
├── NameTracker/naming.py
├── IO/input.py
├── IO/output.py
├── obfuscate.py          # CLI
└── app.py                # REST API
```

## Installation

```bash
git clone https://github.com/gwdio/Pyobfuscate.git
cd Pyobfuscate
pip install -r requirements.txt
```

## Makefile

`make help` lists everything. Common targets:

| Target | What it does |
|--------|-------------|
| `make install` | `pip install -r requirements.txt` |
| `make install-dev` | install + pytest |
| `make serve` | `uvicorn app:app --reload` |
| `make cli` | run `obfuscate.py` interactively |
| `make test` | run the pytest suite |
| `make verify` | diff `IO/input.py` vs `IO/output.py` runtime output |
| `make build` | build Lambda zip + Pyodide `package.json` |
| `make plan` | build then `terraform plan` |
| `make deploy` | test + build then `terraform apply` |
| `make clean` | remove build artifacts |

## Quickstart (CLI)

Place the target script at `IO/input.py`, then:

```bash
python obfuscate.py
```

Output is written to `IO/output.py`.

## REST API

Start the service:

```bash
uvicorn app:app --reload
```

### Endpoint

`POST /obfuscate`

**Request body (JSON):**

```json
{
  "input_path": "IO/input.py",
  "output_path": "IO/output.py",
  "enable_junk": true,
  "enable_loops": true,
  "enable_conditionals": true,
  "enable_identities": true,
  "enable_numbers": true,
  "enable_renaming": true,
  "junk_strategies": ["bitwise", "non_constant_time", "arithmetic"],
  "junk_density": 2,
  "loop_strategy": "collatz",
  "conditional_strategies": ["random"],
  "identity_probability": 0.2,
  "number_strategies": ["feistel", "xor_string"],
  "return_code": false,
  "seed": 42
}
```

**Response (JSON):**

```json
{
  "output_path": "IO/output.py",
  "code": null
}
```

If `return_code` is `true` or `output_path` is omitted, `code` contains the transformed source.

## Configuration Overview

* **input_path** *(required)*: Source `.py` to obfuscate.
* **output_path**: Destination file for obfuscated code.
* **enable_\* toggles**: Turn individual phases on/off.
* **junk_strategies**: Subset and order of `["arithmetic","bitwise","non_constant_time","lambda"]`.
* **junk_density** *(int)*: Intensity of junk insertion.
* **loop_strategy**: `"plain"` (straightforward for→while) or `"collatz"` (Collatz state machine).
* **conditional_strategies**: Currently `["random"]`.
* **identity_probability** *(float 0–1)*: Frequency of identity wrappers.
* **number_strategies**: Any ordered subset of `["feistel","xor_string","simple_feistel"]`.
* **return_code** *(bool)*: Include transformed code in the response.
* **seed** *(int)*: Makes a run repeatable.

## Extending

1. Implement a new strategy in the relevant module (or upload a `.py` file from the browser UI).
2. Register it in the API's strategy map or wire it in the CLI pipeline.
3. Validate on representative inputs.

Starter templates for each strategy family are available in the browser UI under **Custom Strategy**.

## Testing

Run the automated round-trip test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

Manual verification:

```bash
python IO/input.py > original.out
python IO/output.py > obfuscated.out
diff original.out obfuscated.out   # should be empty
```

## Limitations

Pyobfuscate is a practical deterrent, not a security guarantee. A determined analyst with enough runtime traces can still reverse-engineer behavior. It is not a replacement for access controls, encryption, or proper secrets management.

## License

MIT. See `LICENSE`.
