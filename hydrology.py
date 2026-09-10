"""
Uttarakhand water flow - routing, yield, and design flood peaks.

    python hydrology.py

WHAT THIS DOES

1. Routes the state drainage tree (uk_data.CATCHMENTS) to get total upstream
   area at every confluence, and validates the result against two independently
   published catchment areas - the Pashulok barrage at Rishikesh (21,400 km2)
   and the Bhimgoda barrage at Haridwar (23,000 km2).

2. Computes mean annual flow by water balance: rainfall x runoff coefficient
   over the non-glacierized area, plus a glacier melt term. Snow and ice are
   not a detail here - in the Higher Himalayan headwaters they are most of the
   pre-monsoon flow, which is why these rivers run in May when a purely
   rain-fed river of the same size would be dry.

3. Computes design flood peaks Q25/Q50/Q100/Q500 by the index-flood method:
   a regional mean-annual-flood relation MAF = a * A^b, calibrated on ONE
   observed datum (the mean annual peak of the Ganga at Devprayag), then scaled
   by Gumbel EV1 growth factors.

4. Cross-checks those peaks against Dickens' formula, the empirical estimator
   in standard use across north India, and reports the implied Dickens
   coefficient so the disagreement is visible rather than hidden.

5. Solves Manning's equation for normal depth at Q100 in thirteen real reaches,
   giving inundation width, velocity, and unit stream power - the quantity that
   actually decides whether a flood wets a building or removes it.

6. Computes flood wave travel time, which is the warning lead time a
   downstream town would get.

WHAT THIS IS NOT

This is a screening model built from published basin figures and typical
hydraulic parameters. It is not a gauged flood frequency analysis, and it is
not a hydraulic model of any surveyed cross-section. Nothing here should be
used to site a building. Its purpose is to establish the ORDER OF MAGNITUDE
and the RELATIVE ranking between reaches, which is enough to expose where the
risk actually concentrates - and, in section 5, enough to show that the
standard design flood framework does not describe Uttarakhand's real killer.

VERIFY EVERY COEFFICIENT against a primary source before using any output.
Provenance for each input is tagged [M] or [E] in uk_data.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import uk_data as D

SECONDS_PER_YEAR = 31_556_952.0
RHO_WATER = 1000.0      # kg/m3
GRAVITY = 9.81          # m/s2

# ---------------------------------------------------------------------------
# Regional flood frequency parameters
# ---------------------------------------------------------------------------

# Index-flood relation  MAF = a * A^b.
#
# b = 0.72 is an ESTIMATE. Index-flood exponents for Himalayan and sub-Himalayan
# basins are typically 0.7-0.8; below 1.0 because large basins do not flood over
# their whole area at once, so specific yield falls as area grows. `a` is then
# calibrated from the single observed anchor rather than assumed.
#
# ONE anchor fits ONE parameter. b is therefore carried on judgement alone, and
# the sensitivity of the answer to b is reported in main() rather than buried.
MAF_EXPONENT_B = 0.72

# Coefficient of variation of the annual maximum series, by physiography [E].
# Higher Himalayan catchments are flashier - small area, steep slope, snowmelt
# and monsoon peaks superimposed - so their annual maxima scatter more widely
# and their growth curve is steeper.
CV_BY_TERRAIN = {"higher": 0.75, "lesser": 0.65, "outer": 0.60, "terai": 0.55}

# Net glacier melt yield, metres water equivalent per year over glacier area [E].
GLACIER_MELT_M_PER_YEAR = 1.2

# Dickens' formula Q = C * A^0.75. C bands from standard north Indian practice:
DICKENS_C_PLAINS = (2.8, 5.6)
DICKENS_C_HILLS = (14.0, 28.0)

# Indicative unit stream power damage thresholds, W/m2 [E].
# From the flood damage literature; bands are broad and overlap in reality.
STREAM_POWER_BANDS = (
    (100.0, "inundation only - wetting, silt, little structural damage"),
    (1000.0, "scour begins - weak walls, boundary walls, kutcha structures fail"),
    (10000.0, "masonry destroyed - buildings removed from foundations"),
    (float("inf"), "channel reworked - boulder transport, total loss of built form"),
)


# ---------------------------------------------------------------------------
# 1. Routing
# ---------------------------------------------------------------------------

@dataclass
class NodeResult:
    key: str
    label: str
    total_area_km2: float
    glacier_km2: float
    mean_flow_cumec: float
    maf_cumec: float
    cv: float
    terrain: str
    confluence: str


def route() -> dict[str, NodeResult]:
    """Accumulate area, glacier area and yield down the drainage tree.

    Depth-first with memoisation. The tree was proven acyclic by
    uk_data.validate(), so recursion terminates.
    """
    memo: dict[str, NodeResult] = {}

    def _solve(key: str) -> NodeResult:
        if key in memo:
            return memo[key]
        c = D.CATCHMENT_BY_KEY[key]

        area = c.local_area_km2
        glacier = c.glacier_km2
        flow = _local_yield_cumec(c)
        cv_moment = c.local_area_km2 * CV_BY_TERRAIN.get(c.terrain, 0.65)

        for up in c.upstream:
            r = _solve(up)
            area += r.total_area_km2
            glacier += r.glacier_km2
            flow += r.mean_flow_cumec
            cv_moment += r.total_area_km2 * r.cv

        # Cv is a property of the whole contributing basin, not of the terrain
        # at the outlet. Taking the local terrain class instead produces a
        # visible artifact: Haridwar sits on the Terai, so a local lookup gives
        # it a lower Cv than Rishikesh 24 km upstream, and the 100-year flood
        # comes out SMALLER at the bigger catchment. Area-weighting the
        # incremental contributions removes that discontinuity, and is what the
        # index-flood method means by a homogeneous region in any case.
        cv = cv_moment / area if area > 0 else CV_BY_TERRAIN.get(c.terrain, 0.65)

        node = NodeResult(
            key=key, label=c.label, total_area_km2=area, glacier_km2=glacier,
            mean_flow_cumec=flow, maf_cumec=mean_annual_flood(area), cv=cv,
            terrain=c.terrain, confluence=c.confluence,
        )
        memo[key] = node
        return node

    for c in D.CATCHMENTS:
        _solve(c.key)
    return memo


_ROUTED: dict[str, NodeResult] | None = None


def nodes() -> dict[str, NodeResult]:
    """Routed drainage tree, computed once and cached.

    Routing is pure and depends only on static data, so every caller should get
    the same object rather than re-walking the tree.
    """
    global _ROUTED
    if _ROUTED is None:
        _ROUTED = route()
    return _ROUTED


def _local_yield_cumec(c: D.Catchment) -> float:
    """Mean annual flow generated by ONE catchment's incremental area.

        yield = P * C * (A - A_glacier)  +  melt * A_glacier

    The glacier area is removed from the rainfall term before the melt term is
    added, otherwise ice-covered ground is counted twice - once as rainfall
    runoff and once as melt.
    """
    rain_area_km2 = max(0.0, c.local_area_km2 - c.glacier_km2)
    rain_m3 = (c.rainfall_mm / 1000.0) * c.runoff_coeff * rain_area_km2 * 1e6
    melt_m3 = GLACIER_MELT_M_PER_YEAR * c.glacier_km2 * 1e6
    return (rain_m3 + melt_m3) / SECONDS_PER_YEAR


# ---------------------------------------------------------------------------
# 2. Design floods
# ---------------------------------------------------------------------------

def _maf_coefficient_a() -> float:
    """Calibrate `a` in MAF = a * A^b from the single observed anchor."""
    return D.ANCHOR_DEVPRAYAG_MAF_CUMEC / (D.ANCHOR_DEVPRAYAG_AREA_KM2 ** MAF_EXPONENT_B)


MAF_COEFFICIENT_A = _maf_coefficient_a()


def mean_annual_flood(area_km2: float, b: float = MAF_EXPONENT_B) -> float:
    """Mean annual flood (mean of the annual maximum series), m3/s."""
    if area_km2 <= 0:
        return 0.0
    a = D.ANCHOR_DEVPRAYAG_MAF_CUMEC / (D.ANCHOR_DEVPRAYAG_AREA_KM2 ** b)
    return a * (area_km2 ** b)


def gumbel_frequency_factor(return_period_years: float) -> float:
    """Gumbel EV1 frequency factor K_T for an infinite sample.

        K_T = -(sqrt(6)/pi) * [0.5772 + ln(ln(T/(T-1)))]

    K is zero at T = 2.33 years, which is why the mean annual flood is often
    quoted as "the 2.33-year flood" - it is the mean of the annual maxima, not
    a round-numbered return period.
    """
    if return_period_years <= 1.0:
        raise ValueError("return period must exceed 1 year")
    T = return_period_years
    return -(math.sqrt(6.0) / math.pi) * (0.5772 + math.log(math.log(T / (T - 1.0))))


def design_flood(area_km2: float, return_period_years: float, cv: float) -> float:
    """Q_T by the index-flood method: Q_T = MAF * (1 + Cv * K_T).

    `cv` is the area-weighted coefficient of variation of the contributing
    basin - see route(). Pass a terrain value from CV_BY_TERRAIN only for a
    single ungauged catchment with no routing behind it.
    """
    growth = 1.0 + cv * gumbel_frequency_factor(return_period_years)
    return mean_annual_flood(area_km2) * max(growth, 0.0)


def dickens_peak(area_km2: float, c: float) -> float:
    """Dickens' empirical flood peak, Q = C * A^0.75."""
    return c * (area_km2 ** 0.75)


