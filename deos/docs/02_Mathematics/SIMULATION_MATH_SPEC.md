# Specification: Simulation Mathematics Reference (EESS-0201)

| Metadata | Value |
| :--- | :--- |
| **Document ID** | EESS-0201 |
| **Semantic Version** | v0.3.0 |
| **Status** | Approved |
| **Dependencies** | EESS-0101 |

---

## 1. Fixed-Point Arithmetic Specification (`Q32.32`)

### REQ-MATH-001: Representation Format
All continuous variables (positions, energy levels, utility scores, probabilities) must be stored as signed 64-bit integers (`int64_t`), where:
- Upper 32 bits represent the signed integer component.
- Lower 32 bits represent the fractional component ($1 / 2^{32} pprox 2.328 	imes 10^{-10}$ precision).

```
 63                                32 31                                 0
┌────────────────────────────────────┬────────────────────────────────────┐
│      Signed Integer (32-bit)       │       Fractional (32-bit)          │
└────────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Fundamental Simulation Equations

### REQ-MATH-002: The Flux Equation
The rate of energy/information flux $\Phi_{i,j}$ from entity $i$ to node $j$ is governed by utility gradient difference and conductivity $lpha$:

$$\Phi_{i,j} = lpha \cdot E_i \cdot rac{1}{1 + e^{-k \cdot (U_j - U_i)}}$$

Where $e^x$ is computed using a deterministic 16-entry lookup table with fixed-point linear interpolation.

### REQ-MATH-003: Utility Scoring Function
The utility score $U(a)$ for an agent evaluating action choice $a$ is computed as:

$$U(a) = \sum_{k=0}^{N-1} w_k \cdot f_k(S)$$

Where $w_k$ is the weight of internal need $k$, and $f_k(S)$ is the state satisfaction curve evaluated in `Q32.32`.

---

## 3. Pseudo-Random Number Generator (PRNG)

### REQ-MATH-004: PCG64 / Xoshiro256** Implementation
Floating-point `rand()` functions are strictly banned. System workers must utilize **PCG64** initialized with deterministic per-system seeds derived from the master world seed:

$$	ext{Seed}_{system} = 	ext{BLAKE3}(	ext{MasterSeed} \parallel 	ext{SystemID} \parallel 	ext{Tick})$$

---

## 4. Revision History
| Version | Date | Description | Author |
| :--- | :--- | :--- | :--- |
| v0.3.0 | 2026-07-20 | Fixed-point math and flux specs | EE Arch Team |
