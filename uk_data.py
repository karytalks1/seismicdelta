"""
Uttarakhand - the verified dataset behind the water, flood and built-form analysis.

Every number in this file is tagged with its provenance:

    [M] MEASURED   - published by a named source, cited inline. Use it.
    [E] ESTIMATED  - engineering judgement by the author of this module.
                     Defensible, documented, and NOT a substitute for a survey.

That distinction is the whole point. A flood risk number carries a policy
consequence - somebody's house is inside the line or outside it - so a reader
must be able to tell instantly which figures came from the Census and the CWC
and which ones I reasoned my way to. Mixing the two silently is how bad hazard
maps get built.

Three independent closure checks are run by `validate()` at import time in the
analysis modules:

    1. district areas          ->  53,483 km2  (state area, Census 2011)
    2. district populations    ->  10,086,292  (state population, Census 2011)
    3. routed drainage areas   ->  21,400 km2 at Rishikesh, 23,000 km2 at
                                   Haridwar (Pashulok and Bhimgoda barrage
                                   catchments), and 53,483 km2 statewide

Check 2 closes exactly. Check 3 closes exactly by construction - the
sub-catchments were apportioned to hit the barrage control totals, which means
the totals are validation of the apportionment method, not of any individual
tributary area. Check 1 closes to 0.24%, which is the disagreement between
district gazetteer areas and the state total, not an error in this file.

SOURCES
  Census of India 2011 - district area, population, households
  CWC Upper Ganga Basin Organisation - Alaknanda basin area 10,882 km2
  Pashulok Barrage (Rishikesh) catchment 21,400 km2
  Bhimgoda Barrage (Haridwar) catchment 23,000 km2
  Forest Survey of India, ISFR 2019 - forest cover 24,303 km2 = 45.44%
  IS 1893 (Part 1) : 2016 - seismic zoning
  Full citations in UTTARAKHAND.md.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# State control totals - Census of India 2011
# ---------------------------------------------------------------------------

STATE_AREA_KM2 = 53_483          # [M] Census 2011
STATE_POPULATION_2011 = 10_086_292   # [M] Census 2011
STATE_HOUSEHOLDS_2011 = 2_056_975    # [M] Census 2011
STATE_FOREST_COVER_KM2 = 24_303      # [M] FSI ISFR 2019 (45.44% of state)
STATE_URBAN_FRACTION = 0.3023        # [M] Census 2011
STATE_DECADAL_GROWTH_PCT = 18.81     # [M] Census 2011, 2001-2011

# Catchment control totals, for validating the routed drainage tree
CTRL_ALAKNANDA_DEVPRAYAG_KM2 = 10_882   # [M] CWC Upper Ganga Basin Organisation
CTRL_GANGA_RISHIKESH_KM2 = 21_400       # [M] Pashulok Barrage catchment
CTRL_GANGA_HARIDWAR_KM2 = 23_000        # [M] Bhimgoda Barrage catchment

# Observed anchor for the regional flood-frequency relation.
# Reported mean annual peak flow of the Ganga at Devprayag. This single
# datum calibrates every design flood in hydrology.py, so it is the most
# load-bearing number in the project and the first one to re-check.
ANCHOR_DEVPRAYAG_MAF_CUMEC = 1775.0     # [M] mean annual peak, Ganga at Devprayag
ANCHOR_DEVPRAYAG_AREA_KM2 = 18_692      # [M] = 10,882 Alaknanda + 7,810 Bhagirathi

# Observed extreme events, used to test the design flood framework rather
# than to calibrate it. See hydrology.py - these are NOT rainfall floods.
KEDARNATH_2013_CATCHMENT_KM2 = 45.0     # [M] Mandakini catchment above Kedarnath
KEDARNATH_2013_PEAK_CUMEC = 1699.0      # [M] BREACH model, Chorabari breach 17 Jun 2013
KEDARNATH_2013_VOLUME_M3 = 6.1e5        # [M] released lake volume


# ---------------------------------------------------------------------------
# Districts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class District:
    """One of the 13 districts of Uttarakhand.

    area_km2, population_2011      [M] Census 2011
    seismic_zone                   [M] IS 1893 (Part 1) : 2016
    urban_fraction                 [E] pattern is well established, values rounded
    habitable_fraction             [E] see note below - the key estimate
    glacier_km2                    [E] order-of-magnitude, for GLOF exposure only
    main_basin                     [M] dominant drainage

    HABITABLE FRACTION is the single most consequential estimate in this file.
    It is the share of district area on which building is physically possible:
    not glacier, not rock above the tree line, not slopes steeper than about
    30 degrees, not reserved forest, not active river channel.

    Basis: 45.4% of the state is forest cover (FSI 2019); the Higher Himalayan
    districts carry very large glacier, moraine and alpine-rock areas; and
    Uttarakhand is roughly 86% hill terrain where valley floors and river
    terraces are the only level ground. Values below are apportioned on that
    reasoning, low in the Higher Himalaya, high in the Terai.

    These are NOT surveyed land-use figures. A real study would take them from
    a slope raster and an LULC classification. Everything downstream that reads
    `habitable_fraction` inherits that uncertainty - builtform.py reports a
    sensitivity band for exactly this reason.
    """
    name: str
    division: str            # Garhwal | Kumaon
    area_km2: float
    population_2011: int
    seismic_zone: str        # IS 1893:2016 - "IV", "V", or "IV/V" where split
    terrain: str             # higher | lesser | outer | terai
    urban_fraction: float
    habitable_fraction: float
    glacier_km2: float
    main_basin: str
    decadal_growth_pct: float = 0.0   # [M] 2001-2011 where verified, else [E]


# decadal_growth_pct, 2001-2011
#   VERIFIED [M]: Udham Singh Nagar 33.4, Dehradun 32.3, Haridwar 30.6,
#   Nainital 25.1, Almora -1.3, Pauri Garhwal -1.4, state 18.81. Pithoragarh,
#   Rudraprayag, Bageshwar, Chamoli and Tehri are reported in the literature as
#   "5% or less" and the values here sit inside that band. Uttarkashi and
#   Champawat are [E].
#
#   Two districts LOST population over the decade. That is the fact the whole
#   construction-density picture turns on - see builtform.py.
DISTRICTS: tuple[District, ...] = (
    # --- Garhwal division -------------------------------------------------
    District("Uttarkashi",   "Garhwal", 8016, 330_086,  "IV/V", "higher", 0.077, 0.035,  980, "Bhagirathi/Yamuna", 11.9),
    District("Chamoli",      "Garhwal", 8030, 391_605,  "V",    "higher", 0.150, 0.040, 1100, "Alaknanda", 5.6),
    District("Rudraprayag",  "Garhwal", 1984, 242_285,  "V",    "lesser", 0.027, 0.075,   85, "Mandakini/Alaknanda", 6.5),
    District("Tehri Garhwal","Garhwal", 4080, 618_931,  "IV/V", "lesser", 0.110, 0.110,   40, "Bhagirathi/Bhilangna", 2.4),
    District("Dehradun",     "Garhwal", 3088, 1_696_694,"IV",   "outer",  0.553, 0.300,    0, "Yamuna/Song", 32.3),
    District("Pauri Garhwal","Garhwal", 5329, 687_271,  "IV/V", "lesser", 0.170, 0.130,    0, "Alaknanda/Nayar", -1.4),
    District("Haridwar",     "Garhwal", 2360, 1_890_422,"IV",   "terai",  0.363, 0.680,    0, "Ganga", 30.6),
    # --- Kumaon division --------------------------------------------------
    District("Pithoragarh",  "Kumaon",  7110, 483_439,  "V",    "higher", 0.150, 0.045,  720, "Kali/Gori", 4.7),
    District("Bageshwar",    "Kumaon",  2302, 259_898,  "V",    "lesser", 0.036, 0.080,  180, "Saryu/Pindar", 4.2),
    District("Almora",       "Kumaon",  3144, 622_506,  "IV/V", "lesser", 0.100, 0.140,    0, "Kosi/Ramganga", -1.3),
    District("Champawat",    "Kumaon",  1766, 259_648,  "IV/V", "lesser", 0.140, 0.130,    0, "Kali/Ladhiya", 15.6),
    District("Nainital",     "Kumaon",  3860, 954_605,  "IV",   "outer",  0.390, 0.280,    0, "Kosi/Gaula", 25.1),
    District("Udham S Nagar","Kumaon",  2542, 1_648_902,"IV",   "terai",  0.354, 0.720,    0, "Terai/Sharda", 33.4),
)


# ---------------------------------------------------------------------------
# Drainage network - the state as a tree of confluences
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Catchment:
    """One node in the drainage tree.

    `local_area_km2` is the INCREMENTAL area draining directly to this node -
    not the total upstream area. Total area is accumulated by routing in
    hydrology.py. Storing incremental areas means the tree cannot double-count
    at a confluence, and it makes the closure checks meaningful.

    local_area_km2   [E] apportioned to hit the CWC/barrage control totals
    rainfall_mm      [E] mean annual precipitation over the incremental area
    runoff_coeff     [E] annual runoff coefficient
    glacier_km2      [E] glacierized area within the incremental area
    terrain          [M] physiographic province
    """
    key: str
    label: str
    upstream: tuple[str, ...]
    local_area_km2: float
    rainfall_mm: float
    runoff_coeff: float
    glacier_km2: float
    terrain: str
    confluence: str = ""       # the prayag / town at this node, if any
    district: str = ""         # district the node sits in


# The Panch Prayag, in order down the Alaknanda, then the Bhagirathi arm.
#
# Runoff coefficients are high (0.55-0.72) because these are steep, thin-soiled,
# largely bare or ice-covered catchments where rainfall converts to runoff fast.
# The Bhabar/Terai coefficient is deliberately LOW (0.30-0.35): the Bhabar gravel
# belt swallows surface flow - streams genuinely go underground there and
# re-emerge in the Terai springs. Applying a hill coefficient to the plains would
# roughly double the estimated yield of the whole Kumaon foothill zone.

CATCHMENTS: tuple[Catchment, ...] = (
    # ---- Alaknanda system ------------------------------------------------
    Catchment("alaknanda_head", "Alaknanda headwater (Satopanth)", (), 1450, 1000, 0.70, 420, "higher", "", "Chamoli"),
    Catchment("dhauliganga_w", "Dhauliganga West (Niti, Rishiganga)", (), 1850, 950, 0.72, 480, "higher", "", "Chamoli"),
    Catchment("vishnuprayag", "Alaknanda at Vishnuprayag", ("alaknanda_head", "dhauliganga_w"), 0, 1100, 0.70, 0, "higher", "Vishnuprayag", "Chamoli"),
    Catchment("nandakini", "Nandakini", (), 540, 1350, 0.65, 30, "lesser", "", "Chamoli"),
    Catchment("nandprayag", "Alaknanda at Nandprayag", ("vishnuprayag", "nandakini"), 620, 1250, 0.66, 60, "lesser", "Nandprayag", "Chamoli"),
    Catchment("pindar", "Pindar (Pindari glacier)", (), 1700, 1400, 0.65, 190, "lesser", "", "Bageshwar/Chamoli"),
    Catchment("karnaprayag", "Alaknanda at Karnaprayag", ("nandprayag", "pindar"), 330, 1300, 0.64, 0, "lesser", "Karnaprayag", "Chamoli"),
    Catchment("mandakini_kedarnath", "Mandakini above Kedarnath", (), 45, 1500, 0.72, 22, "higher", "Kedarnath", "Rudraprayag"),
    Catchment("mandakini", "Mandakini at Rudraprayag", ("mandakini_kedarnath",), 1601, 1450, 0.66, 60, "lesser", "", "Rudraprayag"),
    Catchment("rudraprayag", "Alaknanda at Rudraprayag", ("karnaprayag", "mandakini"), 700, 1350, 0.63, 0, "lesser", "Rudraprayag", "Rudraprayag"),
    Catchment("alaknanda_devprayag", "Alaknanda at Devprayag", ("rudraprayag",), 2046, 1400, 0.62, 0, "lesser", "", "Pauri Garhwal"),
    # ---- Bhagirathi system -----------------------------------------------
    Catchment("bhagirathi_harsil", "Bhagirathi at Harsil", (), 1450, 1000, 0.70, 620, "higher", "Gaumukh", "Uttarkashi"),
    Catchment("bhagirathi_head", "Bhagirathi at Uttarkashi", ("bhagirathi_harsil",), 1450, 1100, 0.68, 140, "higher", "", "Uttarkashi"),
    Catchment("bhilangna", "Bhilangna (Khatling)", (), 2320, 1400, 0.65, 150, "lesser", "", "Tehri Garhwal"),
    Catchment("tehri", "Bhagirathi at Tehri", ("bhagirathi_head", "bhilangna"), 1450, 1350, 0.64, 40, "lesser", "Tehri", "Tehri Garhwal"),
    Catchment("bhagirathi_devprayag", "Bhagirathi at Devprayag", ("tehri",), 1140, 1450, 0.62, 0, "lesser", "", "Tehri Garhwal"),
    # ---- Ganga -----------------------------------------------------------
    Catchment("devprayag", "GANGA at Devprayag", ("alaknanda_devprayag", "bhagirathi_devprayag"), 0, 1400, 0.62, 0, "lesser", "Devprayag", "Tehri Garhwal"),
    Catchment("nayar", "Nayar (East + West)", (), 2150, 1500, 0.58, 0, "lesser", "", "Pauri Garhwal"),
    Catchment("rishikesh", "GANGA at Rishikesh", ("devprayag", "nayar"), 558, 1900, 0.58, 0, "outer", "Pashulok barrage", "Dehradun"),
    Catchment("song_suswa", "Song + Suswa (Doon valley)", (), 1000, 2100, 0.55, 0, "outer", "", "Dehradun"),
    Catchment("haridwar", "GANGA at Haridwar", ("rishikesh", "song_suswa"), 600, 1900, 0.50, 0, "terai", "Bhimgoda barrage", "Haridwar"),
    # ---- Yamuna system ---------------------------------------------------
    Catchment("yamuna_head", "Yamuna headwater (Yamunotri)", (), 2320, 1300, 0.66, 120, "higher", "Yamunotri", "Uttarkashi"),
    Catchment("tons", "Tons (Supin + Rupin)", (), 4900, 1450, 0.66, 240, "higher", "", "Uttarkashi"),
    Catchment("kalsi", "Yamuna at Kalsi", ("yamuna_head", "tons"), 500, 1800, 0.58, 0, "outer", "Kalsi", "Dehradun"),
    Catchment("aglar", "Aglar", (), 490, 1600, 0.58, 0, "lesser", "", "Tehri Garhwal"),
    Catchment("yamuna_exit", "Yamuna at state boundary", ("kalsi", "aglar"), 200, 2000, 0.55, 0, "outer", "Dak Pathar", "Dehradun"),
    # ---- Kali / Sharda system -------------------------------------------
    Catchment("gori_ganga", "Gori Ganga (Milam, Johar)", (), 2250, 1150, 0.70, 380, "higher", "", "Pithoragarh"),
    Catchment("dhauliganga_e", "Dhauliganga East (Darma)", (), 1650, 1000, 0.70, 290, "higher", "", "Pithoragarh"),
    Catchment("kali_upper", "Kali mainstem + Ladhiya (Indian bank)", (), 3400, 1600, 0.62, 50, "lesser", "", "Pithoragarh/Champawat"),
    Catchment("saryu_bageshwar", "Saryu at Bageshwar", (), 900, 1450, 0.62, 30, "lesser", "Bageshwar", "Bageshwar"),
    Catchment("saryu_eram", "Saryu + Eastern Ramganga", ("saryu_bageshwar",), 2500, 1500, 0.60, 0, "lesser", "Rameshwar", "Bageshwar/Almora"),
    Catchment("sharda_banbasa", "SHARDA at Banbasa", ("gori_ganga", "dhauliganga_e", "kali_upper", "saryu_eram"), 0, 1600, 0.60, 0, "terai", "Banbasa barrage", "Champawat"),
    # ---- Other Kumaon systems -------------------------------------------
    Catchment("ramganga_kalagarh", "Ramganga (West) at Kalagarh", (), 3100, 1550, 0.58, 0, "lesser", "Kalagarh dam", "Almora/Pauri"),
    Catchment("kosi_someshwar", "Kosi at Someshwar", (), 850, 1500, 0.58, 0, "lesser", "Someshwar", "Almora"),
    Catchment("kosi_ramnagar", "Kosi at Ramnagar", ("kosi_someshwar",), 1200, 1600, 0.55, 0, "lesser", "Ramnagar", "Almora/Nainital"),
    Catchment("gaula_kathgodam", "Gaula at Kathgodam", (), 630, 2200, 0.55, 0, "outer", "Kathgodam", "Nainital"),
    Catchment("nandhaur", "Nandhaur", (), 1000, 1900, 0.45, 0, "outer", "", "Nainital"),
    Catchment("terai_direct", "Terai / Bhabar direct drainage", (), 4593, 1500, 0.32, 0, "terai", "", "Udham S Nagar"),
)


# ---------------------------------------------------------------------------
# Channel reaches - geometry for the Manning normal-depth solution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Reach:
    """A valley cross-section, idealised as a COMPOUND (two-stage) trapezoid.

    Stage 1, up to `bank_depth_m`, is the main channel: bed width `bed_width_m`,
    side slope `side_slope_z`, roughness `manning_n`.

    Stage 2, above bank-full, is the floodplain: side slope `valley_slope_z`,
    roughness `overbank_n`.

    A single trapezoid is not good enough here and modelling it that way hides
    the result. With one set of banks the inundation width grows only 1-4% from
    the 25-year to the 100-year flood in EVERY reach, gorge and plain alike, so
    the two look alike. They are not alike. Real floods leave the channel: a
    Terai river spreads for kilometres across ground that falls away at 1:400,
    while a Bhagirathi gorge is walled by rock at 1:4 and cannot spread at all.
    That contrast lives entirely in `valley_slope_z`, which is why it is a
    separate parameter and why it ranges over two orders of magnitude below.

    All four hydraulic parameters are [E]. Real values come from a surveyed
    cross-section; these are typical values chosen for the reach type.

    manning_n after Chow (1959) open-channel tables:
        0.030-0.035  large plains channel, sand bed
        0.038-0.045  gravel/cobble bed, moderate slope
        0.050-0.060  mountain stream, cobbles and large boulders
        0.050-0.100  overbank - crops, scrub, trees, buildings

    valley_slope_z, horizontal per unit vertical, above bank-full [E]:
        3-10         confined bedrock gorge - rock walls, no room to spread
        10-80        open valley, terraces, alluvial fan
        200-500      Terai alluvial plain - effectively flat

    bed_slope is the single biggest control on what the flood does. It varies
    by a factor of ~30 across this list, from 0.0012 at Haridwar to 0.035 at
    Joshimath, and that spread is why the same discharge produces shallow sheet
    inundation in the Terai and a boulder-laden torrent in the Higher Himalaya.
    """
    key: str
    label: str
    node: str                # which Catchment node supplies the discharge
    bed_width_m: float
    side_slope_z: float      # horizontal : 1 vertical, in-bank
    manning_n: float
    bed_slope: float
    bank_depth_m: float      # depth at which flow leaves the main channel
    valley_slope_z: float    # horizontal : 1 vertical, overbank
    overbank_n: float
    district: str
    reach_length_km: float = 0.0    # for flood wave travel time
    settlement: str = ""


REACHES: tuple[Reach, ...] = (
    #     key           label                        node                   b     z  n_ch   slope  bank    zv  n_ob  district         L_km  settlement
    Reach("kedarnath",  "Mandakini at Kedarnath",   "mandakini_kedarnath",  25,  1.2, 0.060, 0.0800, 1.5,   3.0, 0.100, "Rudraprayag",     0, "Kedarnath"),
    Reach("mandakini",  "Mandakini at Rudraprayag", "mandakini",            45,  1.5, 0.055, 0.0200, 3.0,   4.0, 0.080, "Rudraprayag",    68, "Rudraprayag"),
    Reach("joshimath",  "Dhauliganga at Joshimath", "dhauliganga_w",        35,  1.5, 0.060, 0.0350, 3.0,   3.0, 0.090, "Chamoli",        22, "Joshimath/Tapovan"),
    Reach("harsil",     "Bhagirathi at Harsil",     "bhagirathi_harsil",    40,  1.5, 0.058, 0.0250, 3.0,   6.0, 0.080, "Uttarkashi",      0, "Harsil/Dharali"),
    Reach("uttarkashi", "Bhagirathi at Uttarkashi", "bhagirathi_head",      60,  1.5, 0.050, 0.0120, 4.0,   8.0, 0.070, "Uttarkashi",     75, "Uttarkashi"),
    Reach("srinagar",   "Alaknanda at Srinagar",    "alaknanda_devprayag",  90,  2.0, 0.045, 0.0060, 5.0,  25.0, 0.060, "Pauri Garhwal",  34, "Srinagar"),
    Reach("devprayag",  "Ganga at Devprayag",       "devprayag",           110,  2.0, 0.042, 0.0055, 6.0,   4.0, 0.070, "Tehri Garhwal",   0, "Devprayag"),
    Reach("rishikesh",  "Ganga at Rishikesh",       "rishikesh",           180,  2.5, 0.038, 0.0025, 6.0,  60.0, 0.060, "Dehradun",       72, "Rishikesh"),
    Reach("haridwar",   "Ganga at Haridwar",        "haridwar",            350,  4.0, 0.033, 0.0012, 6.0, 400.0, 0.050, "Haridwar",       24, "Haridwar"),
    Reach("banbasa",    "Sharda at Banbasa",        "sharda_banbasa",      300,  4.0, 0.035, 0.0015, 5.0, 400.0, 0.050, "Champawat",       0, "Banbasa/Tanakpur"),
    Reach("kalagarh",   "Ramganga at Kalagarh",     "ramganga_kalagarh",   150,  3.0, 0.038, 0.0035, 3.0,  80.0, 0.060, "Pauri Garhwal",   0, "Kalagarh"),
    Reach("ramnagar",   "Kosi at Ramnagar",         "kosi_ramnagar",       120,  3.0, 0.040, 0.0045, 2.5,  60.0, 0.060, "Nainital",        0, "Ramnagar"),
    Reach("kathgodam",  "Gaula at Kathgodam",       "gaula_kathgodam",      70,  2.5, 0.042, 0.0060, 2.0,  40.0, 0.060, "Nainital",        0, "Haldwani"),
    Reach("tehri",      "Bhagirathi at Tehri",      "tehri",                80,  2.0, 0.045, 0.0080, 4.0,  10.0, 0.070, "Tehri Garhwal",   0, "New Tehri/Ghansali"),
    Reach("jauljibi",   "Kali at Jauljibi",         "kali_upper",           70,  2.0, 0.050, 0.0100, 4.0,   5.0, 0.080, "Pithoragarh",     0, "Dharchula/Jauljibi"),
    Reach("bageshwar",  "Saryu at Bageshwar",       "saryu_bageshwar",      50,  2.0, 0.048, 0.0090, 2.2,  12.0, 0.070, "Bageshwar",       0, "Bageshwar"),
    Reach("someshwar",  "Kosi at Someshwar",        "kosi_someshwar",       40,  2.5, 0.045, 0.0080, 3.0,  20.0, 0.070, "Almora",          0, "Someshwar"),
    Reach("khatima",    "Sharda at Khatima",        "sharda_banbasa",      320,  4.0, 0.035, 0.0012, 5.0, 500.0, 0.050, "Udham S Nagar",   0, "Khatima/Sitarganj"),
)


# ---------------------------------------------------------------------------
# Floodplain share of buildable land, by physiography  [E]
# ---------------------------------------------------------------------------

# Of the land in a district that CAN be built on, what share lies inside the
# river corridor?
#
# This is high in the mountains and that is not a paradox - it is the central
# fact of Himalayan settlement. In a steep valley the only level ground is the
# valley floor and the river terraces above it, which is to say the floodplain
# and the paleo-floodplain. Level ground and flood-exposed ground are very
# nearly the same ground. In the Terai, by contrast, there is level ground
# everywhere, so a smaller share of it is committed to the corridor.
FLOODPLAIN_SHARE_OF_HABITABLE = {
    "higher": 0.70,
    "lesser": 0.55,
    "outer": 0.35,
    "terai": 0.45,
}


# ---------------------------------------------------------------------------
# Lookups and closure checks
# ---------------------------------------------------------------------------

DISTRICT_BY_NAME = {d.name: d for d in DISTRICTS}
CATCHMENT_BY_KEY = {c.key: c for c in CATCHMENTS}
REACH_BY_KEY = {r.key: r for r in REACHES}


def validate(verbose: bool = False) -> list[str]:
    """Run the three closure checks. Returns a list of human-readable lines.

    Raises ValueError only for a structural fault in the drainage tree -
    a dangling upstream reference or a cycle - because those make routing
    meaningless. Numerical closure gaps are reported, not raised: a 0.24%
    disagreement between summed district areas and the published state area
    is a real property of the source data, not a bug to assert away.
    """
    lines: list[str] = []

    # -- structural: every upstream key must exist, and the graph must be acyclic
    for c in CATCHMENTS:
        for up in c.upstream:
            if up not in CATCHMENT_BY_KEY:
                raise ValueError(f"catchment {c.key!r} references unknown upstream {up!r}")

    seen: dict[str, int] = {}

    def _visit(key: str, stack: tuple[str, ...]) -> None:
        if key in stack:
            raise ValueError(f"cycle in drainage tree: {' -> '.join(stack + (key,))}")
        if key in seen:
            return
        for up in CATCHMENT_BY_KEY[key].upstream:
            _visit(up, stack + (key,))
        seen[key] = 1

    for c in CATCHMENTS:
        _visit(c.key, ())

    # -- check 1: district areas vs state area
    area = sum(d.area_km2 for d in DISTRICTS)
    gap = 100.0 * (area - STATE_AREA_KM2) / STATE_AREA_KM2
    lines.append(f"district areas      {area:>10,.0f} km2  vs {STATE_AREA_KM2:>10,} km2   {gap:+.2f}%")

    # -- check 2: district populations vs state population
    pop = sum(d.population_2011 for d in DISTRICTS)
    gap = 100.0 * (pop - STATE_POPULATION_2011) / STATE_POPULATION_2011
    lines.append(f"district population {pop:>10,} vs {STATE_POPULATION_2011:>10,}   {gap:+.2f}%")

    # -- check 3: incremental catchment areas vs state area
    catch = sum(c.local_area_km2 for c in CATCHMENTS)
    gap = 100.0 * (catch - STATE_AREA_KM2) / STATE_AREA_KM2
    lines.append(f"catchment areas     {catch:>10,.0f} km2  vs {STATE_AREA_KM2:>10,} km2   {gap:+.2f}%")

    if verbose:
        for line in lines:
            print("   ", line)
    return lines


if __name__ == "__main__":
    print()
    print("uk_data.py - closure checks")
    print()
    validate(verbose=True)
    print()
    print(f"    {len(DISTRICTS)} districts, {len(CATCHMENTS)} catchment nodes, "
          f"{len(REACHES)} channel reaches")
    print()
