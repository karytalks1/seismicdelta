"""
WALKTHROUGH - IS 1893:2016 seismic analysis, one step at a time.

    python walkthrough.py

Same functions as seismic.py, run slowly with every number shown and every
code clause named. Keep IS 1893 (Part 1):2016 open beside you if you have it.

Pen and paper. Work each stage before pressing Enter.
"""

from __future__ import annotations

from seismic import (
    ZONE_FACTOR,
    fundamental_period,
    horizontal_seismic_coefficient,
    spectral_acceleration,
    storey_forces,
    Storey,
)


def pause(msg="press Enter"):
    try:
        input(f"\n    [{msg}]")
    except EOFError:
        print()


def rule(t):
    print()
    print("=" * 78)
    print(f"  {t}")
    print("=" * 78)


# The building from BUILD_SPEC.md
PLAN_AREA = 20.0 * 15.0        # m2
STOREY_H = 3.2
N_STOREYS = 6
HEIGHT = round(STOREY_H * N_STOREYS, 3)


def main():
    rule("WHAT THIS PROJECT ACTUALLY IS")
    print("""
    Not a software project. A COMPARISON STUDY.

    Take one building. Design it twice - once as if it stood in Seismic
    Zone II (Delhi is Zone IV; much of south India is Zone II), once in
    Zone IV. Change NOTHING else. Then measure what the extra earthquake
    demand costs in steel, concrete, and rupees.

    The code exists to make that comparison trustworthy:

      seismic.py        computes the earthquake force by hand, in code,
                        so you can check what STAAD tells you
      frame2d.py        a finite element solver, so you can check the
                        deflections too
      generate_staad.py builds the STAAD models from one script, so the
                        two models differ ONLY in the zone factor

    That last point is the experiment design. If you clicked two models
    by hand you could never be sure a difference was real rather than a
    typo.
""")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 1 - SEISMIC WEIGHT  (IS 1893 Cl 7.3)")
    print("""
    An earthquake shakes MASS. So first: how heavy is the building?

    Seismic weight = full DEAD load + 25% of LIVE load
                     (25% applies when live load <= 3 kN/m2)
    Roof live load is NOT included - nobody is on the roof in an
    earthquake.

    Per floor, 300 m2:
""")
    slab_dl = 3.125          # 125 mm slab x 25 kN/m3
    finish = 1.0
    partition = 1.0
    live = 2.0

    dl_area = (slab_dl + finish + partition) * PLAN_AREA
    beams = 155 * 2.44       # 155 m of beam, 300x450 minus slab
    cols = 20 * 12.8         # 20 columns, 400x400 x 3.2 m
    walls = 70 * 12.65       # 70 m perimeter, 230 brick
    live_part = 0.25 * live * PLAN_AREA
    per_floor = dl_area + beams + cols + walls + live_part

    print(f"      slab + finish + partitions   {slab_dl + finish + partition:>5.3f} kN/m2 x 300 = {dl_area:>8.0f} kN")
    print(f"      beams   155 m x 2.44 kN/m                     = {beams:>8.0f} kN")
    print(f"      columns 20 x 12.8 kN                          = {cols:>8.0f} kN")
    print(f"      walls   70 m x 12.65 kN/m                     = {walls:>8.0f} kN")
    print(f"      25% of live load 0.25 x 2.0 x 300             = {live_part:>8.0f} kN")
    print(f"      {'':<46}  {'-'*8}")
    print(f"      per floor                                     = {per_floor:>8.0f} kN")
    print(f"\n    That is {per_floor / PLAN_AREA:.1f} kN/m2. Sanity check: a typical RC")
    print("    residential floor runs 10-13 kN/m2. We are inside that.")

    roof = per_floor * 0.85
    storeys = [Storey(f"Storey {i+1}", per_floor, (i + 1) * STOREY_H)
               for i in range(N_STOREYS - 1)]
    storeys.append(Storey("Roof", roof, HEIGHT))
    W = sum(s.weight_kn for s in storeys)
    print(f"\n    Total seismic weight W = {W:,.0f} kN  (roof taken lighter, no live load)")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 2 - FUNDAMENTAL PERIOD Ta  (IS 1893 Cl 7.6.2)")
    print("""
    How long does the building take to sway back and forth once?

    Tall and flexible = long period. Short and stiff = short period.
    This matters because the ground shakes at its own frequencies, and a
    building whose period matches gets hit hardest.

    For an RC moment-resisting frame WITHOUT brick infill:

        Ta = 0.075 x h^0.75          h in metres
""")
    T = fundamental_period(HEIGHT)
    print(f"    h  = {HEIGHT} m")
    print(f"    Ta = 0.075 x {HEIGHT}^0.75 = {T:.3f} s")
    print("""
    Roughly 0.7 seconds per sway. Feels about right for six storeys -
    a rule of thumb is 0.1 s per storey.

    NOTE: with brick infill the formula becomes 0.09h/sqrt(d). Infill
    STIFFENS the frame, so the period drops, Sa/g usually rises, and
    base shear goes UP. Which formula you pick is an engineering
    decision you must be able to justify - it is not a default.
""")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 3 - SPECTRAL ACCELERATION Sa/g  (IS 1893 Cl 6.4.2)")
    print("""
    The design spectrum answers: for a building of THIS period, how hard
    does the ground push, as a multiple of gravity?

    For medium soil (Type II), 5% damping:

        T < 0.10 s          Sa/g = 1 + 15T      rising ramp
        0.10 <= T <= 0.55   Sa/g = 2.50         the plateau
        0.55 < T <= 4.00    Sa/g = 1.36 / T     the decay
""")
    sa = spectral_acceleration(T, "II")
    print(f"    Our Ta = {T:.3f} s, which is past 0.55, so we are on the decay:")
    print(f"    Sa/g = 1.36 / {T:.3f} = {sa:.3f}")
    print("""
    We fell off the plateau. A stiffer, shorter building would sit at
    2.50 and attract MORE acceleration. This is the counter-intuitive
    bit: taller and more flexible often means less seismic force.
""")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 4 - DESIGN COEFFICIENT Ah  (IS 1893 Cl 6.4.2)")
    print("""
        Ah = (Z / 2) x (Sa/g) / (R / I)

    Four terms, and you will be asked about two of them:

    Z / 2   Z is the peak ground acceleration for the MAXIMUM CONSIDERED
            earthquake. We design for the DESIGN BASIS earthquake, taken
            as half of it - expecting the building to survive the MCE
            with damage but without collapse.

    R       Response reduction factor. A ductile frame yields and soaks
            up energy, so it may be designed for LESS than full elastic
            demand. R = 5 for a Special Moment Resisting Frame ASSUMES
            you detail it per IS 13920. Claim R = 5 and skip the
            detailing and the assumption is void - that is a real
            safety failure, not a paperwork one.

    I       Importance factor. 1.0 ordinary, 1.2 for hospitals etc.
""")
    for zone in ("II", "IV"):
        Z = ZONE_FACTOR[zone]
        ah = horizontal_seismic_coefficient(zone, T, "II", 1.0, 5.0)
        print(f"    Zone {zone:<3} Z = {Z:.2f}   Ah = ({Z}/2) x {sa:.3f} / (5/1) = {ah:.5f}")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 5 - BASE SHEAR Vb  (IS 1893 Cl 7.6.1)")
    print("""
        Vb = Ah x W

    The total horizontal force the earthquake applies at the base.
""")
    res = {}
    for zone in ("II", "IV"):
        ah = horizontal_seismic_coefficient(zone, T, "II", 1.0, 5.0)
        vb = ah * W
        res[zone] = vb
        print(f"    Zone {zone:<3} Vb = {ah:.5f} x {W:,.0f} = {vb:,.0f} kN")

    ratio = res["IV"] / res["II"]
    print(f"""
    RATIO = {ratio:.2f}

    Exactly 2.40, and you must be able to say why: every other term in
    Ah is identical between the two runs - same Ta, same Sa/g, same R,
    same I. So the ratio collapses to

        Z_IV / Z_II = 0.24 / 0.10 = 2.4

    If your STAAD run gives anything other than about 2.4, something
    ELSE changed between the two models. That is the check.
""")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 6 - STOREY FORCES  (IS 1893 Cl 7.6.3)")
    print("""
        Qi = Vb x (Wi x hi^2) / sum(Wj x hj^2)

    Note the SQUARE on height. It approximates the first mode shape -
    roughly an inverted triangle of acceleration - so upper storeys take
    disproportionate force.
""")
    forces = storey_forces(storeys, res["IV"])
    print(f"    Zone IV, Vb = {res['IV']:,.0f} kN\n")
    print(f"    {'STOREY':<12}{'HEIGHT':>8}{'FORCE':>10}{'SHARE':>8}")
    print("    " + "-" * 40)
    for (name, q), s in zip(forces, storeys):
        print(f"    {name:<12}{s.height_m:>7.1f}m{q:>9.1f}kN{q/res['IV']:>8.1%}")
    print(f"""
    The roof takes about {forces[-1][1]/res['IV']:.0%} of the total, not the 1/6 = 17%
    an even split would give. Storey 1 takes barely 1%.

    That h^2 is why the top of a building whips in an earthquake, and
    why you will be asked about it.
""")
    pause()

    # -----------------------------------------------------------------
    rule("STEP 7 - WHAT REMAINS, AND WHY")
    print("""
    You now have the FORCE. What you do not have yet is the EFFECT.

      frame2d.py         puts those storey forces on a 2D frame and
                         solves for deflection - are storey drifts
                         within the 0.004h limit of IS 1893 Cl 7.11?

      STAAD              does the same in 3D, and designs the members
                         to IS 456. You cross-check its base shear
                         against Step 5 above.

      hand design        one beam and one column to IS 456 by hand,
                         then explain why it differs from STAAD.
                         (It will. Rigid-zone offsets at the joints.)

      BBS + rates        turn the reinforcement into kilograms and
                         rupees, both zones. THAT is the answer to
                         the question the project asks.

    THE FINDING TO EXPECT:
        Base shear goes up 2.4x. Steel does NOT.
        Gravity load never changed, so gravity-governed beams barely
        move. Only members whose governing load combination FLIPPED
        from gravity to lateral change - mostly columns and the beams
        framing into them.

        Counting how many members actually changed is the result.

    NEXT: open seismic.py. Every function you just watched is in there,
    in the same order.
""")


if __name__ == "__main__":
    main()
