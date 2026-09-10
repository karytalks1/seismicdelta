"""
Uttarakhand construction density - where the building stock actually is.

    python builtform.py

THE QUESTION THIS ANSWERS

Uttarakhand's population density is 189 people per km2. India's is 382. On that
number the state looks half-empty, and it is the number that gets quoted.

It is the wrong number. Roughly 86% of the state is hill terrain, 45% is under
forest cover, and large tracts of the Higher Himalaya are glacier, moraine and
rock above the tree line. Almost none of that can be built on. Dividing people
by TOTAL area answers a question nobody asked. Dividing them by BUILDABLE area
answers the one that matters, and gives a completely different answer.

Then there is where the buildable land is. In a steep valley the level ground
is the valley floor and the river terraces - which is to say the floodplain and
the paleo-floodplain. Flat land and flood-exposed land are very nearly the same
land. So construction does not merely coexist with the flood hazard here; it is
pushed into it by the topography.

    hydrology.py  - how much water, how fast, how hard it hits
    floodrisk.py  - where the zoning line falls and why it is in the wrong place
    builtform.py  - what is standing inside that line, and what it is made of

ASSUMPTIONS, all [E], all consequential:

  * habitable_fraction per district (uk_data.py) - the dominant one. A
    sensitivity band is reported rather than a single answer.
  * dwelling footprint and a non-residential multiplier for roads, shops,
    schools, hotels and the Char Dham service infrastructure.
  * household size by terrain, then scaled by a SINGLE factor so the state
    total closes on the Census figure of 2,056,975 households. The factor is
    printed - if it were far from 1.0 the size assumptions would be wrong.

These are screening estimates from published aggregates, not a building survey
or a footprint extraction from imagery. Ranking and order of magnitude are the
deliverable; a plot-level answer is not.
"""

from __future__ import annotations

from dataclasses import dataclass

import uk_data as D
import hydrology as H
import floodrisk as FR
import seismic

# ---------------------------------------------------------------------------
# Building stock assumptions  [E]
# ---------------------------------------------------------------------------

# Average persons per household, before calibration to the Census total.
# Hill households are smaller - out-migration of working-age adults leaves
# older, smaller households behind. Terai households are larger.
HOUSEHOLD_SIZE = {"higher": 4.6, "lesser": 4.6, "outer": 4.9, "terai": 5.5}

# Ground-floor footprint per dwelling, m2.
# Urban dwellings have a SMALLER footprint because they stack - the floor area
# is comparable, the ground taken is not.
FOOTPRINT_RURAL = {"higher": 55.0, "lesser": 60.0, "outer": 75.0, "terai": 85.0}
FOOTPRINT_URBAN = 45.0

# Multiplier on residential footprint for everything else that gets built:
# roads, bazaars, schools, offices, hotels. Higher in the hill districts on the
# pilgrimage routes, where the serviced population far exceeds the resident one.
NONRESIDENTIAL_MULTIPLIER = {"higher": 1.9, "lesser": 1.7, "outer": 1.6, "terai": 1.5}

# Density comparators, Census 2011, persons per km2 [M]
COMPARATORS = (
    ("Bihar - densest major state", 1106),
    ("West Bengal", 1028),
    ("Kerala", 860),
    ("Uttar Pradesh", 829),
    ("INDIA", 382),
    ("Uttarakhand, as usually quoted", 189),
)


@dataclass
class BuiltForm:
    district: D.District
    households: int
    buildable_km2: float
    built_up_km2: float
    raw_density: float
    buildable_density: float
    built_up_ratio: float          # built-up as % of buildable land
    corridor_dwellings: int
    corridor_built_up_km2: float
    unit_power: float


def _household_size_calibration() -> float:
    """Scale factor that makes the assumed household sizes close on the Census.

    Assumed sizes give a state household count; the Census gives 2,056,975. One
    multiplicative factor reconciles them. Reporting it is the check - a factor
    within a few per cent of 1.0 means the size assumptions are about right,
    and a factor far from 1.0 would mean they are not and the district split
    should not be trusted.
    """
    assumed = sum(d.population_2011 / HOUSEHOLD_SIZE[d.terrain] for d in D.DISTRICTS)
    return assumed / D.STATE_HOUSEHOLDS_2011


