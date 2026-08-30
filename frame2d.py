"""
2D plane frame analysis by the direct stiffness method. Pure Python, no deps.

WHY THIS EXISTS
    Two reasons, and the second one matters more.

    1. It unblocks you. You can get storey drifts and member forces TODAY,
       before your Bentley licence arrives. If STAAD never comes through, this
       plus hand design is still a complete, defensible project.

    2. It makes the project genuinely uncommon. "I validated STAAD's output
       against my own finite element implementation" is a sentence almost no
       B.Tech candidate can say. Most students trust the software. You checked
       it. That is the difference between an operator and an engineer.

WHAT IT DOES
    Analyses ONE plane frame (a single grid line pulled out of the 3D
    building). Each node has 3 degrees of freedom: horizontal, vertical,
    rotation. Members are frame elements carrying axial force, shear, and
    moment.

WHAT IT DOES NOT DO - state these limits, do not hide them
    - 2D only. No torsion, no out-of-plane behaviour, no accidental
      eccentricity.
    - The frame carries a tributary share of the load, so results are
      approximate compared with a full 3D model.
    - No P-delta, no cracked-section stiffness modifiers.
    - Rigid zones at joints are ignored, so moments come out at member
      centrelines. This is exactly why your numbers will read HIGHER than
      STAAD's, and being able to say that is worth more than matching.

    python frame2d.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isclose


# ---------------------------------------------------------------------------
# Linear algebra - Gaussian elimination with partial pivoting
# ---------------------------------------------------------------------------

def solve(A: list[list[float]], b: list[float]) -> list[float]:
    """Solve A x = b. Partial pivoting for numerical stability.

    O(n^3). At ~105 DOF that is about a million operations - instant. A real
    solver would exploit the fact that a stiffness matrix is symmetric,
    positive definite and banded (Cholesky, or a skyline solver), which is
    what makes commercial packages fast on 100,000-DOF models. Worth saying
    if asked how you would scale this.
    """
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]

    for col in range(n):
        # Pivot: pick the largest remaining entry in this column.
        piv = max(range(col, n), key=lambda r: abs(M[r][col]))
        if isclose(M[piv][col], 0.0, abs_tol=1e-12):
            raise ValueError(
                f"Singular stiffness matrix at DOF {col}. Usually means the "
                f"structure is a mechanism - check supports and connectivity."
            )
        M[col], M[piv] = M[piv], M[col]

        inv = 1.0 / M[col][col]
        for r in range(col + 1, n):
            f = M[r][col] * inv
            if f:
                for c in range(col, n + 1):
                    M[r][c] -= f * M[col][c]

    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][c] * x[c] for c in range(r + 1, n))
        x[r] = s / M[r][r]
    return x


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

@dataclass
class Node:
    id: int
    x: float
    y: float
    fixed: bool = False


@dataclass
class Member:
    id: int
    n1: int
    n2: int
    E: float          # kN/m2
    A: float          # m2
    I: float          # m4
    udl: float = 0.0  # kN/m, downward positive (gravity)
    kind: str = "beam"


@dataclass
class Frame:
    nodes: list[Node] = field(default_factory=list)
    members: list[Member] = field(default_factory=list)
    loads: dict[int, tuple[float, float, float]] = field(default_factory=dict)

    def ndof(self) -> int:
        return 3 * len(self.nodes)

    def node(self, nid: int) -> Node:
        return self.nodes[nid]


def member_geometry(f: Frame, m: Member) -> tuple[float, float, float]:
    """Return length, cos, sin of the member axis."""
    a, b = f.node(m.n1), f.node(m.n2)
    dx, dy = b.x - a.x, b.y - a.y
    L = (dx * dx + dy * dy) ** 0.5
    return L, dx / L, dy / L


def local_stiffness(E: float, A: float, I: float, L: float) -> list[list[float]]:
    """Standard 6x6 plane frame element stiffness, local axes.

    DOF order: [u1, v1, theta1, u2, v2, theta2]
    Axial terms uncouple from bending - that is the Euler-Bernoulli assumption
    (plane sections remain plane, shear deformation neglected). Fine for the
    slender members here; a deep transfer girder would need Timoshenko.
    """
    ea = E * A / L
    z = E * I / L
    z2 = 6.0 * E * I / (L * L)
    z3 = 12.0 * E * I / (L ** 3)

    return [
        [ ea,   0,    0,    -ea,   0,    0  ],
        [  0,  z3,   z2,      0, -z3,   z2  ],
        [  0,  z2, 4*z,       0, -z2, 2*z   ],
        [-ea,   0,    0,     ea,   0,    0  ],
        [  0, -z3,  -z2,      0,  z3,  -z2  ],
        [  0,  z2, 2*z,       0, -z2, 4*z   ],
    ]


def transform(c: float, s: float) -> list[list[float]]:
    """Local-to-global rotation matrix for a plane frame element."""
    return [
        [ c, s, 0,  0, 0, 0],
        [-s, c, 0,  0, 0, 0],
        [ 0, 0, 1,  0, 0, 0],
        [ 0, 0, 0,  c, s, 0],
        [ 0, 0, 0, -s, c, 0],
        [ 0, 0, 0,  0, 0, 1],
    ]


def matmul(A, B):
    n, k, m = len(A), len(B), len(B[0])
    return [[sum(A[i][p] * B[p][j] for p in range(k)) for j in range(m)] for i in range(n)]


def transpose(A):
    return [list(r) for r in zip(*A)]


def matvec(A, v):
    return [sum(a * x for a, x in zip(row, v)) for row in A]


def fixed_end_forces(w: float, L: float) -> list[float]:
    """Fixed-end forces for a downward UDL w on a beam, LOCAL axes.

        shear at each end = wL/2, moment = wL^2/12 (opposing signs)

    These are the reactions a fully fixed beam would develop. We apply their
    NEGATIVE as equivalent nodal loads, solve, then add them back when
    recovering member forces. Standard, and worth being able to explain -
    it is how distributed loads enter a nodal-DOF formulation at all.
    """
    return [0.0, -w * L / 2.0, -w * L * L / 12.0,
            0.0, -w * L / 2.0,  w * L * L / 12.0]


def analyse(f: Frame) -> dict:
    """Assemble, apply boundary conditions, solve, recover member forces."""
    n = f.ndof()
    K = [[0.0] * n for _ in range(n)]
    F = [0.0] * n

    # Nodal loads
    for nid, (fx, fy, mz) in f.loads.items():
        F[3 * nid] += fx
        F[3 * nid + 1] += fy
        F[3 * nid + 2] += mz

    member_cache = []

    for m in f.members:
        L, c, s = member_geometry(f, m)
        kl = local_stiffness(m.E, m.A, m.I, L)
        T = transform(c, s)
        kg = matmul(matmul(transpose(T), kl), T)

        dofs = [3 * m.n1, 3 * m.n1 + 1, 3 * m.n1 + 2,
                3 * m.n2, 3 * m.n2 + 1, 3 * m.n2 + 2]

        for i, di in enumerate(dofs):
            for j, dj in enumerate(dofs):
                K[di][dj] += kg[i][j]

        fef_local = fixed_end_forces(m.udl, L) if m.udl else [0.0] * 6
        if m.udl:
            # Equivalent nodal loads = -(T^T * fixed end forces)
            fef_global = matvec(transpose(T), fef_local)
            for i, di in enumerate(dofs):
                F[di] -= fef_global[i]

        member_cache.append((m, L, c, s, kl, T, dofs, fef_local))

    # Boundary conditions: penalty-free approach - zero the row/col, put 1 on
    # the diagonal. Simple and exact for fully fixed supports.
    for nd in f.nodes:
        if nd.fixed:
            for d in (3 * nd.id, 3 * nd.id + 1, 3 * nd.id + 2):
                for j in range(n):
                    K[d][j] = 0.0
                    K[j][d] = 0.0
                K[d][d] = 1.0
                F[d] = 0.0

    U = solve(K, F)

    # Recover member end forces in local axes
    forces = {}
    for m, L, c, s, kl, T, dofs, fef in member_cache:
        ug = [U[d] for d in dofs]
        ul = matvec(T, ug)
        fl = matvec(kl, ul)
        fl = [a + b for a, b in zip(fl, fef)]
        forces[m.id] = {
            "axial": -fl[0], "shear_i": fl[1], "moment_i": fl[2],
            "shear_j": fl[4], "moment_j": fl[5], "length": L,
        }

    return {"U": U, "forces": forces}


# ---------------------------------------------------------------------------
# Build the SeismicDelta frame
# ---------------------------------------------------------------------------

def build_frame(
    bays: list[float], storey_h: float, n_storeys: int,
    beam_udl: float, lateral: list[float],
    col_b: float = 0.40, col_d: float = 0.40,
    beam_b: float = 0.30, beam_d: float = 0.45,
    fck: float = 25.0,
) -> Frame:
    """One plane frame: len(bays)+1 columns, n_storeys levels.

    lateral[i] = horizontal force applied at level i+1 (kN), from IS 1893.
    beam_udl   = gravity UDL on beams (kN/m), tributary share.
    """
    E = 5000.0 * (fck ** 0.5) * 1000.0        # kN/m2

    A_col, I_col = col_b * col_d, col_b * col_d ** 3 / 12.0
    A_bm, I_bm = beam_b * beam_d, beam_b * beam_d ** 3 / 12.0

    xs = [0.0]
    for b in bays:
        xs.append(xs[-1] + b)

    f = Frame()
    nid = 0
    grid: dict[tuple[int, int], int] = {}

    for lvl in range(n_storeys + 1):
        for ix, x in enumerate(xs):
            f.nodes.append(Node(nid, x, lvl * storey_h, fixed=(lvl == 0)))
            grid[(ix, lvl)] = nid
            nid += 1

    mid = 0
    for lvl in range(n_storeys):                     # columns
        for ix in range(len(xs)):
            f.members.append(Member(mid, grid[(ix, lvl)], grid[(ix, lvl + 1)],
                                    E, A_col, I_col, 0.0, "column"))
            mid += 1

    for lvl in range(1, n_storeys + 1):              # beams
        for ix in range(len(xs) - 1):
            f.members.append(Member(mid, grid[(ix, lvl)], grid[(ix + 1, lvl)],
                                    E, A_bm, I_bm, beam_udl, "beam"))
            mid += 1

    # Lateral force at each level, split equally across that level's nodes.
    for lvl in range(1, n_storeys + 1):
        q = lateral[lvl - 1] / len(xs)
        for ix in range(len(xs)):
            f.loads[grid[(ix, lvl)]] = (q, 0.0, 0.0)

    f.grid = grid          # type: ignore[attr-defined]
    f.n_cols = len(xs)     # type: ignore[attr-defined]
    return f


def storey_drifts(f: Frame, U: list[float], storey_h: float, n_storeys: int) -> list[dict]:
    """Horizontal displacement per level, and inter-storey drift."""
    grid = f.grid          # type: ignore[attr-defined]
    out = []
    prev = 0.0

    for lvl in range(1, n_storeys + 1):
        nid = grid[(0, lvl)]
        disp = U[3 * nid] * 1000.0                   # m -> mm
        drift = disp - prev
        out.append({
            "level": lvl,
            "disp_mm": disp,
            "drift_mm": drift,
            "ratio": drift / (storey_h * 1000.0),
            "limit_ok": drift <= 0.004 * storey_h * 1000.0,
        })
        prev = disp

    return out


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _validate() -> None:
    """Check the solver against results you can compute in your head."""

    # 1. Cantilever, tip point load. delta = P L^3 / (3 E I)
    E, I, A, L, P = 2.0e8, 1.0e-4, 1.0e-2, 2.0, 10.0
    f = Frame()
    f.nodes = [Node(0, 0.0, 0.0, fixed=True), Node(1, 0.0, L)]
    f.members = [Member(0, 0, 1, E, A, I)]
    f.loads = {1: (P, 0.0, 0.0)}
    U = analyse(f)["U"]
    expected = P * L ** 3 / (3.0 * E * I)
    assert abs(U[3] - expected) / expected < 1e-6, (U[3], expected)

    # 2. Fixed-fixed beam under UDL: end moment = wL^2/12
    w, Lb = 20.0, 6.0
    f = Frame()
    f.nodes = [Node(0, 0.0, 0.0, fixed=True), Node(1, Lb, 0.0, fixed=True)]
    f.members = [Member(0, 0, 1, E, A, I, udl=w)]
    r = analyse(f)
    m_i = abs(r["forces"][0]["moment_i"])
    assert abs(m_i - w * Lb ** 2 / 12.0) < 1e-6, m_i

    print("  validation: cantilever PL^3/3EI  OK")
    print("  validation: fixed-fixed wL^2/12  OK")


def main() -> None:
    _validate()

    # Lateral forces from seismic.py. REPLACE with your own run.
    # One plane frame of four carries roughly a quarter of the base shear.
    from seismic import analyse as seismic_analyse, sample_building

    storeys = sample_building()
    n_frames = 4          # number of parallel frames in this direction

    print()
    print("=" * 78)
    print("  2D PLANE FRAME  -  one interior frame, tributary loads")
    print("=" * 78)

    for zone in ("II", "IV"):
        s = seismic_analyse(storeys, zone=zone, soil="II", r_factor=5.0)
        lateral = [q / n_frames for _, q in s["storey_forces"]]

        fr = build_frame(
            bays=[5.0, 5.0, 5.0, 5.0], storey_h=3.2, n_storeys=6,
            beam_udl=25.0,            # tributary gravity UDL, kN/m
            lateral=lateral,
        )
        res = analyse(fr)
        drifts = storey_drifts(fr, res["U"], 3.2, 6)

        print()
        print(f"  ZONE {zone}   frame base shear = {sum(lateral):,.1f} kN")
        print(f"    {'Level':<7}{'Disp mm':>10}{'Drift mm':>11}{'Ratio':>10}{'Check':>8}")
        for d in drifts:
            flag = "OK" if d["limit_ok"] else "FAIL"
            print(f"    {d['level']:<7}{d['disp_mm']:>10.2f}{d['drift_mm']:>11.2f}"
                  f"{d['ratio']:>10.5f}{flag:>8}")

        worst = max(drifts, key=lambda d: d["drift_mm"])
        print(f"    Max inter-storey drift {worst['drift_mm']:.2f} mm at level "
              f"{worst['level']}   (limit {0.004 * 3200:.1f} mm)")

    print()
    print("  Compare these against STAAD. Expect YOUR moments to read higher:")
    print("  no rigid-zone offsets here, so spans are centre-to-centre.")
    print()


if __name__ == "__main__":
    main()
