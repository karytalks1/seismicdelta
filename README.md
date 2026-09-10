# SeismicDelta

The same G+5 RC framed building, designed twice — Seismic Zone II and Zone IV — to measure
what the extra seismic demand actually costs in steel, concrete, and rupees.

Pure Python for the analysis. STAAD.Pro for cross-checking. No dependencies.

```bash
python seismic.py          # IS 1893:2016 base shear and storey forces
python frame2d.py          # 2D frame FE solver - storey drifts and member forces
python generate_staad.py   # writes three STAAD .std models

python hydrology.py        # Uttarakhand water flow and design floods
python floodrisk.py        # flood plain zoning and district risk index
python builtform.py        # construction density, and the seismic cross-link
```

## Why do it twice

Anyone can analyse a building. The interesting question is what *changes* when the demand
changes — and which members change at all. Running one geometry through two zones, with
everything else held fixed, isolates that.

## The building

| | |
|---|---|
| Plan | 20 m × 15 m, 5 m bays (4 × 3) |
| Storeys | G+5, 3.2 m each, 19.2 m total |
| Frame | SMRF, R = 5, importance factor 1.0 |
| Sections | Beams 300 × 450, columns 400 × 400 |
| Materials | M25 concrete, Fe500 steel |
| Soil | Type II (medium) |

## Results

**Seismic demand — IS 1893:2016 equivalent static**

| | Zone II | Zone IV |
|---|---|---|
| Fundamental period Ta | 0.688 s | 0.688 s |
| Spectral acceleration Sa/g | 1.977 | 1.977 |
| Zone factor Z | 0.10 | 0.24 |
| Design coefficient Ah | 0.01977 | 0.04745 |
| **Base shear Vb** | **409 kN** | **982 kN** |

Zone IV base shear is **2.40×** Zone II. Exactly 2.40, because every other term in
`Ah = (Z/2)(Sa/g)/(R/I)` is identical between the two runs — the ratio collapses to
`Z_IV / Z_II = 0.24 / 0.10`.

**Storey force distribution.** The roof takes **32.9%** of base shear, not the 1/6 an even
split would give. That is the `h²` term in IS 1893 Cl 7.6.3 approximating the first mode
shape — an inverted triangle of acceleration, so upper storeys attract disproportionate force.

**Drift — from the 2D frame solver**

| | Zone II | Zone IV | Limit |
|---|---|---|---|
| Max inter-storey drift | 2.86 mm | 6.88 mm | 12.8 mm |
| Governing storey | Level 2 | Level 2 | — |

Both pass with 400 × 400 columns, so **strength governs, not stiffness** — no column resize
was needed for Zone IV. Drift peaks at level 2 rather than the base because column fixity at
the foundation stiffens the ground storey.

Drift ratio is also 2.40×, as it must be: the analysis is linear elastic, so doubling the
force doubles the displacement.

## Verifying the software instead of trusting it

`seismic.py` and `frame2d.py` exist so that STAAD's answers can be checked against an
independent implementation. Most students trust the output. The point of this project is not to.

`frame2d.py` is a direct stiffness method solver written from scratch:

- 6-DOF plane frame elements (axial + bending), Euler–Bernoulli
- Local stiffness → global via rotation transformation
- Distributed loads entered as equivalent nodal loads from fixed-end forces
- Gaussian elimination with partial pivoting
- Member end forces recovered after solving

It is validated against two closed-form results before it is trusted for anything:

```
validation: cantilever PL^3/3EI  OK
validation: fixed-fixed wL^2/12  OK
```

## Generated STAAD models

`generate_staad.py` writes three `.std` files: 140 joints, 306 members, loads, the IS 1893
seismic definition, 13 load combinations, and IS 456 design commands.

Generating rather than clicking is deliberate. The comparison is only valid if the models are
identical except for the variable under study — and `diff ZoneII.std ZoneIV.std` returns
exactly two lines: the job title, and `ZONE 0.1` → `ZONE 0.24`.

Three hours of GUI modelling, done in a second, with the experimental control guaranteed.


## Uttarakhand — where that building actually stands

The seismic study above holds everything fixed and varies one thing. This second
study asks the question the first one leaves open: *what is the site actually
like?* Uttarakhand, because every one of its 13 districts is in Zone IV or Zone V
— and because the earthquake is not the only thing trying to remove the building.

Full method, sources and limitations in [`UTTARAKHAND.md`](UTTARAKHAND.md).

**Water flow.** ~46.8 km³/yr of surface water off 53,483 km². The drainage tree
is routed from incremental sub-catchments and validated against three published
control totals — Alaknanda at Devprayag 10,882 km², Pashulok barrage 21,400 km²,
Bhimgoda barrage 23,000 km². The 13 district populations sum to 10,086,292
exactly, without adjustment.

**Force, not volume, is the hazard.** At the 100-year flood:

| | discharge | width | unit stream power |
|---|---|---|---|
| Dhauliganga at Joshimath | 1,125 m³/s | 51 m | **7,543 W/m²** |
| Ganga at Haridwar | 6,399 m³/s | 2,114 m | **36 W/m²** |

Six times the discharge, one two-hundredth the intensity. Slope does that. One
inundates buildings; the other removes them — and they need different rules.

**The zoning line is drawn for the wrong event.** Uttarakhand enacted the CWC
Model Bill as the Flood Plain Zoning Act, 2012 — one of only four states to do so.
But the Bill manages risk by mapping a wider line for a rarer flood, and a gorge
cannot widen: Himalayan reaches grow **1.06×** from the 25-year zone to the
100-year zone, against **5.13×** in the Terai. Zone A and Zone C are nearly the
same ground.

