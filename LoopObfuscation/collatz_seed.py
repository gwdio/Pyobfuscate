"""
CRT-narrowed seed search for _collatz_forward's inverse operations.

_collatz_forward tracks:  v = (P*n + Q) / a^e
  0-step (v -> 2v):        P -> 2P, Q -> 2Q          no new constraint
  1-step (v -> (v-b)/a):   requires v ≡ b (mod a) and result odd
                           pins n mod a^(e+1) (divisibility) and mod 2 (parity)
                           then Q -> Q - b*a^e, e -> e+1
"""

from math import gcd


def _combine(r1, k1, r2, k2, base):
    """Intersect n≡r1 (mod base^k1) with n≡r2 (mod base^k2). Returns (r, k) or None."""
    if k1 == 0:
        return r2, k2
    if k2 == 0:
        return r1, k1
    lo = min(k1, k2)
    if (r1 - r2) % (base ** lo) != 0:
        return None
    return (r1, k1) if k1 >= k2 else (r2, k2)


def _combine_crt(r1, m1, r2, m2):
    """General CRT: intersect n≡r1 (mod m1) with n≡r2 (mod m2). Returns (r, lcm) or None."""
    g = gcd(m1, m2)
    if (r2 - r1) % g != 0:
        return None
    lcm = m1 * m2 // g
    # Extended GCD to find inverse of m1//g mod m2//g
    m2g = m2 // g
    inv = pow(m1 // g % m2g, -1, m2g)
    r = (r1 + m1 * ((r2 - r1) // g * inv % m2g)) % lcm
    return r, lcm


def narrow_class_inverse(steps, a, b):
    """
    Narrow n to a residue class for _collatz_forward's inverse ops.
    Returns (r, M) where n ≡ r (mod M), or None if impossible.
    """
    P, Q, e = 1, 0, 0  # v = (P*n + Q) / a^e
    r, M = 0, 1         # no constraint yet: n ≡ 0 (mod 1) = any

    for ch in steps:
        if ch == '0':
            P *= 2
            Q *= 2
        else:
            ae = a ** e
            ae1 = a ** (e + 1)

            # Divisibility constraint: P*n + Q ≡ b*ae (mod ae1)
            try:
                inv_P = pow(P % ae1, -1, ae1)
            except ValueError:
                return None
            n_div = (inv_P * ((b * ae - Q) % ae1)) % ae1

            # Combine divisibility with existing class
            c = _combine_crt(r, M, n_div, ae1)
            if c is None:
                return None
            r, M = c

            # Odd-result constraint: (P*n + Q - b*ae) / ae1 ≡ 1 (mod 2)
            # i.e. P*n + Q - b*ae ≡ ae1 (mod 2*ae1)
            mod2 = 2 * ae1
            try:
                inv_P2 = pow(P % mod2, -1, mod2)
            except ValueError:
                return None
            n_odd = (inv_P2 * ((b * ae + ae1 - Q) % mod2)) % mod2

            c = _combine_crt(r, M, n_odd, mod2)
            if c is None:
                return None
            r, M = c

            Q = Q - b * ae
            e += 1

    return r, M


def simulate_inverse(n, steps, a, b):
    """
    Simulate _collatz_forward's ops from n. Returns trajectory or None if any step fails
    or any value repeats (loop detected).
    """
    v = n
    traj = [n]
    seen = {n}
    for ch in steps:
        if ch == '1':
            if (v - b) % a != 0 or ((v - b) // a) % 2 == 0:
                return None
            v = (v - b) // a
        else:
            v = 2 * v
        if v < 1 or v in seen:
            return None
        seen.add(v)
        traj.append(v)
    return traj


def find_seed_crt(steps, a, b, rng, threshold=4, max_candidates=100):
    """
    CRT-narrowed search for a valid starting seed for the given step sequence.
    Returns (seed, endpoint) or None if not found.
    """
    if not steps:
        seed = rng.randint(threshold + 1, threshold + 50)
        return seed, seed

    cls = narrow_class_inverse(steps, a, b)
    if cls is None:
        return None
    r, M = cls

    start = r if r > threshold else r + M
    start += rng.randint(0, 20) * M

    for i in range(max_candidates):
        n = start + i * M
        traj = simulate_inverse(n, steps, a, b)
        if traj is not None and traj[0] > threshold and traj[-1] > threshold:
            return n, traj[-1]

    return None
