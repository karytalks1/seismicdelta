# Uttarakhand — water flow, flood plain risk, and construction density

A screening analysis of where water goes in Uttarakhand, where flooding threatens
what, and what has been built in the way. Same rules as the rest of this repo:
pure Python, no dependencies, every coefficient traceable, and the software
checked against something independent rather than trusted.

```bash
python uk_data.py     # the dataset, and its three closure checks
python hydrology.py   # routing, yield, design floods, hydraulics, travel time
python floodrisk.py   # flood plain zoning and the district risk index
python builtform.py   # construction density and the seismic cross-link
```

---

## The three questions, and the short answers

**Where does the water go?** Uttarakhand yields about **46.8 km³/yr** of surface
water off 53,483 km². Two systems dominate: the Ganga headwaters (Bhagirathi +
Alaknanda, meeting at Devprayag, 23,000 km² by the time the river leaves the
hills at Haridwar) and the Kali/Sharda on the Nepal border. Yield falls from
~29 L/s/km² in the glaciated headwaters to ~15 in the Bhabar, because the
foothill gravel belt swallows surface flow into the aquifer.

**How bad is the flood risk, and where?** The three highest-risk districts are
**Pithoragarh, Chamoli and Rudraprayag** — and the ranking is driven by force,
not by volume. At the 100-year flood the Dhauliganga at Joshimath delivers
**7,543 W/m²** of unit stream power; the Ganga at Haridwar, carrying six times
the discharge, delivers **36 W/m²**. A factor of 210. One inundates buildings.
The other removes them.

**How much is built there?** About **996,000 dwellings — 48% of the state's
housing stock — stand on the river-corridor landform**, and roughly 290,000 of
those are in the five districts whose governing reach exceeds 1,000 W/m², the
threshold above which masonry does not survive contact with the flow.

And the finding that reframes all three: **Uttarakhand's real settlement density
is about 1,185 people per km² of buildable land**, against the 189/km² that is
always quoted. That is denser than Bihar, the densest major state in India. The
state is not empty. It is one of the most crowded places in the country,
compressed onto a sixth of its area — and that sixth is largely the valley floors
and river terraces, which is to say the floodplain.

---

## Method, and why each choice was made

### 1. The drainage tree

The state is modelled as 38 catchment nodes carrying **incremental** area, routed
depth-first to accumulate totals at each confluence. Incremental rather than
total area is the point: a tree of incremental areas cannot double-count at a
confluence, and it makes the closure checks meaningful.

Three closure checks run on every execution:

| check | result |
|---|---|
| district areas vs Census state area | +0.24% |
| district populations vs Census state population | **exact** |
| incremental catchment areas vs state area | **exact** |

Plus routing validation against independently published catchments: Alaknanda at
Devprayag 10,882 km² (CWC), Ganga at Rishikesh 21,400 km² (Pashulok barrage),
Ganga at Haridwar 23,000 km² (Bhimgoda barrage).

**These three close to zero by construction** — the sub-catchments were
apportioned to hit them. They validate the routing arithmetic and the topology,
not the area of any individual tributary. That distinction is stated in the code
output too, because a validation that validates nothing is worse than none.

The population check closing *exactly* is the real one: 13 independently sourced
district figures summing to 10,086,292 without adjustment.

### 2. Design floods — and why Dickens was checked rather than used

Design peaks come from the index-flood method: a regional relation
`MAF = 1.491 × A^0.72`, calibrated on one observed datum (mean annual peak of the
Ganga at Devprayag, 1,775 m³/s over 18,692 km²), scaled by Gumbel EV1 growth
factors with an area-weighted coefficient of variation.

One anchor fits one parameter. The exponent `b = 0.72` rests on judgement alone
and is flagged as such.

Then the same peaks were computed with **Dickens' formula**, `Q = C·A^0.75`, the
empirical estimator in standard use across north India:

| | |
|---|---|
| Dickens, textbook hill coefficient C = 20 | **4.5–6× higher** at every scale from 45 km² to 23,000 km² |
| Dickens C implied by the index-flood Q100 | **3.4–4.5** — inside the *plains* band, not the hill band |

The exponent is not the problem; the coefficient is, and it is remarkably flat
across a 500-fold range of catchment area. `C = 14–28` is an envelope of maximum
observed floods on small hill catchments, and an envelope is not a 100-year
estimate. Used as one, it sizes structures for a flood far rarer than intended.