def implied_dickens_c(area_km2: float, discharge_cumec: float) -> float:
    """The Dickens C that would reproduce a given discharge. Diagnostic only."""
    return discharge_cumec / (area_km2 ** 0.75)


# ---------------------------------------------------------------------------
# 3. Open channel hydraulics
# ---------------------------------------------------------------------------

@dataclass
class FlowState:
    depth_m: float
    top_width_m: float
    area_m2: float
    velocity_ms: float
    froude: float
    stream_power_w_per_m: float
    unit_stream_power_w_per_m2: float
    damage_band: str


def section_geometry(y: float, reach: D.Reach) -> tuple[float, float, float, float]:
    """Compound-section geometry at depth y.

    Returns (flow area, top width, wetted perimeter, equivalent roughness).

    Below bank-full it is the main channel trapezoid. Above bank-full a second,
    much flatter trapezoid sits on top of it - the floodplain - with its own
    side slope and its own roughness.

    The two roughnesses are combined by the Horton-Einstein equivalent-n rule,

        n_eq = [ sum(P_i * n_i^1.5) / P ]^(2/3)

    which weights each sub-section by its share of wetted perimeter. Using the
    channel n over the whole compound section would let a flood run across a
    built-up floodplain as smoothly as it runs down the river, overstating
    velocity and understating depth.
    """
    b, z = reach.bed_width_m, reach.side_slope_z
    bank, zv = reach.bank_depth_m, reach.valley_slope_z

    if y <= bank:
        area = (b + z * y) * y
        top = b + 2.0 * z * y
        per = b + 2.0 * y * math.sqrt(1.0 + z ** 2)
        return area, top, per, reach.manning_n

    # in-bank part, filled to bank-full
    area_c = (b + z * bank) * bank
    top_c = b + 2.0 * z * bank
    per_c = b + 2.0 * bank * math.sqrt(1.0 + z ** 2)

    # overbank part
    y2 = y - bank
    area_f = (top_c + zv * y2) * y2
    top_f = top_c + 2.0 * zv * y2
    per_f = 2.0 * y2 * math.sqrt(1.0 + zv ** 2)

    area = area_c + area_f
    per = per_c + per_f
    n_eq = ((per_c * reach.manning_n ** 1.5 + per_f * reach.overbank_n ** 1.5) / per) ** (2.0 / 3.0)
    return area, top_f, per, n_eq


