# Postmortem: CloudFront OAC + Lambda Function URL Auth, and Client/Server Execution Coupling

**Service:** pyobfuscate.grantwang.dev — Python obfuscator
**Architecture:** Browser → CloudFront → S3 (static assets) / Lambda Function URL (POST `/obfuscate`)
**Broken from:** Initial deployment (`age: 400+` on cached error responses confirms full-duration outage)
**Active investigation:** June 2, 2026 → June 4, 2026
**Resolved:** June 4, 2026, 12:57 AM — verified end-to-end POST working (the early account's "June 3" was assumed, not confirmed). The client/server execution-coupling fix (below) landed earlier, June 2 → June 3 before noon.
**Severity:** Full outage — all dynamic requests returning 403; "client mode" silently non-functional in deployment
**Resolution:** End-to-end POST working with OAC + IAM + `source_arn` + client-side body hash; client and server execution paths fully decoupled

---

## One-Line Summary

Securing a Lambda Function URL to be invocable only through one CloudFront distribution
(OAC + IAM, no shared-secret reliance) required fixing **six independent problems** in the
auth chain, each of which silently masked the next. Several produced the *same* `403`
symptom from *different* layers, which repeatedly sent the investigation down the wrong path.

Running underneath that was a **separate architectural fault**: the client-side (Pyodide)
and server-side (Lambda) execution paths were coupled through a shared server endpoint, so a
single infrastructure failure broke both modes at once and made it impossible to tell which
path was actually failing. The two faults shared a literal culprit — the same
`custom_error_response` rule masked errors in *both* — which is why they're documented
together here.

---

## ⚠️ Note on a Superseded Conclusion

> The **initial exploration** of this incident concluded that **CloudFront OAC does not
> populate `AWS:SourceArn`** for Lambda Function URLs and that the fix was to **remove
> `source_arn`** from the Lambda permission (accepting a confused-deputy risk).
>
> **This conclusion was wrong and has been superseded.** OAC *does* set `AWS:SourceArn`,
> and `source_arn` *is* required and present in the final working configuration. The
> "remove `source_arn`" diagnostic produced a false positive because the permission used
> in that test still carried `function_url_auth_type = "AWS_IAM"` (problem #2 below) and
> the host-header bug (problem #3) was still unfixed — so removing `source_arn` was never
> what changed the outcome. See [Wrong Turns & Red Herrings](#wrong-turns--red-herrings)
> for the full explanation.
>
> **The "service restored" claim in that early account was assumed, not verified.** It was
> the first pass at the problem (alongside a since-lost coding session), written before the
> real fix was found. When later asked for postmortem material, it was told only that "major
> changes" had been made and inferred that its own `source_arn` removal was the change that
> worked — it never confirmed that POST `/obfuscate` actually succeeded. The genuine value
> retained from it below is the **initial symptoms, detection gap, and references** — not its
> root cause or resolution. The verified end-to-end fix is the one in
> [Final Working Configuration](#final-working-configuration).

---

## Background

The goal was to lock a Lambda Function URL so it could only be invoked through one specific
CloudFront distribution, using Origin Access Control (OAC) with IAM authentication — rather
than relying solely on a shared secret header or leaving the URL publicly invokable.

OAC for Lambda Function URL origins launched **April 11, 2024** and **explicitly requires
`AWS_IAM`** as the Function URL `AuthType`. Guidance written before that date (e.g. blog
posts noting that `AWS_IAM` caused 403s) is now stale and was an early source of confusion.

---

## Initial Symptoms

1. **Empty headers in CloudWatch.** Lambda logs showed events with `"headers": {}` — no
   SigV4 signing headers (`Authorization`, `X-Amz-Date`, `X-Amz-Security-Token`). The
   `/package.json` path in one such event indicated an automated scanner probing the raw
   Lambda URL directly, which initially (and misleadingly) supported a "requests bypassing
   CloudFront" theory. (Note: this scanner traffic is unrelated to the app's own Pyodide
   loader, which originally fetched the *dynamic* `/package` route and was later repointed at
   a *static* `/package.json` S3 object — see
   [Client/Server Execution Coupling](#architectural-root-cause-clientserver-execution-coupling).
   A `/package.json` request landing on the Lambda URL with empty headers is a scanner, not
   the loader, since the loader is served from S3/CloudFront.)
2. **All dynamic requests 403.** CloudFront returned `403` with `x-cache: Error from cloudfront`.
3. **GET worked once OAC/IAM was correct; POST still failed.** This split was the key to
   eventually isolating the body-hash problems from the IAM-wiring problems.

A decoder for the three distinct 403 bodies seen during the investigation:

| Response | Meaning |
|---|---|
| `{"Message":"Forbidden"}` | No valid SigV4 signature at all |
| `{"Message":null}` (`x-amzn-errortype: AccessDeniedException`) | Valid signature from `cloudfront.amazonaws.com`, but a resource-policy condition fails (or the signed host doesn't match) |
| `{"message":"The request signature we calculated does not match..."}` | Signature present but the **body hash** mismatches |

`{"Message":null}` was the most misleading: it reads like a permissions problem but in this
incident was caused by condition failures and host-header mismatch, not by a missing grant.

---

## Root Causes (in order of discovery)

### 1. `custom_error_response` masking raw errors

The distribution converted every `403` into a `200` serving `index.html`:

```hcl
custom_error_response {
  error_code         = 403
  response_code      = 200
  response_page_path = "/index.html"
}
```

The browser saw HTML with a `200` status, hiding the real error entirely.

An error-to-`200`-HTML rewrite is the kind of masking that makes failures invisible, and the
earlier client-side Pyodide loader failure may have involved the same class of behavior —
though the exact loader symptom is unconfirmed (see
[Client/Server Execution Coupling](#architectural-root-cause-clientserver-execution-coupling)).
What's certain here is that this rule masked the auth failures.

**Fix:** Temporarily remove `custom_error_response` to expose raw errors during debugging.
(Longer term, scope it so it does not blanket-convert API/loader errors into `200` HTML.)

---

### 2. `function_url_auth_type` on the permission adds an unsatisfiable condition

The Terraform `aws_lambda_permission` argument `function_url_auth_type = "AWS_IAM"` injects
this condition into the resource policy:

```json
"Condition": {
  "StringEquals": { "lambda:FunctionUrlAuthType": "AWS_IAM" }
}
```

This condition key is **not present in the IAM authorization context** when the caller is
CloudFront OAC. `StringEquals` on a missing key evaluates to `false` → implicit deny →
`AccessDeniedException {"Message":null}`, with **no Lambda CloudWatch invocation**.

Critically, because this condition is ANDed with the `source_arn` condition, it failed
*before* `source_arn` was ever meaningfully evaluated — which is what created the false
impression that `source_arn` was broken.

**Symptom:** `403`, `x-amzn-errortype: AccessDeniedException`, body `{"Message":null}`, no Lambda invocation.

**Fix:** Do **not** use `function_url_auth_type` in `aws_lambda_permission`. Use `source_arn` instead. (The Function URL still has `authorization_type = "AWS_IAM"` set on the `aws_lambda_function_url` resource — that is required and separate.)

---

### 3. `host` header must be excluded from the origin request policy

OAC signs origin requests with SigV4 using the **Lambda Function URL domain**
(`<id>.lambda-url.us-east-1.on.aws`) as the canonical host. If the origin request policy
forwards the viewer's `Host` header (`pyobfuscate.grantwang.dev`) to the origin, Lambda
receives a different host than OAC signed with → signature invalid.

This is exactly why AWS provides the managed policy named
`Managed-AllViewerExceptHostHeader`. The Terraform had referenced that policy as a data
source but was using a custom policy that omitted `host`.

**Symptom:** signature mismatch, and (depending on layering) `{"Message":null}`.

**Fix:**
```hcl
headers_config {
  header_behavior = "allExcept"
  headers { items = ["authorization", "host"] }
}
```

---

### 4. `source_arn` IS required and OAC DOES set `AWS:SourceArn`

Early in the investigation it appeared that `source_arn` couldn't work — `AWS:SourceArn`
was assumed to be unset by OAC for Lambda Function URLs. **This was wrong.** OAC does set
`AWS:SourceArn`. `source_arn` appeared broken only because `function_url_auth_type`
(problem #2) was *also* present in the combined condition; both had to pass, the
`function_url_auth_type` clause always failed, so the `source_arn` clause was never the
deciding factor. Removing only `source_arn` left the broken clause in place and the error
was unchanged — which led to the incorrect conclusion that `source_arn` was the culprit.

`source_arn` scopes invocation to the one specific distribution ARN (via `ArnLike`),
preventing any other CloudFront distribution — including ones in other AWS accounts — from
invoking the function. It belongs in the final config.

**Fix:** Use `source_arn` **without** `function_url_auth_type`.

---

### 5. Two Lambda permissions are required

OAC for Lambda Function URLs requires **two** resource-based policy statements. One alone
is insufficient — with only `lambda:InvokeFunctionUrl`, the signing chain still produces
`AccessDeniedException`.

```hcl
resource "aws_lambda_permission" "cloudfront_url" {
  statement_id  = "AllowCloudFrontInvokeFunctionUrl"
  action        = "lambda:InvokeFunctionUrl"
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
  function_name = aws_lambda_function.obfuscator.function_name
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id  = "AllowCloudFrontInvokeFunction"
  action        = "lambda:InvokeFunction"     # this one too
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
  function_name = aws_lambda_function.obfuscator.function_name
}
```

---

### 6. POST requires `x-amz-content-sha256` with the actual body SHA-256

GET requests sign fine (no body). For POST with a body, SigV4 requires the SHA-256 of the
body in the canonical request, and OAC uses the value of the `x-amz-content-sha256` header
as that payload hash. Lambda Function URLs **reject** a missing hash or `UNSIGNED-PAYLOAD`
(a sentinel S3 accepts in some scenarios but Lambda URLs do not). The client (browser) must
compute the real hash and send it; CloudFront OAC incorporates it into the signature, and
Lambda verifies it against the body it actually received.

**Failed alternatives:**
- No `x-amz-content-sha256` → OAC uses a different payload hash than Lambda expects → mismatch
- `x-amz-content-sha256: UNSIGNED-PAYLOAD` → not accepted for POST bodies → mismatch

**Required browser-side code:**
```js
const payloadBytes = new TextEncoder().encode(payload);
const hashBuffer   = await crypto.subtle.digest('SHA-256', payloadBytes);
const hashHex      = Array.from(new Uint8Array(hashBuffer))
                       .map(b => b.toString(16).padStart(2, '0')).join('');

fetch('/obfuscate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'x-amz-content-sha256': hashHex,
  },
  body: payload,
});
```

> **Implementation trap:** An agentic coding tool was instructed three times to implement
> this and each time deployed `'x-amz-content-sha256': 'UNSIGNED-PAYLOAD'` instead of
> computing the hash. The instructions were correct; the deployed artifact was not. **Verify
> the actual served JS, not the apply output, when delegating to an agent.**

---

### 7. A viewer-request CloudFront Function reading `event.request.body` re-encodes the body

The `/obfuscate` cache behavior had a viewer-request CloudFront Function (`reject_truncated`)
that touched the request body:

```javascript
function handler(event) {
  var body = event.request.body;     // ← merely referencing the object triggers buffering
  if (body && body.inputTruncated) { ... }
  return event.request;
}
```

When a CloudFront Function accesses the request body object, CloudFront **buffers and
re-encodes** the body. The re-encoded bytes forwarded to the origin are not bit-for-bit
identical to what the browser sent. The browser hashed the original bytes; OAC hashed the
re-encoded bytes → mismatch.

This was the **last problem standing** and the hardest to find because:
- It affected only POST (GET has no body)
- It produced the *same* signature-mismatch error as problems #3 and #6
- The function code looked correct

**Confirmed by:** a `curl` request computing and sending `x-amz-content-sha256` worked
(curl does not pass through the CloudFront Function), while the browser failed with the
*same hash value* (it does pass through the function).

**Fix:** Remove the viewer-request function association from `/obfuscate`. Move body-size
protection into the Lambda handler (51 KB check). If a viewer-request function is truly
needed, read only the `body.inputTruncated` boolean — never `body.data` and ideally never
the body object at all when OAC is in use.

---

## Architectural Root Cause: Client/Server Execution Coupling

Distinct from the seven auth-chain problems above, an architectural fault made the outage
harder to see and harder to diagnose. pyobfuscate offers two execution paths — a client-side
path running Python in the browser via Pyodide, and a server-side path calling the Lambda.
These were supposed to be independent. They weren't.

**This was found and fixed first, before the server-side auth work began.** It surfaced
almost by accident. The reported symptom was simply that Pyodide wasn't loading in prod —
"did it not get packaged, or does it just need more time?" While investigating, a coding
session mentioned offhand that the Pyodide path and the server-side path were unified, which
prompted drilling deeper into how client mode actually loaded its code. So the sequence was:
discover and decouple the client path (June 2 → June 3 before noon), *then* take on the
OAC/IAM saga (resolved June 4, 12:57 AM).

### What was coupled

The client-side Pyodide path loaded its Python source files by calling `fetch('/package')`
from `app.js`. `/package` was a **`GET /package` route defined in `app.py`** (FastAPI) —
fine in local dev where the FastAPI server runs, but the prod deployment runs only
`lambda_handler.py`, which handles **only `POST /obfuscate`**. Nothing serves `/package` in
prod, so:

- Client mode silently did not work in deployment, and it failed *invisibly* — there was no
  surfaced network error to notice. It fell back to server-only mode (which the auth outage
  had also broken), so from the front end nothing worked and there was no clear signal why.
- More fundamentally, "client mode" was not really client-side: it required a live server
  route just to initialize. If the server was down, client mode couldn't load its packages.
  And because the auth outage (the entire saga above) was already breaking server mode,
  **both paths were broken at once** — a dead client path falling back to a dead server path.
  The two failures were indistinguishable from the front end.

> **Open question — the exact client-side symptom is not reliably reconstructed.** Memory of
> the front-end behavior has been inconsistent in hindsight, and the candidate observations
> point to different mechanisms: (a) the `/package` request never firing at all — no network
> entry, not even a wrong address; (b) the request appearing to succeed (`200`, content
> downloaded) but carrying `index.html` instead of the package JSON, via either
> `custom_error_response` (root cause #1) or an SPA/`index.html` fallback; or (c) a surfaced
> `404`. What's consistent across all of them is that it was **not** a visible network
> failure that pointed at the cause, and that client mode quietly did nothing. The
> architectural root cause below is solid regardless; the precise runtime symptom would need
> the original session, git history, or a devtools repro to confirm, and should be treated as
> open until then.

### Fix — make the package payload a static build artifact

The fix had four parts:

1. **Generated `frontend/package.json`** — a static JSON file containing all 22 Python
   source files (the same set that `_PACKAGE_FILES` in `app.py` enumerates).
2. **Relied on the existing Terraform upload.** `fileset(local.frontend_dir, "**")` already
   uploads everything under `frontend/` to S3, so the new file is served at `/package.json`
   by CloudFront with **no config change**.
3. **Added a `/package.json` endpoint to `app.py`** so local dev still works. FastAPI serves
   static files under `/frontend/*`, not `/`, so the static file alone wouldn't be reachable
   at `/package.json` locally — the explicit route bridges that gap.
4. **Changed `fetch('/package')` → `fetch('/package.json')` in `app.js`**, and added
   `scripts/build_package_json.py` to regenerate the file whenever the Python sources change.

The two paths now share nothing at runtime:

| Path | Runtime dependencies |
|------|----------------------|
| Client (Pyodide) | CDN (Pyodide runtime) + S3/CloudFront (static `package.json`) |
| Server (Lambda)  | CloudFront → Lambda Function URL |

A Lambda/OAC outage no longer affects client mode; a Pyodide CDN issue no longer affects
server mode.

**Note on `custom_error_response`:** regardless of whether it (or an SPA fallback) was what
served HTML to the loader, the static `/package.json` now returns a real `200` with valid
JSON, so there's no `404` to rewrite and no fallback to hit — the fix sidesteps the masking
either way. Note also that `custom_error_response` was *not* removed here; it (or whatever
hardening existed) stayed in place and, in the server-side investigation that followed, went
on to mask the auth failures as well (root cause #1; removed at timeline step 1). Whatever
the exact CloudFront mechanism, the lesson holds: an error-to-`200`-HTML rewrite hides
failures, and it bit this project more than once.

### Key lesson

**Client-side execution should have zero runtime server dependencies.** If the browser
runtime needs Python source files, those files must be static assets uploaded at deploy time
— not generated on demand by the same server the "server mode" button calls. Coupling them
means one infrastructure failure breaks both modes *and* destroys your ability to diagnose
which one broke. That coupling is a large part of why the auth investigation above was so
hard to localize.

> **Accuracy note:** the narrative beats of this section are confirmed; some specifics
> (exact filenames, the precise error string) are reconstructed from a session that is no
> longer fully available and may be slightly off.

---

## Investigation Timeline

| Step | Action | Outcome |
|------|--------|---------|
| Start | POST `/obfuscate` returns HTML 200 | `custom_error_response` masking 403s |
| 1 | Remove `custom_error_response` | Raw 403, "signature mismatch" |
| 2 | Change ORP to forward viewer host (mistake) | Error changes to `AccessDeniedException` |
| 3 | Remove `source_arn` from permission (mistake) | Still `AccessDeniedException` — `function_url_auth_type` still present |
| 4 | Add `X-Origin-Secret` env var | Terraform provider quirk: env block count 0→1 |
| 5 | Full destroy + rebuild | `AccessDeniedException` persists |
| 6 | Try `source_arn` only (no `function_url_auth_type`) | `AccessDeniedException` (host still forwarded) |
| 7 | Try no conditions | `AccessDeniedException` |
| 8 | Exclude `host` from ORP | progresses past signature/condition failures |
| 9 | Add second `lambda:InvokeFunction` permission | GET path now viable |
| 10 | Add GET health-check Lambda | `/health` works → confirms IAM + `source_arn` + two-perms OK for GET |
| 11 | Send computed `x-amz-content-sha256` from browser | 403 signature mismatch |
| 12 | Try `UNSIGNED-PAYLOAD` | 403 signature mismatch |
| 13 | Remove `x-amz-content-sha256` entirely | 403 signature mismatch |
| 14 | `curl` with computed hash | **Works** → proves the browser path is the variable |
| 15 | Remove `reject_truncated` viewer-request function | **POST `/obfuscate` works** |

---

## The Health-Check Lambda: Best Diagnostic in the Session

A dedicated **GET-only** Lambda at `/health`, with its own OAC and `source_arn`-scoped
permission, was the single most effective debugging tool. Because GET has no body, the
`x-amz-content-sha256` requirement does not apply, which cleanly isolates OAC/IAM wiring
from the POST body-hash problems.

Diagnostic sequence:
1. `/health` returns `{"ok":true,"msg":"OAC wiring verified"}` → OAC, IAM auth, `source_arn` condition, and host-header policy are all correct.
2. `/obfuscate` POST still failing → problem is isolated to body-hash handling.
3. `curl` with a manually computed hash works → the hash approach is correct; the client implementation is wrong.
4. Client implementation looks correct but still fails → something between browser and Lambda is mutating the body (→ the CloudFront Function).

---

## Wrong Turns & Red Herrings

- **"`source_arn` doesn't work / OAC doesn't set `AWS:SourceArn`"** — **False.** It does. The
  real problem was `function_url_auth_type` failing in the same combined condition, masking
  `source_arn`. This is the superseded conclusion noted at the top of this document.
- **"Remove `source_arn` and accept the confused-deputy risk"** — Unnecessary. `source_arn`
  works once `function_url_auth_type` is removed and the host header is excluded. The
  confused-deputy trade-off was never required.
- **"Forwarding the viewer `Host` header fixes OAC"** — False and counterproductive. OAC
  signs with the Lambda URL domain; the host reaching Lambda must match.
- **"`UNSIGNED-PAYLOAD` is what OAC uses for POST"** — False. OAC uses the actual body SHA-256.
- **"CloudFront Functions are body-transparent"** — False. Accessing `event.request.body` at
  all triggers buffering and re-encoding.
- **"Requests are bypassing CloudFront"** — The empty-header CloudWatch event with
  `/package.json` was an external scanner hitting the raw URL, not evidence of a CloudFront
  bypass in legitimate traffic.
- **"Terraform renders the `source_arn` condition incorrectly"** — False. The provider emits
  correct IAM JSON; the problem was never how Terraform rendered the ARN condition.

---

## Final Working Configuration

| Component | Setting |
|---|---|
| Lambda Function URL `AuthType` | `AWS_IAM` |
| Lambda resource-policy actions | `lambda:InvokeFunctionUrl` **and** `lambda:InvokeFunction` (two statements) |
| Lambda resource-policy condition | `source_arn = <distribution ARN>` (no `function_url_auth_type`) |
| CloudFront OAC origin type | `lambda` |
| CloudFront OAC signing behavior | `always` |
| CloudFront OAC signing protocol | `sigv4` |
| Origin request policy | `allExcept: [authorization, host]` |
| Viewer-request CF Function on `/obfuscate` | **none** (body-size check moved into Lambda handler) |
| Client POST requests | compute SHA-256 via `crypto.subtle.digest`, send as `x-amz-content-sha256` |

### Lambda permissions (two required)
```hcl
resource "aws_lambda_permission" "cloudfront" {
  statement_id  = "AllowCloudFrontInvokeFunctionUrl"
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.obfuscator.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id  = "AllowCloudFrontInvokeFunction"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.obfuscator.function_name
  principal     = "cloudfront.amazonaws.com"
  source_arn    = aws_cloudfront_distribution.main.arn
}
```

### Lambda Function URL
```hcl
resource "aws_lambda_function_url" "obfuscator" {
  function_name      = aws_lambda_function.obfuscator.function_name
  authorization_type = "AWS_IAM"
}
```

### OAC
```hcl
resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "pyobfuscate-lambda-oac"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}
```

### Origin request policy (host MUST be excluded)
```hcl
resource "aws_cloudfront_origin_request_policy" "lambda" {
  headers_config {
    header_behavior = "allExcept"
    headers { items = ["authorization", "host"] }
  }
  cookies_config       { cookie_behavior       = "all" }
  query_strings_config { query_string_behavior = "all" }
}
```

---

## Lambda@Edge: Considered and Rejected

Computing `x-amz-content-sha256` server-side via Lambda@Edge (origin-request event) was
proposed to avoid client changes. Rejected because:
- Lambda@Edge runs at roughly 3× the per-GB-second cost of regular Lambda.
- Lambda@Edge silently truncates request bodies at 1 MB; Lambda Function URLs support up to 6 MB.
- The Web Crypto API (`crypto.subtle.digest`) is built into every modern browser and computes the hash in a few lines with no added infrastructure.

The client-side hash was chosen instead.

---

## Detection Gap

The breakage was present from the very first deployment but went unnoticed because:
- CloudFront cached the initial 403 responses (`age: 400+`).
- No Lambda CloudWatch logs were produced (auth failed at the Function URL layer, before the handler ran).
- No uptime monitoring or synthetic-request alerting was in place.
- An error-to-`200`-HTML response (whether `custom_error_response` or an SPA `index.html`
  fallback) meant auth failures didn't surface as non-200s.
- The client/server coupling meant the two failures were indistinguishable from the front
  end: client mode silently fell back to a dead server path, so even an observant user
  couldn't tell that *two* separate things were broken, or which one. (The exact client-side
  symptom is unconfirmed — see the coupling section — but in every recalled version it failed
  silently rather than surfacing a clear error.)

The only observable signal was CloudFront serving 403s with `x-cache: Error from cloudfront`,
which requires active traffic or monitoring to catch.

**Action items:**
- Add synthetic POST monitoring against `/obfuscate` (not just GET `/health`) so body-path
  regressions are caught.
- Add a synthetic check that exercises client mode (Pyodide loads `/package.json` and runs)
  independently of server mode, so a regression in one path can't hide behind the other.
- Scope `custom_error_response` so it doesn't blanket-convert API/loader errors into `200`
  HTML — error responses should stay observable.

---

## What to Restore (defence in depth)

The `X-Origin-Secret` belt-and-suspenders approach (custom origin header + Lambda-side
validation) was commented out during debugging. With OAC + IAM proven working, restore it:

1. Uncomment `random_password.origin_secret`
2. Uncomment `environment.variables.ORIGIN_SECRET` on the obfuscator Lambda
3. Uncomment `custom_header` on the Lambda CloudFront origin
4. Restore `X-Origin-Secret` validation in `lambda_handler.py`

OAC cryptographically proves the request came from your CloudFront distribution; the secret
header adds a second check that the distribution hasn't been misconfigured to forward
traffic it shouldn't. (With `source_arn` correctly in place, this is genuinely
defence-in-depth rather than a workaround for a confused-deputy gap.)

---

## References

- AWS What's New, April 11 2024 — CloudFront OAC for Lambda function URL origins:
  https://aws.amazon.com/about-aws/whats-new/2024/04/amazon-cloudfront-oac-lambda-function-url-origins/
- AWS CloudFront Developer Guide — Restrict access to a Lambda function URL origin:
  https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-lambda.html
- AWS re:Post — Lambda function URL using CloudFront OAC:
  https://repost.aws/questions/QUF-r_6HrRRf2MZAdxYGkX7Q/lambda-function-url-using-cloudfront-oac
- AWS blog — Secure your Lambda function URLs using CloudFront OAC:
  https://aws.amazon.com/blogs/networking-and-content-delivery/secure-your-lambda-function-urls-using-amazon-cloudfront-origin-access-control
- Terraform AWS provider issue #28296 (related condition-key handling):
  https://github.com/hashicorp/terraform-provider-aws/issues/28296

> **Caveat on one external source:** arpadt.com's "Lambda does not support locking function
> URL invocations to specific resources" was cited in the superseded account as proof that
> `source_arn` is inert. The on-the-ground result in this incident contradicts that reading:
> `source_arn` is present and functioning in the final configuration. Treat that claim with
> skepticism for the OAC case.