Either result can be defended. They cannot both be used, and the choice has to be
stated. That is the whole reason for running the cross-check.

### 3. Compound-section hydraulics

Normal depth is solved by bisection on Manning's equation over a **two-stage
(compound) cross-section** — a main channel below bank-full, a much flatter
floodplain above it, with the two roughnesses combined by the Horton–Einstein
equivalent-*n* rule.

A single trapezoid was tried first and had to be discarded. It gave 1–4%
inundation widening from the 25-year to the 100-year flood in *every* reach,
gorge and plain alike, which made the two look identical. They are not identical,
and the difference is the entire argument of this study. Real floods leave the
channel: a Terai river spreads across ground falling at 1:400 while a Bhagirathi
gorge is walled by rock at 1:4 and cannot spread at all.

With the compound section:

| | Zone A → Zone C widening |
|---|---|
| Confined Himalayan reaches | **1.06×** |
| Terai reaches | **5.13×** |

### 4. The risk index

`Risk = (Hazard × Exposure × Vulnerability)^⅓`, the standard UNDRR/NDMA
decomposition. A geometric mean, so a district cannot score well on two terms and
buy its way out of the third — a hazard with nobody exposed to it is not a risk.

Two methodological corrections worth recording:

- **Score floor.** Plain min–max normalisation maps the lowest district to
  exactly zero, and zero inside a geometric mean annihilates the product. Udham
  Singh Nagar scored 0.4/100 on an early run purely because it held the minimum
  on one component. That is a scaling artifact, not a finding — the Terai floods,
  repeatedly. Scoring lowest among 13 means "least of these", never "none", so
  normalisation now runs 0.05–1.0.
- **Area-weighted Cv.** Taking the coefficient of variation from the terrain at
  the outlet gave Haridwar a *smaller* 100-year flood than Rishikesh 24 km
  upstream, because Haridwar sits on the Terai. Cv is a property of the whole
  contributing basin, so it is now area-weighted over all upstream increments.

Weights were chosen, not derived, so the ranking is also printed under equal
weights: 4 of 13 districts move. **Read the result as three or four tiers, not as
thirteen ordered places.**

---

## The central finding: the zoning line is drawn for the wrong event

Uttarakhand is one of only four Indian states to have enacted the CWC's Model
Bill for Flood Plain Zoning (1975) — the **Uttarakhand Flood Plain Zoning Act,
2012**. The legal instrument exists. The problem is what it measures.

The Model Bill manages risk by mapping a wider line for a rarer flood. On an
alluvial plain that works: the water spreads, extra discharge becomes extra area,
and the zone boundary genuinely moves. In a bedrock gorge the line barely moves
(1.06×) while the force inside it climbs. Zone A and Zone C end up being very
nearly the same ground — so a plot reclassified from A to C has not become
materially safer, it has only become legal to build on. And "regulated
construction on a raised plinth" inside Zone C is not mitigation when the plinth
stands in a boulder-laden torrent at several thousand W/m².

Worse, the return period is measuring the wrong process altogether.

**Mandakini above Kedarnath, catchment 45 km²:**

| | m³/s |
|---|---|
| 100-year rainfall flood (this model) | 77 |
| 500-year rainfall flood (this model) | 99 |
| Dickens, C = 28 — the hill envelope | 486 |
| **Observed, 17 June 2013** | **1,699** |

The observed peak was **22× the 100-year flood**, 17× the 500-year, and 3.5× even
the Dickens envelope.

The model is not wrong. It is answering a different question. Chorabari lake
released 610,000 m³ through a moraine breach — a volume that was in *storage*,
not in the rainfall. A frequency curve fitted to annual rainfall maxima cannot
contain it at any return period, because the process is a dam failure, not a
storm. The same holds for landslide-dam outburst and for rock-ice avalanche: the
Chamoli event of February 2021 happened in **winter**, with no monsoon and no rain
at all.

### The breach model, and its one validation

Peak outflow is modelled with Evans (1986), `Qp = 0.72·V^0.53`, times a debris
bulking factor of 2.0 — Himalayan outbursts entrain moraine and channel boulders
and arrive as debris flows, not as clear water.

