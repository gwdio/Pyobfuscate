"""
Parametrized generalized-Collatz parity-word solver.

A map is defined by three numbers (base b, multiplier m, constant a):

    if  v ≡ 0 (mod b):   v -> v / b          # the '0' step  (divide)
    else:                v -> m*v + a        # the '1' step  (multiply)

Classic Collatz is (b, m, a) = (2, 3, 1). The CLI also covers 3x-1
(2, 3, -1), 5x+7 (2, 5, 7), base-3 maps like (3, 2, 1), etc.

Given a step string over {0,1}, find the smallest start n whose trajectory
follows exactly that sequence of operations, with start > threshold,
end > threshold, all values positive, and every value unique.

--------------------------------------------------------------------------
Why the CRT-style narrowing works (and when it doesn't)
--------------------------------------------------------------------------
Track the value as an affine function of the start:  v = (P*n + Q) / b^e.
A '0' step requires  v ≡ 0 (mod b), i.e.

        P*n + Q ≡ 0  (mod b^(e+1))

The accumulated multiplier is P = m^(#multiply-steps). That congruence is
uniquely solvable in n  iff  P is invertible mod b^(e+1), i.e. iff
gcd(m, b) = 1. Each '0' step therefore pins n in a residue class to one
higher power of b; combining them (prime-power lifting -- "CRT" for the
single prime dividing b) collapses the search to ONE class  n ≡ r (mod b^K),
K = number of '0' steps. We then brute-force only r, r+b^K, r+2*b^K, ...

A '1' step requires  v ≢ 0 (mod b). When b = 2 that is the single residue
"v odd", so it folds into the class as a congruence too (giving the tight
classic behavior). For b > 2 it is a union of b-1 residues, so we don't
fold it -- the '0' steps still narrow the class, and full simulation per
candidate filters the multiply legality.

If gcd(m, b) != 1 (e.g. an even multiplier with base 2) the narrowing
degrades: P is no longer invertible mod b^k and the class stops collapsing.
We detect that up front and refuse rather than search blindly.
"""

import sys
import argparse
from math import gcd
from time import perf_counter


def combine(r1, k1, r2, k2, base):
    """Intersect n≡r1 (mod base^k1) with n≡r2 (mod base^k2). Nested prime-power
    moduli, so consistency check on the coarser one, then keep the finer."""
    if k1 == 0:
        return r2, k2
    if k2 == 0:
        return r1, k1
    lo = min(k1, k2)
    if (r1 - r2) % (base ** lo) != 0:
        return None
    return (r1, k1) if k1 >= k2 else (r2, k2)


def narrow_class(steps, base, mult, const):
    """Collapse the search to n ≡ r (mod base^k). Returns (r, k) or None."""
    P, Q, e = 1, 0, 0          # v0 = n  ->  (P*n + Q) / base^e
    r, k = 0, 0                # no constraint yet

    for ch in steps:
        if ch == '0':                          # divide: require v ≡ 0 (mod base)
            mod = base ** (e + 1)
            n0 = (pow(P % mod, -1, mod) * (-Q)) % mod
            c = combine(r, k, n0, e + 1, base)
            if c is None:
                return None
            r, k = c
            e += 1
        else:                                  # multiply: v -> mult*v + const
            if base == 2:                      # 'v not divisible' == single residue 'v odd'
                mod = base ** (e + 1)
                target = (base ** e - Q) % mod
                n0 = (pow(P % mod, -1, mod) * target) % mod
                c = combine(r, k, n0, e + 1, base)
                if c is None:
                    return None
                r, k = c
            Q = mult * Q + const * (base ** e)
            P = mult * P
    return r, k


def simulate(n, steps, base, mult, const):
    """Run the map. Return full trajectory, or None if any step is illegal
    (divide on a non-multiple, multiply on a multiple, or non-positive value)."""
    v = n
    traj = [v]
    for ch in steps:
        if ch == '0':
            if v % base != 0:
                return None
            v //= base
        else:
            if v % base == 0:
                return None
            v = mult * v + const
        if v < 1:
            return None
        traj.append(v)
    return traj


