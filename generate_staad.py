"""
Generate STAAD.Pro input files (.std) for the SeismicDelta study.

    python generate_staad.py

Writes ZoneII.std, ZoneIV.std, and ZoneIV_SoftStorey.std into ./staad/

WHY GENERATE INSTEAD OF CLICK:
    Building a 140-joint, 306-member frame by hand in the GUI takes hours and
    you will make mistakes. Worse, the whole point of this project is that the
    three models must be IDENTICAL except for the one thing you are studying.
    Generating them from one script guarantees that. Click three models by hand
    and you will never be certain a difference is real rather than a typo.

    It is also a genuinely good interview answer: "I scripted the model
    generation so the only variable between runs was the zone factor."

HOW TO USE THE OUTPUT:
    1. Open STAAD.Pro
    2. File > Open, change file type to "STAAD Space (*.std)", pick ZoneII.std
    3. It opens as a full model. Check geometry looks right in the 3D view.
    4. Analyze > Run Analysis
    5. Repeat for the other two files.

VERIFY BEFORE TRUSTING:
    STAAD command syntax varies slightly between versions (CONNECT Edition vs
    older V8i). If a command is rejected, open the STAAD Editor (Edit > Edit
    Input Command File), fix that line, and note the change here. Treat this
    file as a strong starting point, not gospel - you are still the engineer.
"""

from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# BUILDING DEFINITION - change these, everything else follows
# ---------------------------------------------------------------------------
BAY_X = [5.0, 5.0, 5.0, 5.0]        # 4 bays -> 20 m
BAY_Z = [5.0, 5.0, 5.0]             # 3 bays -> 15 m
STOREY_HEIGHT = 3.2
N_STOREYS = 6                        # G+5

BEAM_D, BEAM_B = 0.45, 0.30          # YD, ZD in metres
COL_D, COL_B = 0.40, 0.40

FCK = 25                             # M25
SLAB_THK = 0.125

# Loads (kN/m2 and kN/m) - see BUILD_SPEC.md section 2
FLOOR_DL = 2.125                     # finish 1.0 + partition 1.0 (slab self via FLOAD below)
SLAB_SELF = SLAB_THK * 25            # 3.125
FLOOR_LL = 2.0
ROOF_LL = 1.5
WALL_UDL = 12.65                     # 230 brick, clear height 3.2 - 0.45


def grid_coords() -> tuple[list[float], list[float], list[float]]:
    """Cumulative coordinates along each axis."""
    xs = [0.0]
    for b in BAY_X:
        xs.append(xs[-1] + b)

    zs = [0.0]
    for b in BAY_Z:
        zs.append(zs[-1] + b)

    ys = [i * STOREY_HEIGHT for i in range(N_STOREYS + 1)]
    return xs, ys, zs


def build_model() -> dict:
    """Generate joints and members.

    Joint numbering: level-major, then x, then z. Keeping this deterministic
    matters - it is what lets the three .std files be directly comparable.
    """
    xs, ys, zs = grid_coords()

    joints: dict[tuple[int, int, int], int] = {}   # (ix, iy, iz) -> joint no
    coords: list[tuple[int, float, float, float]] = []

    n = 0
    for iy, y in enumerate(ys):
        for ix, x in enumerate(xs):
            for iz, z in enumerate(zs):
                n += 1
                joints[(ix, iy, iz)] = n
                coords.append((n, x, y, z))

    columns: list[tuple[int, int, int]] = []
    beams_x: list[tuple[int, int, int]] = []
    beams_z: list[tuple[int, int, int]] = []
    perimeter: list[int] = []

    m = 0

    # Columns: vertical between consecutive levels
    for iy in range(N_STOREYS):
        for ix in range(len(xs)):
            for iz in range(len(zs)):
                m += 1
                columns.append((m, joints[(ix, iy, iz)], joints[(ix, iy + 1, iz)]))

    # Beams along X, at every level above ground
    for iy in range(1, N_STOREYS + 1):
        for iz in range(len(zs)):
            for ix in range(len(xs) - 1):
                m += 1
                beams_x.append((m, joints[(ix, iy, iz)], joints[(ix + 1, iy, iz)]))
                if iz in (0, len(zs) - 1):
                    perimeter.append(m)

    # Beams along Z, at every level above ground
    for iy in range(1, N_STOREYS + 1):
        for ix in range(len(xs)):
            for iz in range(len(zs) - 1):
                m += 1
                beams_z.append((m, joints[(ix, iy, iz)], joints[(ix, iy, iz + 1)]))
                if ix in (0, len(xs) - 1):
                    perimeter.append(m)

    base_joints = [joints[(ix, 0, iz)] for ix in range(len(xs)) for iz in range(len(zs))]

    return {
        "coords": coords,
        "columns": columns,
        "beams_x": beams_x,
        "beams_z": beams_z,
        "perimeter": sorted(perimeter),
        "base_joints": base_joints,
        "total_height": round(ys[-1], 3),
        "xs": xs, "ys": ys, "zs": zs,
    }