And the return period is measuring the wrong process. Above Kedarnath the
100-year flood is 77 m³/s. On 17 June 2013 the observed peak was **1,699 m³/s —
22× the 100-year flood**, because a moraine dam failed and released volume that
was in storage, not in the rainfall. Modelled with Evans (1986) plus a debris
bulking factor of 2.0 it comes back at 1,677 m³/s, within −1.3% — which says the
mechanism is right, not that the model is accurate.

**Dickens' formula was checked, not trusted.** The standard north Indian
estimator with the textbook hill coefficient overpredicts this basin's 100-year
flood by **4.5–6× at every scale from 45 km² to 23,000 km²**. The implied C is
3.4–4.5 — the *plains* band. C = 14–28 is an envelope of maximum observed floods,
and an envelope is not a 100-year estimate.

**Construction density — the number everyone quotes is wrong.**

| | per km² |
|---|---|
| Uttarakhand, as always quoted | 189 |
| Bihar, densest major state | 1,106 |
| **Uttarakhand, per km² of buildable land** | **1,185** |

Only 15.9% of the state can be built on. Measured against that, Uttarakhand is
denser than Bihar. Rudraprayag looks nearly empty at 122/km²; on buildable land it
carries 1,628/km², denser than Haridwar.

And the buildable land *is* the hazard: in a steep valley the only flat ground is
the valley floor and the river terraces. **996,000 dwellings — 48% of the state's
housing stock — stand on the river-corridor landform**, ~290,000 of them in the
five districts whose governing reach exceeds 1,000 W/m², the level at which
masonry does not survive contact with the flow.

**Depopulation is not risk reduction.** Almora and Pauri Garhwal *lost* population
2001–2011. But in Pauri, rural population fell 5.4% while urban rose 25.4% — people
leaving high-slope villages move down to the valley-floor town, which is the river
terrace. A falling district headcount can hide a rising number of buildings in the
corridor.

**Back to the seismic study.** All 13 districts sit in Zone IV or V, so
`builtform.py` runs this repo's own G+5 SMRF through `seismic.py` for Zone V too:

| | Z | Vb | vs Zone II |
|---|---|---|---|
| Zone II | 0.10 | 409 kN | 1.00× |
| Zone IV | 0.24 | 982 kN | 2.40× |
| **Zone V** | 0.36 | **1,473 kN** | **3.60×** |

The headline comparison at the top of this README understates real Uttarakhand
demand by half again. And the G+5 SMRF is not what is standing there — it is
random rubble stone masonry in mud mortar, or owner-built RC on a cut-and-fill
terrace above the Alaknanda. Designing for Zone V while ignoring the slope and the
river is not a partial solution; in this terrain they are one problem.

## Loads

Per IS 875 Parts 1 and 2:

- Slab self-weight 3.125 kN/m² · floor finish 1.0 · partitions 1.0
- Live load 2.0 kN/m² typical, 1.5 kN/m² roof
- 230 mm brick wall on perimeter beams, 12.65 kN/m
- Seismic weight = full dead load + 25% live load (IS 1893 Cl 7.3.1), roof live excluded

Load combinations per IS 1893 Cl 6.3.1.2, including `0.9 DL ± 1.5 EL` — the case that checks
column uplift and is the one most often forgotten.

## In progress

- [ ] STAAD runs, both zones, cross-checked against `seismic.py`
- [ ] Soft-storey case — open ground floor for stilt parking, the classic Indian failure mode.
      Storey stiffness check per IS 1893 Cl 7.1, then the 2.5× force factor of Cl 7.10
- [ ] Hand design of one critical beam and column to IS 456, compared against STAAD
- [ ] IS 13920 ductile detailing — R = 5 was claimed, so the detailing is owed
- [ ] Bar Bending Schedule and DSR rate analysis, both zones
- [ ] Feed the Zone IV BBS into [RebarOpt](../rebaropt) to quantify cutting waste

## Files

| File | What it does |
|---|---|
| `seismic.py` | IS 1893:2016 — period, spectrum, Ah, base shear, storey distribution |
| `frame2d.py` | Direct stiffness 2D frame solver, with validation tests |
| `generate_staad.py` | Parametric STAAD `.std` generation for all three models |
| `BUILD_SPEC.md` | Full method: loads, code clauses, hand-design procedure |
| `staad/` | Generated model files |
| `uk_data.py` | Uttarakhand dataset — districts, drainage tree, reaches, with `[M]`/`[E]` provenance and closure checks |
| `hydrology.py` | Flow routing, water balance, design floods, compound-section hydraulics, wave travel time |
| `floodrisk.py` | Flood plain zoning, moraine-breach scenarios, district Hazard × Exposure × Vulnerability index |
| `builtform.py` | Construction density on buildable land, corridor exposure, seismic cross-link |
| `UTTARAKHAND.md` | Full method, sources and limitations for the Uttarakhand study |

## Codes

IS 1893 (Part 1) : 2016 · IS 456 : 2000 · IS 875 (Parts 1 and 2) · IS 13920 : 2016

For the Uttarakhand study: Model Bill for Flood Plain Zoning (CWC, 1975) ·
Uttarakhand Flood Plain Zoning Act, 2012 · Census of India 2011 · CWC Upper Ganga
Basin Organisation · FSI ISFR 2019 · BMTPC Vulnerability Atlas of India
