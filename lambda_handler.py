import json
import sys
import tempfile
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path

from pipeline import ObfuscationConfig, run_pipeline
from Utils.input_guard import validate_input

_TIMEOUT_SECONDS = 10

sys.setrecursionlimit(1000)

# Fields the caller must not inject (server-side concerns)
_BLOCKED_FIELDS = {"input_path", "output_path", "return_code"}


def lambda_handler(event, context):
    try:
        method = event.get("requestContext", {}).get("http", {}).get("method", "POST")
        if method.upper() != "POST":
            return _error(405, "Method not allowed")

        body = event.get("body") or "{}"
        if isinstance(body, str) and len(body.encode()) > 51_200:
            return _error(413, "Payload too large")
        payload = json.loads(body) if isinstance(body, str) else body

        source = payload.pop("source", None)
        if source is None:
            return _error(400, "Missing required field: 'source'")

        for field in _BLOCKED_FIELDS:
            payload.pop(field, None)

        try:
            validate_input(source)
        except ValueError as e:
            return _error(400, str(e))

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", dir="/tmp", delete=False, encoding="utf-8"
        ) as f:
            f.write(source)
            input_path = Path(f.name)

        try:
            cfg = ObfuscationConfig(input_path=input_path, return_code=True, **payload)
            result = _run_with_timeout(cfg)
        finally:
            input_path.unlink(missing_ok=True)

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"code": result}),
        }

    except FutureTimeout:
        return _error(408, f"Pipeline timed out after {_TIMEOUT_SECONDS} seconds")
    except json.JSONDecodeError:
        return _error(400, "Invalid JSON body")
    except SyntaxError as e:
        return _error(400, f"Syntax error in source: {e}")
    except RecursionError:
        return _error(400, "Input too deeply nested")
    except (ValueError, TypeError) as e:
        return _error(400, str(e))
    except FileNotFoundError as e:
        return _error(404, str(e))
    except Exception:
        return _error(500, "Processing error")


def _run_with_timeout(cfg: ObfuscationConfig) -> str:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run_pipeline, cfg)
        return future.result(timeout=_TIMEOUT_SECONDS)


def _error(status: int, message: str) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