def ranges(nums: list[int]) -> str:
    """Compress [1,2,3,7,8] into '1 TO 3 7 TO 8' for compact STAAD lists."""
    if not nums:
        return ""

    nums = sorted(nums)
    out: list[str] = []
    start = prev = nums[0]

    for v in nums[1:] + [None]:
        if v is not None and v == prev + 1:
            prev = v
            continue
        out.append(str(start) if start == prev else f"{start} TO {prev}")
        if v is not None:
            start = prev = v

    return " ".join(out)


def wrap(prefix: str, body: str, width: int = 70) -> str:
    """STAAD input lines have a length limit; continue with a trailing dash."""
    words = body.split()
    lines: list[str] = []
    cur = prefix

    for w in words:
        if len(cur) + len(w) + 1 > width:
            lines.append(cur + " -")
            cur = "  " + w
        else:
            cur = f"{cur} {w}" if cur.strip() else w

    lines.append(cur)
    return "\n".join(lines)


def write_std(model: dict, zone: float, title: str, soft_storey: bool = False) -> str:
    """Emit a complete STAAD input file."""
    L: list[str] = []
    a = L.append

    a("STAAD SPACE")
    a("START JOB INFORMATION")
    a(f"ENGINEER DATE {title}")
    a("END JOB INFORMATION")
    a("INPUT WIDTH 79")
    a("UNIT METER KN")

    a("JOINT COORDINATES")
    for n, x, y, z in model["coords"]:
        a(f"{n} {x:.3f} {y:.3f} {z:.3f};")

    a("MEMBER INCIDENCES")
    for m, j1, j2 in model["columns"] + model["beams_x"] + model["beams_z"]:
        a(f"{m} {j1} {j2};")

    a("DEFINE MATERIAL START")
    a("ISOTROPIC CONCRETE")
    a(f"E {5000 * (FCK ** 0.5) * 1000:.0f}")     # Ec = 5000*sqrt(fck) MPa -> kN/m2
    a("POISSON 0.17")
    a("DENSITY 25")
    a("ALPHA 1e-05")
    a("DAMP 0.05")
    a("TYPE CONCRETE")
    a(f"STRENGTH FCU {FCK * 1000}")
    a("END DEFINE MATERIAL")

    col_ids = [m for m, _, _ in model["columns"]]
    beam_ids = [m for m, _, _ in model["beams_x"] + model["beams_z"]]

    a("MEMBER PROPERTY INDIAN")
    a(wrap("", f"{ranges(col_ids)} PRIS YD {COL_D} ZD {COL_B}"))
    a(wrap("", f"{ranges(beam_ids)} PRIS YD {BEAM_D} ZD {BEAM_B}"))

    a("CONSTANTS")
    a("MATERIAL CONCRETE ALL")

    a("SUPPORTS")
    a(wrap("", f"{ranges(model['base_joints'])} FIXED"))

    # ---- IS 1893 seismic definition -------------------------------------
    # ZONE = zone factor Z, RF = response reduction, I = importance,
    # SS = soil (1 hard, 2 medium, 3 soft), ST = structure type, DM = damping
    a("DEFINE 1893 LOAD")
    a(f"ZONE {zone} RF 5 I 1 SS 2 ST 1 DM 0.05")
    a("SELFWEIGHT")
    a(wrap("MEMBER WEIGHT", f"{ranges(model['perimeter'])} UNI {WALL_UDL}"))
    # Seismic weight = full DL + 25% LL (IS 1893 Cl 7.3.1)
    a("FLOOR WEIGHT")
    a(f"YRANGE {STOREY_HEIGHT - 0.1} {model['total_height'] + 0.1} "
      f"FLOAD {SLAB_SELF + FLOOR_DL + 0.25 * FLOOR_LL} GY")

    # ---- Load cases ------------------------------------------------------
    a("LOAD 1 LOADTYPE Dead TITLE DEAD LOAD")
    a("SELFWEIGHT Y -1")
    a(wrap("MEMBER LOAD", f"{ranges(model['perimeter'])} UNI GY -{WALL_UDL}"))
    a("FLOOR LOAD")
    a(f"YRANGE {STOREY_HEIGHT - 0.1} {model['total_height'] + 0.1} "
      f"FLOAD -{SLAB_SELF + FLOOR_DL} GY")

    a("LOAD 2 LOADTYPE Live TITLE LIVE LOAD")
    a("FLOOR LOAD")
    a(f"YRANGE {STOREY_HEIGHT - 0.1} {model['total_height'] - 0.1} FLOAD -{FLOOR_LL} GY")
    a(f"YRANGE {model['total_height'] - 0.1} {model['total_height'] + 0.1} FLOAD -{ROOF_LL} GY")

    a("LOAD 3 LOADTYPE Seismic TITLE EQ +X")
    a("1893 LOAD X 1")
    a("LOAD 4 LOADTYPE Seismic TITLE EQ +Z")
    a("1893 LOAD Z 1")

    # ---- Combinations (IS 1893 Cl 6.3.1.2) -------------------------------
    combos = [
        (11, "1.5 (DL + LL)", [(1, 1.5), (2, 1.5)]),
        (12, "1.2 (DL + LL + EQX)", [(1, 1.2), (2, 1.2), (3, 1.2)]),
        (13, "1.2 (DL + LL - EQX)", [(1, 1.2), (2, 1.2), (3, -1.2)]),
        (14, "1.2 (DL + LL + EQZ)", [(1, 1.2), (2, 1.2), (4, 1.2)]),
        (15, "1.2 (DL + LL - EQZ)", [(1, 1.2), (2, 1.2), (4, -1.2)]),
        (16, "1.5 (DL + EQX)", [(1, 1.5), (3, 1.5)]),
        (17, "1.5 (DL - EQX)", [(1, 1.5), (3, -1.5)]),
        (18, "1.5 (DL + EQZ)", [(1, 1.5), (4, 1.5)]),
        (19, "1.5 (DL - EQZ)", [(1, 1.5), (4, -1.5)]),
        (20, "0.9DL + 1.5EQX", [(1, 0.9), (3, 1.5)]),
        (21, "0.9DL - 1.5EQX", [(1, 0.9), (3, -1.5)]),
        (22, "0.9DL + 1.5EQZ", [(1, 0.9), (4, 1.5)]),
        (23, "0.9DL - 1.5EQZ", [(1, 0.9), (4, -1.5)]),
    ]
    for num, name, parts in combos:
        a(f"LOAD COMB {num} {name}")
        a(" ".join(f"{lc} {f}" for lc, f in parts))

    a("PERFORM ANALYSIS PRINT STATICS CHECK")

    a("START CONCRETE DESIGN")
    a("CODE INDIAN")
    a(f"FYMAIN 500 ALL")
    a(f"FYSEC 500 ALL")
    a(f"FC {FCK * 1000} ALL")
    a("TRACK 2 ALL")
    a(wrap("DESIGN BEAM", ranges(beam_ids)))
    a(wrap("DESIGN COLUMN", ranges(col_ids)))
    a("CONCRETE TAKE OFF")
    a("END CONCRETE DESIGN")
    a("FINISH")

    if soft_storey:
        L.insert(4, "* SOFT STOREY CASE: model infill struts on storeys 2+ MANUALLY")
        L.insert(5, "* in the GUI (Geometry > Add Member) per IS 1893 Cl 7.9.2.2,")
        L.insert(6, "* leaving the ground storey bare. See BUILD_SPEC.md section 5b.")

    return "\n".join(L) + "\n"


def main() -> None:
    model = build_model()
    out = Path(__file__).parent / "staad"
    out.mkdir(exist_ok=True)

    files = [
        ("ZoneII.std", 0.10, "ZONE II", False),
        ("ZoneIV.std", 0.24, "ZONE IV", False),
        ("ZoneIV_SoftStorey.std", 0.24, "ZONE IV SOFT STOREY", True),
    ]

    for name, zone, title, soft in files:
        text = write_std(model, zone, title, soft)
        (out / name).write_text(text, encoding="utf-8")
        print(f"  wrote staad/{name:<26} Z = {zone}")

    print()
    print(f"  Joints        : {len(model['coords'])}")
    print(f"  Columns       : {len(model['columns'])}")
    print(f"  Beams         : {len(model['beams_x']) + len(model['beams_z'])}")
    print(f"  Perimeter beams (wall load): {len(model['perimeter'])}")
    print(f"  Total height  : {model['total_height']} m")
    print()
    print("  Open in STAAD.Pro: File > Open > file type 'STAAD Space (*.std)'")
    print("  Then Analyze > Run Analysis.")
    print()


if __name__ == "__main__":
    main()