def normal_depth(q_cumec: float, reach: D.Reach, tol: float = 1e-6) -> float:
    """Solve Manning's equation for normal depth in the compound section.

        Q = (1/n) * A * R^(2/3) * sqrt(S)

    Discharge increases monotonically with depth, so bisection is
    unconditionally convergent - no derivative, no divergence, no initial guess
    to get wrong. Newton would be faster and would occasionally shoot negative.
    Speed is not the constraint here.
    """
    if q_cumec <= 0:
        return 0.0

    def _q(y: float) -> float:
        area, _top, per, n = section_geometry(y, reach)
        if per <= 0 or area <= 0:
            return 0.0
        r = area / per
        return (1.0 / n) * area * (r ** (2.0 / 3.0)) * math.sqrt(reach.bed_slope)

    lo, hi = 1e-6, 1.0
    while _q(hi) < q_cumec:
        hi *= 2.0
        if hi > 1e4:
            raise ValueError("normal depth did not bracket - check reach geometry")

    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if _q(mid) < q_cumec:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def flow_state(q_cumec: float, reach: D.Reach) -> FlowState:
    """Full hydraulic state at a given discharge.

    Unit stream power omega = rho*g*Q*S / T is the number that matters for
    damage. Total stream power says how much energy the flood carries; dividing
    by top width says how concentrated it is. A steep narrow Himalayan reach and
    a flat wide Terai reach can pass the same discharge with unit stream powers
    two orders of magnitude apart - and that difference, not the discharge, is
    what decides whether a house is flooded or erased.
    """
    y = normal_depth(q_cumec, reach)
    area, top_width, _per, _n = section_geometry(y, reach)
    velocity = q_cumec / area if area > 0 else 0.0
    hydraulic_depth = area / top_width if top_width > 0 else 0.0
    froude = velocity / math.sqrt(GRAVITY * hydraulic_depth) if hydraulic_depth > 0 else 0.0

    total_power = RHO_WATER * GRAVITY * q_cumec * reach.bed_slope
    unit_power = total_power / top_width if top_width > 0 else 0.0

    band = next(desc for limit, desc in STREAM_POWER_BANDS if unit_power < limit)

    return FlowState(y, top_width, area, velocity, froude, total_power, unit_power, band)