HOUSEHOLD_CALIBRATION = _household_size_calibration()


def analyse() -> list[BuiltForm]:
    nodes = H.nodes()
    out: list[BuiltForm] = []

    for d in D.DISTRICTS:
        size = HOUSEHOLD_SIZE[d.terrain] * HOUSEHOLD_CALIBRATION
        households = int(round(d.population_2011 / size))

        urban_hh = households * d.urban_fraction
        rural_hh = households - urban_hh
        residential_m2 = (rural_hh * FOOTPRINT_RURAL[d.terrain]
                          + urban_hh * FOOTPRINT_URBAN)
        built_up_km2 = residential_m2 * NONRESIDENTIAL_MULTIPLIER[d.terrain] / 1e6

        buildable = d.area_km2 * d.habitable_fraction
        share = D.FLOODPLAIN_SHARE_OF_HABITABLE[d.terrain]

        reach = FR.governing_reach(d)
        n = nodes[reach.node]
        st = H.flow_state(H.design_flood(n.total_area_km2, 100, n.cv), reach)

        out.append(BuiltForm(
            district=d,
            households=households,
            buildable_km2=buildable,
            built_up_km2=built_up_km2,
            raw_density=d.population_2011 / d.area_km2,
            buildable_density=d.population_2011 / buildable if buildable else 0.0,
            built_up_ratio=100.0 * built_up_km2 / buildable if buildable else 0.0,
            corridor_dwellings=int(round(households * share)),
            corridor_built_up_km2=built_up_km2 * share,
            unit_power=st.unit_stream_power_w_per_m2,
        ))
    return out


def _rule(char: str = "=", n: int = 78) -> str:
    return char * n


