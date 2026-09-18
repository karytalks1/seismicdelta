# SeismicDelta

The same G+5 RC framed building, designed twice — Seismic Zone II and Zone IV — to measure
what the extra seismic demand actually costs in steel, concrete, and rupees.

Pure Python for the analysis. STAAD.Pro for cross-checking. No dependencies.

```bash
python seismic.py          # IS 1893:2016 base shear and storey forces
python frame2d.py          # 2D frame FE solver - storey drifts and member forces
python generate_staad.py   # writes three STAAD .std models
python generate_dxf.py     # AutoCAD plan + frame elevation (drawings/, see AUTOCAD_STEPS.md)
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

## Codes

IS 1893 (Part 1) : 2016 · IS 456 : 2000 · IS 875 (Parts 1 and 2) · IS 13920 : 2016