def wave_travel_time_hours(reach: D.Reach, state: FlowState) -> float:
    """Kinematic wave travel time over the reach - the warning lead time.

    Celerity c = (5/3) * V for a wide channel under Manning friction. The flood
    wave outruns the water itself by that factor, so lead time is shorter than
    a float would suggest. This is an upper bound on available warning: it
    assumes the wave is detected the instant it forms.
    """
    if reach.reach_length_km <= 0 or state.velocity_ms <= 0:
        return 0.0
    celerity = (5.0 / 3.0) * state.velocity_ms
    return (reach.reach_length_km * 1000.0) / celerity / 3600.0


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _rule(char: str = "=", n: int = 78) -> str:
    return char * n


def main() -> None:
    nodes_ = nodes()

    print()
    print(_rule())
    print("  UTTARAKHAND - WATER FLOW AND DESIGN FLOOD ANALYSIS")
    print(_rule())

    # -- data closure ------------------------------------------------------
    print()
    print("  DATA CLOSURE")
    for line in D.validate():
        print(f"    {line}")

    # -- routing validation ------------------------------------------------
    print()
    print("  ROUTING VALIDATION - routed area vs independently published catchment")
    checks = (
        ("Alaknanda at Devprayag", "alaknanda_devprayag", D.CTRL_ALAKNANDA_DEVPRAYAG_KM2),
        ("Ganga at Rishikesh", "rishikesh", D.CTRL_GANGA_RISHIKESH_KM2),
        ("Ganga at Haridwar", "haridwar", D.CTRL_GANGA_HARIDWAR_KM2),
    )
    for label, key, control in checks:
        got = nodes_[key].total_area_km2
        err = 100.0 * (got - control) / control
        flag = "OK" if abs(err) < 0.5 else "CHECK"
        print(f"    {label:<26}{got:>9,.0f} km2  vs {control:>8,} km2  {err:+6.2f}%  {flag}")
    print()
    print("    These close to zero BY CONSTRUCTION - sub-catchments were apportioned")
    print("    to hit them. They validate the routing arithmetic and the topology,")
    print("    NOT the area of any individual tributary.")

    # -- water flow --------------------------------------------------------
    print()
    print(_rule("-"))
    print("  1. WATER FLOW  -  mean annual, by water balance")
    print(_rule("-"))
    print()
    print(f"    {'Node':<34}{'Area':>10}{'Glacier':>9}{'Mean Q':>10}{'Yield':>9}")
    print(f"    {'':<34}{'km2':>10}{'km2':>9}{'m3/s':>10}{'L/s/km2':>9}")

    order = ("vishnuprayag", "nandprayag", "karnaprayag", "rudraprayag",
             "alaknanda_devprayag", "bhagirathi_harsil", "tehri",
             "bhagirathi_devprayag", "devprayag", "rishikesh", "haridwar",
             "yamuna_exit", "sharda_banbasa", "ramganga_kalagarh",
             "kosi_ramnagar", "gaula_kathgodam", "nandhaur", "terai_direct")
    for key in order:
        n = nodes_[key]
        specific = 1000.0 * n.mean_flow_cumec / n.total_area_km2
        print(f"    {n.label:<34}{n.total_area_km2:>10,.0f}{n.glacier_km2:>9,.0f}"
              f"{n.mean_flow_cumec:>10,.0f}{specific:>9.1f}")

    hw = nodes_["haridwar"]
    total_state = sum(_local_yield_cumec(c) for c in D.CATCHMENTS)
    print()
    print(f"    Ganga leaves the hills at Haridwar carrying {hw.mean_flow_cumec:,.0f} m3/s")
    print(f"    on average - {hw.mean_flow_cumec * SECONDS_PER_YEAR / 1e9:,.1f} km3/yr from "
          f"{hw.total_area_km2:,.0f} km2.")
    print(f"    Whole-state surface water yield: {total_state:,.0f} m3/s = "
          f"{total_state * SECONDS_PER_YEAR / 1e9:,.1f} km3/yr")
    print()
    head_y = 1000.0 * nodes_["bhagirathi_harsil"].mean_flow_cumec / nodes_["bhagirathi_harsil"].total_area_km2
    terai_y = 1000.0 * nodes_["terai_direct"].mean_flow_cumec / nodes_["terai_direct"].total_area_km2
    print("    Read the yield column, not the discharge column. Discharge just")
    print("    tracks catchment size; yield says how much water a square kilometre")
    print("    of a given landscape actually delivers to the channel.")
    print()
    print(f"    Glaciated headwater (Bhagirathi at Harsil)  {head_y:>5.1f} L/s/km2")
    print(f"    Terai / Bhabar direct drainage              {terai_y:>5.1f} L/s/km2")
    head_p = D.CATCHMENT_BY_KEY["bhagirathi_harsil"].rainfall_mm
    terai_p = D.CATCHMENT_BY_KEY["terai_direct"].rainfall_mm
    print()
    print(f"    The Terai gets {terai_p:,.0f} mm of rain against Harsil's {head_p:,.0f} mm")
    print("    and still yields half as much water. The Bhabar gravel belt is why")
    print("    - it swallows surface flow, and streams crossing it")
    print("    genuinely go underground. That is recharge, not loss: the water")
    print("    re-emerges downslope as the Terai spring line. Apply a hill runoff")
    print("    coefficient to the foothill belt and you roughly double its")
    print("    estimated surface yield while missing the aquifer entirely.")

    # -- design floods -----------------------------------------------------
    print()
    print(_rule("-"))
    print("  2. DESIGN FLOOD PEAKS  -  index flood + Gumbel EV1")
    print(_rule("-"))
    print()
    print(f"    Calibration: MAF = {MAF_COEFFICIENT_A:.3f} * A^{MAF_EXPONENT_B}")
    print(f"    anchored on the Ganga at Devprayag, mean annual peak "
          f"{D.ANCHOR_DEVPRAYAG_MAF_CUMEC:,.0f} m3/s over {D.ANCHOR_DEVPRAYAG_AREA_KM2:,} km2.")
    print()
    print("    Gumbel growth factors (1 + Cv*K_T):")
    print(f"      {'T (yr)':<10}{'K_T':>8}", end="")
    for terr in ("higher", "lesser", "outer", "terai"):
        print(f"{terr:>10}", end="")
    print()
    for T in (2.33, 25, 50, 100, 500):
        k = gumbel_frequency_factor(T)
        print(f"      {T:<10.2f}{k:>8.3f}", end="")
        for terr in ("higher", "lesser", "outer", "terai"):
            print(f"{1.0 + CV_BY_TERRAIN[terr] * k:>10.2f}", end="")
        print()

    print()
    print(f"    {'Reach':<28}{'Area':>9}{'Cv':>6}{'MAF':>9}{'Q25':>9}{'Q50':>9}{'Q100':>9}{'Q500':>9}")
    print(f"    {'':<28}{'km2':>9}{'wtd':>6}{'m3/s':>9}{'m3/s':>9}{'m3/s':>9}{'m3/s':>9}{'m3/s':>9}")
    for r in D.REACHES:
        n = nodes_[r.node]
        a = n.total_area_km2
        row = [design_flood(a, T, n.cv) for T in (25, 50, 100, 500)]
        print(f"    {r.label:<28}{a:>9,.0f}{n.cv:>6.2f}{n.maf_cumec:>9,.0f}"
              + "".join(f"{v:>9,.0f}" for v in row))

    # -- Dickens cross-check ----------------------------------------------
    print()
    print(_rule("-"))
    print("  3. CROSS-CHECK AGAINST DICKENS' FORMULA")
    print(_rule("-"))
    print()
    print("    Q = C * A^0.75, the empirical estimator in standard use across")
    print(f"    north India. C = {DICKENS_C_PLAINS[0]}-{DICKENS_C_PLAINS[1]} for plains, "
          f"{DICKENS_C_HILLS[0]}-{DICKENS_C_HILLS[1]} for hills.")
    print()
    print(f"    {'Reach':<28}{'Q100':>10}{'Dickens':>10}{'ratio':>8}{'implied':>9}")
    print(f"    {'':<28}{'index':>10}{'C=20':>10}{'':>8}{'C':>9}")
    for r in D.REACHES:
        n = nodes_[r.node]
        a = n.total_area_km2
        q100 = design_flood(a, 100, n.cv)
        dick = dickens_peak(a, 20.0)
        print(f"    {r.label:<28}{q100:>10,.0f}{dick:>10,.0f}"
              f"{dick / q100:>8.1f}x{implied_dickens_c(a, q100):>9.2f}")

    print()
    print("    Dickens with the textbook HILL coefficient overpredicts this basin's")
    print("    100-year flood by 4.5-6x at every scale from 45 km2 to 23,000 km2.")
    print("    The implied C sits at 3.4-4.5 - inside the PLAINS band, not the hill")
    print("    band, and remarkably flat across a 500-fold range of catchment area.")
    print()
    print("    The exponent is not the problem; the coefficient is. C = 14-28 is an")
    print("    envelope of maximum observed floods on small hill catchments, and an")
    print("    envelope is not a 100-year estimate. Used as one it sizes structures")
    print("    for a flood far rarer than intended. Either result may be defended -")
    print("    but they cannot both be used, and the choice must be stated.")

    # -- hydraulics --------------------------------------------------------
    print()
    print(_rule("-"))
    print("  4. FLOODPLAIN HYDRAULICS AT Q100  -  Manning normal depth")
    print(_rule("-"))
    print()
    print(f"    {'Reach':<28}{'slope':>8}{'depth':>8}{'width':>8}{'vel':>7}{'Fr':>6}{'unit power':>12}")
    print(f"    {'':<28}{'m/m':>8}{'m':>8}{'m':>8}{'m/s':>7}{'':>6}{'W/m2':>12}")
    states: dict[str, FlowState] = {}
    for r in D.REACHES:
        n = nodes_[r.node]
        q100 = design_flood(n.total_area_km2, 100, n.cv)
        st = flow_state(q100, r)
        states[r.key] = st
        print(f"    {r.label:<28}{r.bed_slope:>8.4f}{st.depth_m:>8.1f}{st.top_width_m:>8.0f}"
              f"{st.velocity_ms:>7.1f}{st.froude:>6.2f}{st.unit_stream_power_w_per_m2:>12,.0f}")

    print()
    print("    DAMAGE BAND at Q100:")
    for r in D.REACHES:
        print(f"      {r.label:<28}{states[r.key].damage_band}")

    print()
    print("    This is the central hydraulic result, and it inverts the intuition")
    print("    that a bigger river is a more dangerous one.")
    print()
    hd, kd = states["haridwar"], states["kedarnath"]
    print(f"    Ganga at Haridwar carries far more water than the Mandakini at")
    print(f"    Kedarnath, yet its unit stream power is {hd.unit_stream_power_w_per_m2:,.0f} W/m2")
    print(f"    against {kd.unit_stream_power_w_per_m2:,.0f} W/m2 - a factor of "
          f"{kd.unit_stream_power_w_per_m2 / hd.unit_stream_power_w_per_m2:,.0f}.")
    print()
    print("    Slope does that. A flat wide channel spreads the same energy over a")
    print("    kilometre of width; a steep narrow gorge concentrates it into 30 m.")
    print("    So the two hazards are physically different and need different rules:")
    print()
    print("      Terai      wide shallow inundation, low velocity. Damage is by")
    print("                 water contact. Plinth level and drainage are the fix.")
    print("      Himalaya   narrow, deep, supercritical, boulder-laden. Damage is")
    print("                 by impact and scour. NOTHING built in the corridor")
    print("                 survives it. Only setback distance works.")

    # -- travel time -------------------------------------------------------
    print()
    print(_rule("-"))
    print("  5. FLOOD WAVE TRAVEL TIME  -  the warning lead time")
    print(_rule("-"))
    print()
    print(f"    {'Reach':<28}{'length':>9}{'celerity':>10}{'lead time':>12}")
    print(f"    {'':<28}{'km':>9}{'m/s':>10}{'minutes':>12}")
    for r in D.REACHES:
        if r.reach_length_km <= 0:
            continue
        st = states[r.key]
        hrs = wave_travel_time_hours(r, st)
        print(f"    {r.label:<28}{r.reach_length_km:>9.0f}"
              f"{(5.0 / 3.0) * st.velocity_ms:>10.1f}{hrs * 60.0:>12.0f}")
    print()
    print("    These are UPPER bounds - they assume the wave is detected the")
    print("    instant it forms. Under an hour is not an evacuation window; it is")
    print("    barely a siren window, and only if the siren already exists.")

    # -- the framework's blind spot ---------------------------------------
    print()
    print(_rule("-"))
    print("  6. WHERE THIS ENTIRE FRAMEWORK FAILS")
    print(_rule("-"))
    print()
    a = D.KEDARNATH_2013_CATCHMENT_KM2
    q100_kedar = design_flood(a, 100, nodes_["mandakini_kedarnath"].cv)
    q500_kedar = design_flood(a, 500, nodes_["mandakini_kedarnath"].cv)
    obs = D.KEDARNATH_2013_PEAK_CUMEC
    print(f"    Mandakini above Kedarnath, catchment {a:.0f} km2:")
    print()
    print(f"      100-year rainfall flood (this model)   {q100_kedar:>8,.0f} m3/s")
    print(f"      500-year rainfall flood (this model)   {q500_kedar:>8,.0f} m3/s")
    print(f"      Dickens, C = 28 (hill envelope)        {dickens_peak(a, 28.0):>8,.0f} m3/s")
    print(f"      OBSERVED, 17 June 2013                 {obs:>8,.0f} m3/s")
    print()
    print(f"    The observed peak was {obs / q100_kedar:.0f}x the 100-year flood and "
          f"{obs / q500_kedar:.0f}x the 500-year.")
    print(f"    It exceeded even the Dickens hill envelope by "
          f"{obs / dickens_peak(a, 28.0):.1f}x.")
    print()
    print("    The model is not wrong. It is answering a different question.")
    print()
    print(f"    Chorabari lake released {D.KEDARNATH_2013_VOLUME_M3:,.0f} m3 through a")
    print("    moraine breach. That volume was in storage, not in the rainfall. A")
    print("    frequency curve fitted to annual rainfall maxima cannot contain it at")
    print("    ANY return period, because the process is a dam failure, not a storm.")
    print()
    print("    The same holds for the other Uttarakhand mechanisms: glacial lake")
    print("    outburst (GLOF), landslide-dam outburst (LDOF), and rock-ice avalanche")
    print("    - the Chamoli event of February 2021, which happened in WINTER, with")
    print("    no monsoon and no rain at all.")
    print()
    print("    CONSEQUENCE FOR ZONING: a floodplain line drawn at Q100 is drawn for")
    print("    the wrong event. In the Himalayan reaches the zoning envelope has to")
    print("    come from GEOMORPHOLOGY - paleoflood terraces, debris-fan boundaries,")
    print("    the visible boulder line - not from a return period. Those landforms")
    print("    record what has actually happened. The frequency curve records only")
    print("    what the rain gauge has seen since it was installed.")
    print()


if __name__ == "__main__":
    main()
