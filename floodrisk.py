"""
Uttarakhand flood plain zoning and district flood risk.

    python floodrisk.py

Two things happen here.

FIRST, the statutory zoning line is drawn. The Model Bill for Flood Plain
Zoning (CWC, 1975) sets out land-use zones by flood return period, and
Uttarakhand is one of only four states that ever enacted it - the Uttarakhand
Flood Plain Zoning Act, 2012. Sections 1 and 2 compute those zone widths from
the Q25/Q50/Q100 discharges in hydrology.py and Manning normal depth.

SECOND, that line is tested against the event that actually happens here.
Section 3 models a moraine-dam breach with a published empirical dam-break
relation, validates it against the Chorabari breach of 17 June 2013, and then
compares the corridor it produces against the statutory Q100 corridor. The gap
between those two widths is the finding of this module.

Section 4 ranks the 13 districts on a Hazard x Exposure x Vulnerability index,
the standard UNDRR / NDMA decomposition.

LIMITATIONS - read these before quoting any number.

  * There is no gauged flood frequency analysis behind this. Design floods come
    from a regional relation calibrated on ONE observed datum. See hydrology.py.
  * Channel geometry is typical-value, not surveyed. Widths are indicative.
  * Exposure assumes population spreads evenly across buildable land. Real
    settlement concentrates on flat ground even harder than that, so the
    corridor exposure computed here is more likely under- than over-stated.
  * The risk index is a RANKING tool. The absolute score has no physical unit
    and no meaning outside this comparison set.
  * A real zoning exercise requires surveyed cross-sections, a gauged flood
    series, and a field-mapped geomorphic envelope. This is the screening pass
    that tells you where to spend that survey money.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import uk_data as D
import hydrology as H

# ---------------------------------------------------------------------------
# Model Bill for Flood Plain Zoning, 1975 - land use zones
# ---------------------------------------------------------------------------

# The Bill zones land by flood frequency and restricts use accordingly. The
# return periods below are the conventional bands used in Indian practice.
ZONES = (
    ("A", 25, "PROHIBITIVE  no permanent structure, no fill, no obstruction"),
    ("B", 50, "RESTRICTIVE  agriculture, parks, flood-proofed low-value use only"),
    ("C", 100, "REGULATED    raised plinth, no critical or emergency facility"),
)

# Empirical peak outflow from a breached moraine-dammed lake.
#
#     Qp = 0.72 * V^0.53        Evans (1986), V in m3, Qp in m3/s
#
# Derived from observed moraine-dam failures. It predicts the WATER discharge.
# A Himalayan outburst does not stay water: it entrains moraine, till and
# channel boulders and arrives as a debris flow with a much larger bulk volume.
EVANS_A, EVANS_B = 0.72, 0.53

# Debris bulking factor [E]. Sediment concentrations of 40-60% by volume are
# routine in Himalayan debris flows, which multiplies the water discharge by
# roughly 1.7-2.5x. 2.0 is taken here and TESTED against Chorabari in section 3.
DEBRIS_BULKING = 2.0

# Risk index weights [E]. Chosen, not derived. Changing them changes the
# ranking, so main() reports how much.
W_HAZARD = (0.40, 0.35, 0.25)        # stream power, GLOF exposure, flashiness
W_EXPOSURE = (0.50, 0.50)            # corridor population, corridor crowding
W_VULNERABILITY = (0.40, 0.30, 0.30)  # building typology, flashiness, seismic

SEISMIC_WEIGHT = {"IV": 0.60, "IV/V": 0.80, "V": 1.00}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Lower bound for a normalised score. Plain min-max maps the lowest district to
# exactly zero, and zero inside a geometric mean annihilates the whole product -
# Udham Singh Nagar came out at 0.4 out of 100 on an early run purely because it
# held the minimum on one component. That is a scaling artifact, not a finding:
# the Terai floods, repeatedly and destructively. Scoring lowest in a set of 13
# means "least of these", never "none", so the floor says so.
SCORE_FLOOR = 0.05


def normalise(values: dict[str, float]) -> dict[str, float]:
    """Min-max scale to SCORE_FLOOR..1. A flat input maps mid-range."""
    lo, hi = min(values.values()), max(values.values())
    if hi - lo < 1e-12:
        return {k: 0.5 for k in values}
    span = 1.0 - SCORE_FLOOR
    return {k: SCORE_FLOOR + span * (v - lo) / (hi - lo) for k, v in values.items()}


def breach_peak_cumec(volume_m3: float, bulking: float = DEBRIS_BULKING) -> float:
    """Peak discharge from a moraine-dam breach, including debris bulking."""
    return EVANS_A * (volume_m3 ** EVANS_B) * bulking


# ---------------------------------------------------------------------------
# 1. Zoning widths
# ---------------------------------------------------------------------------

@dataclass
class ZoneWidths:
    reach: D.Reach
    widths: dict[str, float]     # zone letter -> cumulative top width, m
    q: dict[str, float]          # zone letter -> discharge, m3/s


def zone_widths(reach: D.Reach, node: H.NodeResult) -> ZoneWidths:
    widths, qs = {}, {}
    for letter, T, _ in ZONES:
        q = H.design_flood(node.total_area_km2, T, node.cv)
        qs[letter] = q
        widths[letter] = H.flow_state(q, reach).top_width_m
    return ZoneWidths(reach, widths, qs)


# ---------------------------------------------------------------------------
# 2. District risk index
# ---------------------------------------------------------------------------

@dataclass
class DistrictRisk:
    district: D.District
    reach: D.Reach
    corridor_land_km2: float
    corridor_population: int
    corridor_density: float
    unit_power: float
    hazard: float
    exposure: float
    vulnerability: float
    risk: float


def governing_reach(district: D.District) -> D.Reach:
    """The reach that represents a district's flood hazard.

    Where a district has several, take the one with the highest unit stream
    power at Q100 - the worst case, which is what a zoning rule has to survive.
    """
    candidates = [r for r in D.REACHES if r.district == district.name]
    if not candidates:
        raise ValueError(f"no reach mapped to district {district.name!r}")
    nodes = _NODES
    return max(
        candidates,
        key=lambda r: H.flow_state(
            H.design_flood(nodes[r.node].total_area_km2, 100, nodes[r.node].cv), r
        ).unit_stream_power_w_per_m2,
    )


_NODES = H.nodes()


def assess() -> list[DistrictRisk]:
    nodes = _NODES

    raw: dict[str, dict[str, float]] = {}
    reach_of: dict[str, D.Reach] = {}
    land: dict[str, float] = {}
    pop: dict[str, int] = {}

    for d in D.DISTRICTS:
        r = governing_reach(d)
        reach_of[d.name] = r
        n = nodes[r.node]
        st = H.flow_state(H.design_flood(n.total_area_km2, 100, n.cv), r)

        # "Corridor" here is the GEOMORPHIC river corridor - valley floor plus
        # the terraces and fans above it - not the Q100 inundation line. It is
        # the wider figure, and deliberately so: section 3 shows the Q100 line
        # is the wrong envelope for a Himalayan outburst, and the terraces are
        # exactly the ground such an event reoccupies. Do not read these
        # numbers as "people inside the 100-year floodplain"; they are people
        # living on the landform the river built and can take back.
        share = D.FLOODPLAIN_SHARE_OF_HABITABLE[d.terrain]
        habitable = d.area_km2 * d.habitable_fraction
        corridor_land = habitable * share
        # Uniform spread over buildable land. Settlement actually concentrates
        # on flat ground harder than this, so treat as a LOWER bound.
        corridor_pop = int(round(d.population_2011 * share))

        land[d.name] = corridor_land
        pop[d.name] = corridor_pop

        raw[d.name] = {
            "power": math.log10(max(st.unit_stream_power_w_per_m2, 1.0)),
            "glof": math.sqrt(d.glacier_km2),
            "flash": math.log10(r.bed_slope * 1e4),
            "corr_pop": float(corridor_pop),
            "corr_density": corridor_pop / corridor_land if corridor_land > 0 else 0.0,
            "typology": 1.0 - d.urban_fraction,
            "seismic": SEISMIC_WEIGHT[d.seismic_zone],
            "unit_power": st.unit_stream_power_w_per_m2,
        }

    n_ = {k: normalise({d: raw[d][k] for d in raw})
          for k in ("power", "glof", "flash", "corr_pop", "corr_density",
                    "typology", "seismic")}

    out: list[DistrictRisk] = []
    for d in D.DISTRICTS:
        name = d.name
        hz = (W_HAZARD[0] * n_["power"][name]
              + W_HAZARD[1] * n_["glof"][name]
              + W_HAZARD[2] * n_["flash"][name])
        ex = (W_EXPOSURE[0] * n_["corr_pop"][name]
              + W_EXPOSURE[1] * n_["corr_density"][name])
        vu = (W_VULNERABILITY[0] * n_["typology"][name]
              + W_VULNERABILITY[1] * n_["flash"][name]
              + W_VULNERABILITY[2] * n_["seismic"][name])

        # Geometric mean. Risk is a PRODUCT of the three - a hazard with no one
        # exposed to it is not a risk - so a district cannot score well on two
        # terms and buy its way out of the third.
        risk = 100.0 * (max(hz, 1e-6) * max(ex, 1e-6) * max(vu, 1e-6)) ** (1.0 / 3.0)

        out.append(DistrictRisk(
            district=d, reach=reach_of[name],
            corridor_land_km2=land[name], corridor_population=pop[name],
            corridor_density=raw[name]["corr_density"],
            unit_power=raw[name]["unit_power"],
            hazard=hz, exposure=ex, vulnerability=vu, risk=risk,
        ))

    out.sort(key=lambda x: x.risk, reverse=True)
    return out


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _rule(char: str = "=", n: int = 78) -> str:
    return char * n


def main() -> None:
    nodes = _NODES

    print()
    print(_rule())
    print("  UTTARAKHAND - FLOOD PLAIN ZONING AND DISTRICT RISK")
    print(_rule())

    # -- 1. statutory zones ------------------------------------------------
    print()
    print(_rule("-"))
    print("  1. STATUTORY ZONE WIDTHS  -  Model Bill 1975 / UK FPZ Act 2012")
    print(_rule("-"))
    print()
    for letter, T, desc in ZONES:
        print(f"    Zone {letter}   {T:>3}-year flood   {desc}")
    print()
    print("    Cumulative inundation top width at each zone boundary, from")
    print("    Manning normal depth:")
    print()
    print(f"    {'Reach':<28}{'Zone A':>10}{'Zone B':>10}{'Zone C':>10}{'A->C':>9}")
    print(f"    {'':<28}{'Q25, m':>10}{'Q50, m':>10}{'Q100, m':>10}{'growth':>9}")
    zws: dict[str, ZoneWidths] = {}
    for r in D.REACHES:
        zw = zone_widths(r, nodes[r.node])
        zws[r.key] = zw
        a, b, c = zw.widths["A"], zw.widths["B"], zw.widths["C"]
        print(f"    {r.label:<28}{a:>10.0f}{b:>10.0f}{c:>10.0f}{c / a:>8.2f}x")

    gorge = [zws[k] for k in ("kedarnath", "joshimath", "jauljibi", "mandakini")]
    plain = [zws[k] for k in ("haridwar", "khatima", "banbasa")]
    g_avg = sum(z.widths["C"] / z.widths["A"] for z in gorge) / len(gorge)
    p_avg = sum(z.widths["C"] / z.widths["A"] for z in plain) / len(plain)
    print()
    print(f"    Confined Himalayan reaches widen {g_avg:.2f}x from Zone A to Zone C.")
    print(f"    Terai reaches widen {p_avg:.2f}x.")
    print()
    print("    That difference is the whole argument. The Model Bill manages risk")
    print("    by mapping a WIDER line for a rarer flood, and on an alluvial plain")
    print("    that works - the water spreads, so the extra discharge shows up as")
    print("    extra area and the zone boundary genuinely moves.")
    print()
    print("    A bedrock gorge cannot spread. Extra discharge goes into DEPTH and")
    print("    VELOCITY instead, so the line barely moves while the force inside it")
    print("    climbs. Zone A and Zone C end up being very nearly the same ground,")
    print("    and a plot reclassified from A to C has not become materially safer -")
    print("    it has only become legal to build on.")
    print()
    print("    One caveat on the Terai figures: bank overtopping is a threshold, so")
    print("    a reach jumps in width at whichever return period first exceeds")
    print("    bank-full. Where that jump falls between Q50 and Q100 is sensitive")
    print("    to the assumed bank depth. The gorge-versus-plain contrast is robust;")
    print("    the precise multiplier for any one plains reach is not.")

    # -- 2. stream power vs zone -------------------------------------------
    print()
    print(_rule("-"))
    print("  2. WHAT THE ZONE MEANS PHYSICALLY")
    print(_rule("-"))
    print()
    print(f"    {'Reach':<28}{'Q100 width':>12}{'depth':>8}{'vel':>7}{'unit power':>12}")
    print(f"    {'':<28}{'m':>12}{'m':>8}{'m/s':>7}{'W/m2':>12}")
    for r in D.REACHES:
        n = nodes[r.node]
        st = H.flow_state(H.design_flood(n.total_area_km2, 100, n.cv), r)
        print(f"    {r.label:<28}{st.top_width_m:>12.0f}{st.depth_m:>8.1f}"
              f"{st.velocity_ms:>7.1f}{st.unit_stream_power_w_per_m2:>12,.0f}")

    print()
    print("    Above roughly 1,000 W/m2 masonry does not survive contact with the")
    print("    flow. Most Himalayan reaches in this table exceed that at Q100 - so")
    print("    inside Zone C, 'regulated construction on a raised plinth' is not a")
    print("    mitigation. The plinth is in the path of a boulder-laden torrent.")

    # -- 3. the outburst corridor ------------------------------------------
    print()
    print(_rule("-"))
    print("  3. THE EVENT THE ZONING DOES NOT COVER")
    print(_rule("-"))
    print()
    v = D.KEDARNATH_2013_VOLUME_M3
    water_only = EVANS_A * (v ** EVANS_B)
    bulked = breach_peak_cumec(v)
    obs = D.KEDARNATH_2013_PEAK_CUMEC
    print("    VALIDATION - Chorabari lake breach, 17 June 2013")
    print()
    print(f"      released volume                        {v:>10,.0f} m3")
    print(f"      Evans (1986) water peak, 0.72*V^0.53   {water_only:>10,.0f} m3/s")
    print(f"      x debris bulking factor {DEBRIS_BULKING:.1f}            "
          f"{bulked:>10,.0f} m3/s")
    print(f"      OBSERVED (BREACH model)                {obs:>10,.0f} m3/s")
    print(f"      error                                  {100.0 * (bulked - obs) / obs:>9.1f}%")
    print()
    print("    The water-only relation underpredicts by roughly half; with the")
    print("    bulking factor it lands within a few per cent. Do not read that as")
    print("    high accuracy - the bulking factor was chosen from a plausible")
    print("    range and only ONE event tests it here. Read it as evidence that")
    print("    the mechanism is right: an outburst flood is a debris flow, and")
    print("    modelling it as clear water halves the answer.")
    print()
    print("    SCENARIO LADDER - outburst peak and the corridor it needs,")
    print("    computed in a representative steep reach (Mandakini at Rudraprayag):")
    print()
    steep = D.REACH_BY_KEY["mandakini"]
    n_steep = nodes[steep.node]
    q100_steep = H.design_flood(n_steep.total_area_km2, 100, n_steep.cv)
    st100 = H.flow_state(q100_steep, steep)
    print(f"      {'lake volume':<16}{'peak Q':>10}{'vs Q100':>10}{'width':>9}"
          f"{'depth':>8}{'unit power':>12}")
    print(f"      {'Mm3':<16}{'m3/s':>10}{'':>10}{'m':>9}{'m':>8}{'W/m2':>12}")
    for vol_mm3 in (0.5, 1.0, 2.0, 5.0, 10.0, 25.0):
        qp = breach_peak_cumec(vol_mm3 * 1e6)
        st = H.flow_state(qp, steep)
        print(f"      {vol_mm3:<16.1f}{qp:>10,.0f}{qp / q100_steep:>9.1f}x"
              f"{st.top_width_m:>9.0f}{st.depth_m:>8.1f}"
              f"{st.unit_stream_power_w_per_m2:>12,.0f}")
    print()
    print(f"      for reference, Q100 here is {q100_steep:,.0f} m3/s, "
          f"{st100.top_width_m:.0f} m wide, "
          f"{st100.unit_stream_power_w_per_m2:,.0f} W/m2")
    print()
    print("    A 10 Mm3 outburst - not an extreme lake by Himalayan standards -")
    print("    produces a corridor far outside the statutory Zone C line, at a")
    print("    unit stream power that removes built form entirely.")
    print()
    print("    And it carries NO return period. It is not the 200-year flood or")
    print("    the 1,000-year flood. Dam failure is a condition-dependent event,")
    print("    and the condition - a moraine dam impounding a lake that is growing")
    print("    as the glacier retreats - is getting worse with time, not")
    print("    stationary. Frequency analysis assumes stationarity. Here that")
    print("    assumption is simply false.")

    # -- 4. district risk --------------------------------------------------
    print()
    print(_rule("-"))
    print("  4. DISTRICT FLOOD RISK INDEX  -  Hazard x Exposure x Vulnerability")
    print(_rule("-"))
    print()
    results = assess()
    print(f"    {'#':<3}{'District':<16}{'Governing reach':<26}"
          f"{'H':>6}{'E':>6}{'V':>6}{'RISK':>8}")
    for i, r in enumerate(results, 1):
        print(f"    {i:<3}{r.district.name:<16}{r.reach.label:<26}"
              f"{r.hazard:>6.2f}{r.exposure:>6.2f}{r.vulnerability:>6.2f}{r.risk:>8.1f}")

    print()
    print("    CORRIDOR EXPOSURE - people and land on the geomorphic river")
    print("    corridor: valley floor, terraces and fans. This is NOT the Q100")
    print("    inundation line - it is the wider landform envelope, which section")
    print("    3 argues is the envelope that actually matters in the mountains.")
    print()
    print(f"    {'District':<16}{'buildable':>11}{'corridor':>10}{'corridor':>12}"
          f"{'corridor':>12}{'Q100 power':>12}")
    print(f"    {'':<16}{'km2':>11}{'km2':>10}{'people':>12}{'per km2':>12}{'W/m2':>12}")
    for r in sorted(results, key=lambda x: x.corridor_density, reverse=True):
        d = r.district
        buildable = d.area_km2 * d.habitable_fraction
        print(f"    {d.name:<16}{buildable:>11,.0f}{r.corridor_land_km2:>10,.0f}"
              f"{r.corridor_population:>12,}{r.corridor_density:>12,.0f}"
              f"{r.unit_power:>12,.0f}")

    total_corr_pop = sum(r.corridor_population for r in results)
    total_corr_land = sum(r.corridor_land_km2 for r in results)
    print()
    print(f"    Statewide, roughly {total_corr_pop:,} people - "
          f"{100.0 * total_corr_pop / D.STATE_POPULATION_2011:.0f}% of Uttarakhand -")
    print(f"    live on about {total_corr_land:,.0f} km2 of river-corridor landform,")
    print(f"    which is {100.0 * total_corr_land / D.STATE_AREA_KM2:.1f}% of the "
          f"state's area. Half the population on under a tenth of")
    print("    the land, and it is the tenth the river made.")

    # -- weight sensitivity ------------------------------------------------
    print()
    print("    WEIGHT SENSITIVITY - the weights above were chosen, not derived,")
    print("    so here is the ranking under equal weights instead:")
    print()
    equal = sorted(
        results,
        key=lambda r: ((r.hazard + r.exposure + r.vulnerability) / 3.0),
        reverse=True,
    )
    moved = sum(1 for i, r in enumerate(equal)
                if r.district.name != results[i].district.name)
    print("      " + " > ".join(r.district.name for r in equal[:6]))
    print()
    print(f"    {moved} of 13 districts change position. The top of the table is")
    print("    stable under reweighting; the middle is not. Treat the ranking as")
    print("    three or four tiers, not as thirteen ordered places.")
    print()


if __name__ == "__main__":
    main()
