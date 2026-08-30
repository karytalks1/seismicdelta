"""
IS 1893 (Part 1) : 2016 - equivalent static seismic analysis.

Purpose: compute design base shear and its storey-wise distribution by hand
(in code), so you can CROSS-CHECK what STAAD.Pro or ETABS reports.

That cross-check is the point. "I validated the software's base shear against
my own implementation of IS 1893 and they agreed within 2%" is a sentence
almost no candidate can say, and it proves you know what the software did
rather than that you can click buttons.

    python seismic.py

VERIFY EVERY COEFFICIENT BELOW against your own copy of IS 1893:2016 before
you use any output. Codes get amended. A number you did not check is a number
you cannot defend.
"""

from __future__ import annotations

from dataclasses import dataclass

# IS 1893:2016 Table 3 - Zone factor Z
ZONE_FACTOR = {"II": 0.10, "III": 0.16, "IV": 0.24, "V": 0.36}

# IS 1893:2016 Table 9 - Response reduction factor R
R_FACTOR = {"OMRF": 3.0, "SMRF": 5.0}

# Soil types for the design spectrum (Cl 6.4.2)
SOIL_TYPES = ("I", "II", "III")  # rocky/hard, medium, soft


def fundamental_period(height_m: float, base_dim_m: float | None = None) -> float:
    """Approximate fundamental period Ta, IS 1893:2016 Cl 7.6.2.

        RC moment-resisting frame WITHOUT brick infill:  Ta = 0.075 * h^0.75
        RC frame WITH brick infill panels:               Ta = 0.09 * h / sqrt(d)

    where h = height in m, d = base dimension in the direction considered.

    Pass base_dim_m to use the infill formula. Infill stiffens the frame, so
    the period drops, Sa/g usually rises, and base shear goes UP. Which
    formula you choose is an engineering decision you must be able to justify
    - not a default.
    """
    if base_dim_m is None:
        return 0.075 * (height_m ** 0.75)
    return 0.09 * height_m / (base_dim_m ** 0.5)


def spectral_acceleration(period_s: float, soil: str = "II") -> float:
    """Sa/g from the design spectrum, 5% damping. IS 1893:2016 Cl 6.4.2.

    Three branches per soil type: a rising ramp, a constant plateau, then a
    1/T decay. Short stiff buildings sit on the plateau; tall flexible ones
    fall down the decay, which is why a tall building attracts less seismic
    acceleration than people expect.
    """
    if soil not in SOIL_TYPES:
        raise ValueError(f"soil must be one of {SOIL_TYPES}, got {soil!r}")

    T = period_s

    if T <= 0:
        raise ValueError("period must be positive")

    if T < 0.10:
        return 1.0 + 15.0 * T

    if soil == "I":                       # rocky or hard soil
        return 2.50 if T <= 0.40 else 1.00 / T
    if soil == "II":                      # medium soil
        return 2.50 if T <= 0.55 else 1.36 / T
    return 2.50 if T <= 0.67 else 1.67 / T   # soft soil


def horizontal_seismic_coefficient(
    zone: str, period_s: float, soil: str = "II",
    importance: float = 1.0, r_factor: float = 5.0,
) -> float:
    """Ah = (Z/2) * (Sa/g) / (R/I).   IS 1893:2016 Cl 6.4.2

    The Z/2 is because Z is the ZONE PEAK GROUND ACCELERATION for the
    Maximum Considered Earthquake, and design is done for half of it (the
    Design Basis Earthquake). Interviewers ask this.

    R divides because a ductile frame is allowed to yield and dissipate
    energy, so it may be designed for less than elastic demand - provided
    the detailing (IS 13920) actually delivers that ductility. R = 5 with
    non-ductile detailing is unsafe and is a real failure mode.
    """
    z = ZONE_FACTOR[zone]
    sa_g = spectral_acceleration(period_s, soil)
    return (z / 2.0) * sa_g / (r_factor / importance)


@dataclass
class Storey:
    """One storey: seismic weight W (kN) and height h above base (m)."""

    name: str
    weight_kn: float
    height_m: float


def base_shear(seismic_weight_kn: float, ah: float) -> float:
    """Vb = Ah * W.   IS 1893:2016 Cl 7.6.1"""
    return ah * seismic_weight_kn


def storey_forces(storeys: list[Storey], vb_kn: float) -> list[tuple[str, float]]:
    """Distribute base shear up the building. IS 1893:2016 Cl 7.6.3

        Qi = Vb * (Wi * hi^2) / sum(Wj * hj^2)

    Note the SQUARE on height. It is an approximation of the first mode
    shape, which is roughly an inverted triangle in acceleration - so upper
    storeys attract disproportionate force. That h^2 is why the top storey
    of a six-storey building takes far more than one sixth of the shear,
    and it is a favourite interview question.
    """
    denom = sum(s.weight_kn * s.height_m ** 2 for s in storeys)
    return [
        (s.name, vb_kn * (s.weight_kn * s.height_m ** 2) / denom)
        for s in storeys
    ]