def main() -> None:
    results = analyse()
    total_hh = sum(b.households for b in results)
    total_buildable = sum(b.buildable_km2 for b in results)
    total_built = sum(b.built_up_km2 for b in results)

    print()
    print(_rule())
    print("  UTTARAKHAND - CONSTRUCTION DENSITY")
    print(_rule())

    print()
    print(f"    household size calibration factor  {HOUSEHOLD_CALIBRATION:.4f}")
    print(f"    derived households                 {total_hh:>10,}")
    print(f"    Census 2011 households             {D.STATE_HOUSEHOLDS_2011:>10,}")
    print(f"    closure                            "
          f"{100.0 * (total_hh - D.STATE_HOUSEHOLDS_2011) / D.STATE_HOUSEHOLDS_2011:>9.2f}%")

    # -- 1. the density illusion ------------------------------------------
    print()
    print(_rule("-"))
    print("  1. THE DENSITY ILLUSION")
    print(_rule("-"))
    print()
    print(f"    {'District':<16}{'area':>8}{'buildable':>11}{'%':>6}"
          f"{'raw':>9}{'buildable':>11}{'ratio':>8}")
    print(f"    {'':<16}{'km2':>8}{'km2':>11}{'':>6}{'per km2':>9}{'per km2':>11}{'':>8}")
    for b in sorted(results, key=lambda x: x.buildable_density, reverse=True):
        d = b.district
        print(f"    {d.name:<16}{d.area_km2:>8,.0f}{b.buildable_km2:>11,.0f}"
              f"{100.0 * d.habitable_fraction:>6.1f}{b.raw_density:>9,.0f}"
              f"{b.buildable_density:>11,.0f}"
              f"{b.buildable_density / b.raw_density:>7.1f}x")

    state_raw = D.STATE_POPULATION_2011 / D.STATE_AREA_KM2
    state_buildable = D.STATE_POPULATION_2011 / total_buildable
    print()
    print(f"    STATE   {total_buildable:,.0f} km2 buildable = "
          f"{100.0 * total_buildable / D.STATE_AREA_KM2:.1f}% of Uttarakhand")
    print(f"            raw density        {state_raw:>7,.0f} per km2")
    print(f"            buildable density  {state_buildable:>7,.0f} per km2  "
          f"({state_buildable / state_raw:.1f}x)")
    print()
    print("    Against Census 2011 state densities:")
    for label, value in COMPARATORS:
        marker = "  <-- the quoted figure" if "usually quoted" in label else ""
        print(f"      {label:<34}{value:>6,}{marker}")
    print(f"      {'Uttarakhand, per km2 BUILDABLE':<34}{state_buildable:>6,.0f}"
          f"  <-- the real one")
    print()
    print("    On buildable land Uttarakhand is denser than Bihar. The state that")
    print("    looks half-empty is in fact one of the most crowded in India - the")
    print("    people are simply pressed into a sixth of it.")
    print()
    print("    SENSITIVITY. habitable_fraction is an estimate and this result is")
    print("    entirely at its mercy, so here is the band:")
    for mult, tag in ((0.5, "half as much buildable land"),
                      (1.0, "as assumed"),
                      (1.5, "half as much again")):
        print(f"      x{mult:<5.1f}{D.STATE_POPULATION_2011 / (total_buildable * mult):>8,.0f}"
              f" per km2   ({tag})")
    print()
    print("    Even the most generous case leaves the state denser than the national")
    print("    average. The conclusion survives the uncertainty; the exact number")
    print("    does not, and should not be quoted without this band beside it.")

    # -- 2. built-up stock -------------------------------------------------
    print()
    print(_rule("-"))
    print("  2. BUILT-UP STOCK AND ITS EXPOSURE")
    print(_rule("-"))
    print()
    print(f"    {'District':<16}{'dwellings':>11}{'built-up':>10}{'% of':>8}"
          f"{'in corridor':>13}{'corridor':>10}{'Q100 power':>12}")
    print(f"    {'':<16}{'':>11}{'km2':>10}{'buildable':>8}{'dwellings':>13}"
          f"{'km2':>10}{'W/m2':>12}")
    for b in sorted(results, key=lambda x: x.corridor_dwellings, reverse=True):
        print(f"    {b.district.name:<16}{b.households:>11,}{b.built_up_km2:>10,.1f}"
              f"{b.built_up_ratio:>8.1f}{b.corridor_dwellings:>13,}"
              f"{b.corridor_built_up_km2:>10,.1f}{b.unit_power:>12,.0f}")

    corr_dw = sum(b.corridor_dwellings for b in results)
    corr_km2 = sum(b.corridor_built_up_km2 for b in results)
    print()
    print(f"    Statewide {corr_dw:,} dwellings - "
          f"{100.0 * corr_dw / total_hh:.0f}% of the state's housing stock - stand on")
    print(f"    the river corridor landform, covering {corr_km2:,.0f} km2 of built-up area.")

    # dwellings sitting where the flow would destroy masonry
    lethal = [b for b in results if b.unit_power >= 1000.0]
    lethal_dw = sum(b.corridor_dwellings for b in lethal)
    print()
    print(f"    Of those, {lethal_dw:,} are in the "
          f"{len(lethal)} districts whose governing reach exceeds")
    print("    1,000 W/m2 at Q100 - the level at which masonry does not survive")
    print("    contact with the flow:")
    print("      " + ", ".join(b.district.name for b in
                               sorted(lethal, key=lambda x: x.unit_power, reverse=True)))

    # -- 3. where the growth goes -----------------------------------------
    print()
    print(_rule("-"))
    print("  3. WHERE THE CONSTRUCTION IS GOING")
    print(_rule("-"))
    print()
    print(f"    {'District':<16}{'2001-2011':>11}{'buildable':>11}{'corridor':>11}"
          f"{'Q100 power':>12}")
    print(f"    {'':<16}{'growth':>11}{'per km2':>11}{'dwellings':>11}{'W/m2':>12}")
    for b in sorted(results, key=lambda x: x.district.decadal_growth_pct, reverse=True):
        d = b.district
        print(f"    {d.name:<16}{d.decadal_growth_pct:>10.1f}%{b.buildable_density:>11,.0f}"
              f"{b.corridor_dwellings:>11,}{b.unit_power:>12,.0f}")
    print(f"    {'STATE':<16}{D.STATE_DECADAL_GROWTH_PCT:>10.1f}%")

    growing = [b for b in results if b.district.decadal_growth_pct > 20]
    shrinking = [b for b in results if b.district.decadal_growth_pct < 0]
    print()
    print("    Two things are happening at once, and they pull in opposite")
    print("    directions.")
    print()
    names = ", ".join(b.district.name for b in
                      sorted(growing, key=lambda x: -x.district.decadal_growth_pct))
    print(f"    The four fastest-growing districts are the plains and valley ones:")
    print(f"      {names}")
    print("    They grew 25-33% in a decade, and their governing reaches are the")
    print("    LOW stream power ones. Growth is going where a flood inundates")
    print("    rather than destroys.")
    print()
    print(f"    Meanwhile {' and '.join(b.district.name for b in shrinking)} LOST")
    print("    population outright. In Pauri Garhwal the split is the whole story:")
    print("    rural population fell 5.4% while urban population rose 25.4%.")
    print()
    print("    So the hills are not simply emptying. They are CONCENTRATING. People")
    print("    leaving scattered high-slope villages do not all leave the state -")
    print("    many move down to the valley-floor town, which is the one place with")
    print("    flat land, a road, a school and a job. That is the river terrace.")
    print()
    print("    A falling district population can therefore hide a rising number of")
    print("    buildings in the hazard corridor. Depopulation is not risk reduction,")
    print("    and a district-level headcount will not show the difference.")

    # -- 4. what the stock is made of -------------------------------------
    print()
    print(_rule("-"))
    print("  4. WHAT IS STANDING THERE  -  the seismic cross-link")
    print(_rule("-"))
    print()
    print("    Every one of the 13 districts is in IS 1893 Zone IV or Zone V.")
    print("    None is in Zone II or III.")
    print()
    zone_count: dict[str, list[str]] = {}
    for d in D.DISTRICTS:
        zone_count.setdefault(d.seismic_zone, []).append(d.name)
    for z in ("V", "IV/V", "IV"):
        names = zone_count.get(z, [])
        pop = sum(D.DISTRICT_BY_NAME[n].population_2011 for n in names)
        print(f"      Zone {z:<5}{len(names):>3} districts{pop:>12,} people   "
              f"{', '.join(names)}")

    print()
    print("    SeismicDelta's own building, run through seismic.py for all three")
    print("    zones - the same G+5 SMRF, nothing else changed:")
    print()
    storeys = seismic.sample_building()
    base = None
    for zone in ("II", "IV", "V"):
        r = seismic.analyse(storeys, zone=zone, soil="II", importance=1.0, r_factor=5.0)
        if base is None:
            base = r["base_shear_kn"]
        print(f"      Zone {zone:<4} Z = {seismic.ZONE_FACTOR[zone]:.2f}   "
              f"Ah = {r['ah']:.5f}   Vb = {r['base_shear_kn']:>6,.0f} kN   "
              f"{r['base_shear_kn'] / base:.2f}x Zone II")

    print()
    print("    That is the demand a Zone V building must carry - 3.6x Zone II - and")
    print("    the repo's Zone IV/Zone II comparison understates it by half again.")
    print()
    print("    But the G+5 SMRF is not what most of this stock is. The prevailing")
    print("    hill typology is random rubble stone masonry in mud mortar, which")
    print("    has effectively no lateral capacity and is the most vulnerable")
    print("    category in the BMTPC Vulnerability Atlas. Where it is being replaced,")
    print("    it is largely replaced by owner-built RC frames with no engineer,")
    print("    on cut-and-fill terraces, on the same river terrace.")
    print()
    print("    The two hazards then compound in a specific and nasty order:")
    print()
    print("      1. Cut-and-fill terracing for a level plot removes toe support")
    print("         from the slope above and loads the fill below.")
    print("      2. An earthquake cracks masonry and, more to the point,")
    print("         destabilises those cut slopes.")
    print("      3. The next monsoon puts water into the cracks and the fill.")
    print("      4. The slope fails, or the river takes the terrace, and the")
    print("         debris dams the channel.")
    print("      5. The landslide dam breaches - and section 3 of floodrisk.py")
    print("         shows what that discharge does downstream.")
    print()
    print("    Joshimath is this sequence in slow motion: a town on an old landslide")
    print("    deposit, in Zone V, above the Alaknanda, with over 800 houses cracked")
    print("    in January 2023 and more than 30 cm of subsidence measured over the")
    print("    following two years.")
    print()
    print("    Designing for Zone V and ignoring the slope and the river is not a")
    print("    partial solution. In this terrain they are one problem.")
    print()


if __name__ == "__main__":
    main()