def find_start(steps, base, mult, const, threshold=4, timeout=10.0, max_candidates=500_000):
    """CRT-narrowed brute force. Returns dict with status and (if found) n, trajectory."""
    if gcd(mult, base) != 1:
        return {"status": "no_narrowing",
                "msg": f"gcd(multiplier={mult}, base={base}) = {gcd(mult, base)} != 1; "
                       "CRT narrowing does not apply (multiplier must be coprime to base)."}
    t0 = perf_counter()
    cls = narrow_class(steps, base, mult, const)
    if cls is None:
        return {"status": "impossible", "elapsed": perf_counter() - t0,
                "msg": "legality congruences conflict; no integer can follow this word."}
    r, k = cls
    M = base ** k

    n = r if r > 0 else M
    while n <= threshold:
        n += M

    tested = 0
    while perf_counter() - t0 < timeout and tested < max_candidates:
        tested += 1
        traj = simulate(n, steps, base, mult, const)
        if traj is not None and traj[0] > threshold and traj[-1] > threshold \
                and len(set(traj)) == len(traj):
            return {"status": "found", "n": n, "trajectory": traj,
                    "residue": r, "modulus": M, "modexp": k,
                    "tested": tested, "elapsed": perf_counter() - t0}
        n += M

    return {"status": "exhausted", "residue": r, "modulus": M, "modexp": k,
            "tested": tested, "elapsed": perf_counter() - t0,
            "msg": "no valid start within limits (word likely infeasible for this map, "
                   "e.g. an illegal multiply pattern)."}


def find_start_naive(steps, base, mult, const, threshold=4, timeout=10.0):
    """Plain scan over every integer > threshold (baseline)."""
    t0 = perf_counter()
    n, tested = threshold + 1, 0
    while perf_counter() - t0 < timeout:
        tested += 1
        traj = simulate(n, steps, base, mult, const)
        if traj is not None and traj[0] > threshold and traj[-1] > threshold \
                and len(set(traj)) == len(traj):
            return {"status": "found", "n": n, "tested": tested, "elapsed": perf_counter() - t0}
        n += 1
    return {"status": "timeout", "tested": tested, "elapsed": perf_counter() - t0}


def map_name(base, mult, const):
    sign = '+' if const >= 0 else '-'
    return f"v/{base} | {mult}v{sign}{abs(const)}"


def report(steps, base, mult, const, threshold=4, timeout=10.0, naive=True):
    print(f"map [{map_name(base, mult, const)}]   steps={steps!r} ({len(steps)} ops)")
    res = find_start(steps, base, mult, const, threshold, timeout)
    st = res["status"]

    if st == "no_narrowing":
        print(f"  -> {res['msg']}")
        print()
        return
    if st == "impossible":
        print(f"  -> impossible: {res['msg']}  [{res['elapsed']*1e3:.3f} ms]")
        print()
        return
    if st == "exhausted":
        print(f"  -> narrowed to n ≡ {res['residue']} (mod {base}^{res['modexp']} = {res['modulus']})")
        print(f"  -> {res['msg']}  (tested {res['tested']}, {res['elapsed']*1e3:.3f} ms)")
        print()
        return

    # found
    print(f"  -> narrowed to n ≡ {res['residue']} (mod {base}^{res['modexp']} = {res['modulus']})"
          f"   [{res['modulus']}x fewer candidates]")
    print(f"  CRT  : start = {res['n']}   "
          f"(tested {res['tested']} candidate(s), {res['elapsed']*1e3:.3f} ms)")
    print(f"         trajectory: {' -> '.join(map(str, res['trajectory']))}")
    if naive:
        nv = find_start_naive(steps, base, mult, const, threshold, timeout)
        if nv["status"] == "found":
            print(f"  naive: start = {nv['n']} in {nv['tested']} tries, {nv['elapsed']*1e3:.3f} ms")
        else:
            print(f"  naive: timed out after {nv['elapsed']:.2f}s ({nv['tested']} tries)")
    print()


def main():
    ap = argparse.ArgumentParser(description="Parametrized generalized-Collatz solver.")
    ap.add_argument("steps", nargs="*", help="step strings over {0,1}")
    ap.add_argument("--base", type=int, default=2)
    ap.add_argument("--mult", type=int, default=3)
    ap.add_argument("--const", type=int, default=1)
    ap.add_argument("--threshold", type=int, default=4)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--no-naive", action="store_true")
    args = ap.parse_args()

    valid = [s for s in args.steps if s and set(s) <= {"0", "1"}]
    if valid:
        for s in valid:
            report(s, args.base, args.mult, args.const,
                   args.threshold, args.timeout, naive=not args.no_naive)
        return

    print("(no step strings given -- running a demo across several maps)\n")
    demos = [
        # (base, mult, const, word)
        (2, 3, 1,  "10010100"),   # classic Collatz
        (2, 3, -1, "10"),         # 3x-1
        (2, 5, 7,  "10"),         # 5x+7
        (2, 5, 2,  "11"),         # even constant -> consecutive multiplies legal
        (2, 3, 1,  "11"),         # odd constant -> "11" infeasible
        (3, 2, 1,  "10"),         # base 3 (divide by 3 when v≡0 mod 3)
        (2, 4, 1,  "10"),         # even multiplier -> narrowing refuses
    ]
    for b, m, a, w in demos:
        report(w, b, m, a, args.threshold, args.timeout, naive=not args.no_naive)


if __name__ == "__main__":
    main()