def analyse(
    storeys: list[Storey], zone: str, soil: str = "II",
    importance: float = 1.0, r_factor: float = 5.0,
    base_dim_m: float | None = None,
) -> dict:
    """Full equivalent-static run for one zone."""
    height = max(s.height_m for s in storeys)
    weight = sum(s.weight_kn for s in storeys)

    T = fundamental_period(height, base_dim_m)
    sa_g = spectral_acceleration(T, soil)
    ah = horizontal_seismic_coefficient(zone, T, soil, importance, r_factor)
    vb = base_shear(weight, ah)

    return {
        "zone": zone,
        "height_m": height,
        "seismic_weight_kn": weight,
        "period_s": T,
        "sa_by_g": sa_g,
        "ah": ah,
        "base_shear_kn": vb,
        "storey_forces": storey_forces(storeys, vb),
    }


# ---------------------------------------------------------------------------
# Worked example - the building in BUILD_SPEC.md. CHANGE THESE to your model.
# ---------------------------------------------------------------------------

def sample_building() -> list[Storey]:
    """G+5, 20 m x 15 m plan, 3.2 m storey height.

    Seismic weight per IS 1893 Cl 7.3.1 = full dead load + 25% of live load
    (for live load <= 3 kN/m^2). Roof carries no live load in seismic weight.

    REPLACE these weights with the values your own STAAD/ETABS model reports.
    These are order-of-magnitude placeholders so the script runs.
    """
    plan_area = 20.0 * 15.0                    # 300 m2
    typical = plan_area * 12.0                 # ~12 kN/m2 -> 3600 kN
    roof = plan_area * 9.0                     # lighter, no live load

    return [
        Storey("Storey 1", typical, 3.2),
        Storey("Storey 2", typical, 6.4),
        Storey("Storey 3", typical, 9.6),
        Storey("Storey 4", typical, 12.8),
        Storey("Storey 5", typical, 16.0),
        Storey("Roof", roof, 19.2),
    ]


def main() -> None:
    storeys = sample_building()

    print()
    print("=" * 74)
    print("  IS 1893:2016 EQUIVALENT STATIC ANALYSIS  -  Zone II vs Zone IV")
    print("=" * 74)

    results = {}
    for zone in ("II", "IV"):
        r = analyse(storeys, zone=zone, soil="II", importance=1.0, r_factor=5.0)
        results[zone] = r

        print()
        print(f"  ZONE {zone}")
        print(f"    Height h                 : {r['height_m']:.2f} m")
        print(f"    Seismic weight W         : {r['seismic_weight_kn']:,.0f} kN")
        print(f"    Fundamental period Ta    : {r['period_s']:.3f} s")
        print(f"    Spectral accel Sa/g      : {r['sa_by_g']:.3f}")
        print(f"    Zone factor Z            : {ZONE_FACTOR[zone]:.2f}")
        print(f"    Design coefficient Ah    : {r['ah']:.5f}")
        print(f"    BASE SHEAR Vb            : {r['base_shear_kn']:,.0f} kN")
        print()
        print(f"    {'Storey':<12}{'Height':>9}{'Force Qi':>12}{'Share':>9}")
        for (name, q), s in zip(r["storey_forces"], storeys):
            share = 100.0 * q / r["base_shear_kn"]
            print(f"    {name:<12}{s.height_m:>8.1f}m{q:>11.1f}kN{share:>8.1f}%")

    ii, iv = results["II"], results["IV"]
    ratio = iv["base_shear_kn"] / ii["base_shear_kn"]

    print()
    print("-" * 74)
    print(f"  Zone IV base shear is {ratio:.2f}x Zone II "
          f"({iv['base_shear_kn']:,.0f} kN vs {ii['base_shear_kn']:,.0f} kN)")
    print()
    print("  Why exactly this ratio: every other term in Ah is identical")
    print("  (same T, same Sa/g, same R, same I), so the ratio collapses to")
    print(f"  Z_IV / Z_II = {ZONE_FACTOR['IV']} / {ZONE_FACTOR['II']} = "
          f"{ZONE_FACTOR['IV']/ZONE_FACTOR['II']:.1f}.")
    print()
    print("  BUT: base shear ratio is NOT the steel ratio. Gravity load is")
    print("  unchanged, so gravity-governed members barely move. Finding out")
    print("  which members shift from gravity-governed to lateral-governed,")
    print("  and by how much, is the whole project.")
    print()


if __name__ == "__main__":
    main()
