# Pyobfuscate

A modular Python code-obfuscation toolkit that transforms input scripts into functionally equivalent but harder-to-read output. It applies a sequence of injectors and renaming passes to obscure logic, control flow, and numeric constants. The toolkit is configurable and extensible via strategy plug-ins.

## Features

* Pluggable strategies for junk insertion, control-flow rewriting, and numeric literal encoding
* Deterministic runs via optional seed
* CLI for local use and FastAPI service for programmatic use
* Safe namespace tracking and renaming

## Project Structure

```
project-root/
├── Encrpytion/number_obscure_strategies.py
├── Encrpytion/number_obscurer.py
├── Injectors/conditional_injector.py
├── Injectors/identity_injector.py
├── Injectors/inject_junk.py
├── Injectors/junk_conditional_strategies.py
├── Injectors/junk_strategies.py
├── Injectors/identity_strategies.py
├── LoopObfuscation/ob_for.py
├── LoopObfuscation/obfuscation_strategies.py
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
* **loop_strategy**: `"plain"` or `"collatz"`.
* **conditional_strategies**: Currently `["random"]`.
* **identity_probability** *(float 0–1)*: Frequency of identity wrappers.
* **number_strategies**: Any ordered subset of `["feistel","xor_string","simple_feistel"]`.
* **return_code** *(bool)*: Include transformed code in the response.
* **seed** *(int)*: Makes a run repeatable.

## Extending

1. Implement a new strategy in the relevant module.
2. Register it in the API’s strategy map or wire it in the CLI pipeline.
3. Validate on representative inputs.

## Testing

```bash
python IO/input.py > original.out
python IO/output.py > obfuscated.out
diff original.out obfuscated.out
```

## License

MIT. See `LICENSE`.