| Chorabari breach, 17 June 2013 | |
|---|---|
| released volume | 610,000 m³ |
| Evans water-only peak | 839 m³/s |
| × debris bulking 2.0 | **1,677 m³/s** |
| observed (BREACH model) | 1,699 m³/s |
| error | **−1.3%** |

Do not read −1.3% as accuracy. The bulking factor was chosen from a plausible
range and exactly one event tests it here. Read it as evidence that the
*mechanism* is right: model an outburst as clear water and you halve the answer.

**Consequence for zoning.** In the Himalayan reaches the envelope has to come from
**geomorphology** — paleoflood terraces, debris-fan boundaries, the visible
boulder line — not from a return period. Those landforms record what has actually
happened. A frequency curve records only what the rain gauge has seen since it
was installed. And a moraine dam impounding a lake that grows as its glacier
retreats is not a stationary process, which is the assumption frequency analysis
is built on.

### Warning lead time

Kinematic wave travel times, computed as upper bounds — they assume the wave is
detected the instant it forms:

| reach | lead time |
|---|---|
| Dhauliganga → Joshimath (22 km) | **34 min** |
| Alaknanda → Srinagar (34 km) | 94 min |
| Mandakini → Rudraprayag (68 km) | 132 min |

Under an hour is not an evacuation window. It is barely a siren window, and only
if the siren already exists.

---

## Construction density

| | |
|---|---|
| Buildable land | **8,508 km² = 15.9%** of the state |
| Raw density | 189 per km² |
| **Density per km² of buildable land** | **1,185 per km²** (6.3×) |
| Bihar — densest major state (Census 2011) | 1,106 |
| India | 382 |

Sensitivity, because `habitable_fraction` is an estimate and this result lives or
dies by it: halving buildable land gives 2,371/km², increasing it by half gives
790/km². **Even the most generous case leaves the state denser than the national
average.** The conclusion survives the uncertainty; the exact number does not, and
should not be quoted without this band beside it.

Per district the correction is largest exactly where the terrain is worst —
Uttarkashi 28.6×, Chamoli 25.0×, Pithoragarh 22.2×. Rudraprayag looks nearly
empty at 122 people/km²; on buildable land it carries 1,628/km², **denser than
Haridwar**.

### Where the construction is going

| | 2001–2011 growth |
|---|---|
| Udham Singh Nagar, Dehradun, Haridwar, Nainital | +25% to +33% |
| Pithoragarh, Rudraprayag, Bageshwar, Chamoli, Tehri | ≤ +6.5% |
| **Almora, Pauri Garhwal** | **−1.3%, −1.4%** |

Two things are happening at once and they pull in opposite directions. Growth is
concentrated in the plains and valley districts, whose governing reaches are the
low stream-power ones — so most new building is going where a flood inundates
rather than destroys.

Meanwhile two hill districts lost population outright. But in Pauri Garhwal the
split is the whole story: **rural population fell 5.4% while urban population rose
25.4%.** The hills are not simply emptying, they are *concentrating*. People
leaving scattered high-slope villages largely move down to the valley-floor town —
the one place with flat land, a road, a school and a job. That is the river
terrace.

**A falling district population can therefore hide a rising number of buildings in
the hazard corridor.** Depopulation is not risk reduction, and a district-level
headcount will not show the difference.

### The seismic cross-link

All 13 districts are in IS 1893 Zone IV or Zone V. None is in Zone II or III.

Running SeismicDelta's own G+5 SMRF through `seismic.py` for all three zones,
nothing else changed:

| | Z | Ah | Vb | vs Zone II |
|---|---|---|---|---|
| Zone II | 0.10 | 0.01977 | 409 kN | 1.00× |
| Zone IV | 0.24 | 0.04745 | 982 kN | 2.40× |
| **Zone V** | 0.36 | 0.07117 | **1,473 kN** | **3.60×** |

The repo's headline Zone IV/Zone II comparison understates the real Uttarakhand
demand by half again.

But the G+5 SMRF is not what most of this stock is. The prevailing hill typology
is random rubble stone masonry in mud mortar — effectively no lateral capacity,
and the most vulnerable category in the BMTPC Vulnerability Atlas. Where it is
being replaced, it is largely replaced by owner-built RC frames with no engineer,
on cut-and-fill terraces, on the same river terrace.

The hazards then compound in a specific order:

1. Cut-and-fill terracing for a level plot removes toe support from the slope
   above and loads the fill below.
2. An earthquake cracks masonry and, more importantly, destabilises those cut
   slopes.
3. The next monsoon puts water into the cracks and the fill.
4. The slope fails, or the river takes the terrace, and the debris dams the
   channel.
5. The landslide dam breaches — and the scenario ladder above shows what that
   discharge does downstream.

Joshimath is this sequence in slow motion: a town on an old landslide deposit, in
Zone V, above the Alaknanda, with over 800 houses cracked in January 2023 and
more than 30 cm of subsidence measured over the following two years.

**Designing for Zone V while ignoring the slope and the river is not a partial
solution. In this terrain they are one problem.**

---

## What this is not

Read this before quoting any number.

- **No gauged flood frequency analysis.** Design floods come from a regional
  relation calibrated on *one* observed datum. A real study uses the CWC gauged
  series for each site.
- **No surveyed cross-sections.** Channel geometry is typical-value. Widths and
  depths are indicative, and the Terai widening multipliers are sensitive to the
  assumed bank depth — the gorge-versus-plain contrast is robust, the precise
  multiplier for any one plains reach is not.
- **No slope raster, no LULC classification.** `habitable_fraction` is the
  dominant estimate in the whole study and is engineering judgement, not survey.
  Everything downstream inherits its uncertainty.
- **No building footprint extraction.** Built-up area is derived from Census
  household counts and assumed footprints, not from imagery.
- **The risk index is a ranking tool.** Its absolute score has no physical unit
  and no meaning outside this comparison set.
- **Individual tributary catchment areas are apportioned, not measured.** Only
  the three control totals are published values.

Nothing here should be used to site a building or draw a statutory line. This is
the screening pass that tells you where to spend the survey money — and the
argument it makes is about *method*: that a return-period floodplain line, in
this terrain, is measuring the wrong thing.

---

## Sources

**Census and administrative**
- Census of India 2011 — district areas, populations, households; state totals
  53,483 km², 10,086,292 people, 2,056,975 households, 30.23% urban, 18.81%
  decadal growth
- District decadal growth 2001–2011: Udham Singh Nagar 33.4%, Dehradun 32.3%,
  Haridwar 30.6%, Nainital 25.1%, Almora −1.3%, Pauri Garhwal −1.4%; Pauri urban
  +25.4% against rural −5.4%
- Forest Survey of India, ISFR 2019 — forest cover 24,303 km², 45.44%

**Hydrology**
- Central Water Commission, Upper Ganga Basin Organisation — Alaknanda basin
  10,882 km²
- Pashulok Barrage (Rishikesh) catchment 21,400 km²; Bhimgoda Barrage (Haridwar)
  catchment 23,000 km²
- Mean annual peak flow, Ganga at Devprayag ≈ 1,775 m³/s
- Chorabari lake breach, 17 June 2013 — released volume ≈ 6.1 × 10⁵ m³, modelled
  peak ≈ 1,699 m³/s (BREACH); Mandakini catchment above Kedarnath ≈ 45 km²

**Method and codes**
- Model Bill for Flood Plain Zoning, CWC, 1975; **Uttarakhand Flood Plain Zoning
  Act, 2012** (one of four states to enact: Manipur 1978, Rajasthan 1990, J&K
  2005, Uttarakhand 2012)
- Dickens' formula, `Q = C·A^0.75`; C = 2.8–5.6 plains, 14–28 hills
- Evans (1986), moraine-dam breach peak outflow `Qp = 0.72·V^0.53`
- Chow (1959), open-channel roughness tables; Horton–Einstein equivalent
  roughness
- Gumbel EV1 frequency factors
- IS 1893 (Part 1) : 2016 — seismic zoning; Zone V districts Chamoli,
  Rudraprayag, Bageshwar, Pithoragarh
- BMTPC Vulnerability Atlas of India — building category vulnerability
- NDMA / UNDRR — Hazard × Exposure × Vulnerability risk decomposition

**Provenance convention.** Every input in `uk_data.py` is tagged `[M]` measured
from a cited source, or `[E]` estimated by engineering judgement. A flood risk
number carries a policy consequence — somebody's house is inside the line or
outside it — so a reader must be able to tell instantly which figures came from
the Census and the CWC and which were reasoned to. Mixing the two silently is how
bad hazard maps get built.
