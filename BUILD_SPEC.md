# SeismicDelta — build spec

Design the same G+5 RC frame twice, in Seismic Zone II and Zone IV, and quantify
exactly what the extra seismic demand costs in steel, concrete, and money.

**Target: 1 week.** This is the cheapest project in your portfolio and the only one
that produces a physical deliverable (drawings + BBS) a core civil interviewer can
hold.

---

## Why this project rather than "design a building"

Every civil student designs a building. Almost none design the *same* building twice
and measure the difference. The comparison is what makes it a study rather than a
homework submission, and it gives you a number to lead with:

> "Moving from Zone II to Zone IV multiplied base shear by 2.4×, but longitudinal
> steel by only X% — because gravity still governed most beams. The columns were
> where the money went."

That sentence is the project.

---

## 1. Fix the building

Use these, or your own — but **write them down and do not change them mid-project.**

| Item | Value |
|---|---|
| Plan | 20 m × 15 m |
| Bays | 4 × 5 m (X), 3 × 5 m (Y) |
| Storeys | G+5 = 6 storeys |
| Storey height | 3.2 m (total 19.2 m) |
| Slab | 125 mm two-way |
| Beams | 300 × 450 mm (start) |
| Columns | 400 × 400 mm (start) |
| Concrete | M25 |
| Steel | Fe500 |
| Soil | Type II (medium) |
| Frame type | SMRF, R = 5 |
| Importance | I = 1.0 |

Columns will almost certainly need to grow for Zone IV. **That growth is a result,
not a failure** — record the starting and final sizes.

---

## 2. Loads

**Dead (IS 875 Part 1)**
- Slab self-weight: 0.125 × 25 = 3.125 kN/m²
- Floor finish: 1.0 kN/m²
- Partition allowance: 1.0 kN/m²
- External wall on beams: 230 mm brick × 3.2 m ≈ 12 kN/m (deduct openings if you model them)

**Live (IS 875 Part 2)**
- Typical floor (residential): 2.0 kN/m²
- Roof (accessible): 1.5 kN/m²

**Seismic weight (IS 1893 Cl 7.3.1)**
- Full dead load + **25% of live load** where live ≤ 3 kN/m²
- Roof live load is **not** included

**Load combinations (IS 1893 Cl 6.3.1.2 / IS 456)**
```
1.5 (DL + LL)
1.2 (DL + LL ± EL)
1.5 (DL ± EL)
0.9 DL ± 1.5 EL
```
Apply EL in both X and Y. The `0.9 DL ± 1.5 EL` case matters — it checks uplift and
tension in columns, and it is the one students forget.

---

## 3. Run the numbers by hand first

```bash
python seismic.py
```

Gives Ta, Sa/g, Ah, base shear, and storey distribution for both zones. Edit
`sample_building()` to match your model's actual seismic weights once you have them.

**Do this before touching STAAD.** When the software later reports a base shear, you
will already know what it should be — and if it disagrees you will find out why
instead of trusting it.

Expected for the building above: Ta = 0.688 s, Zone II Vb ≈ 409 kN, Zone IV Vb ≈ 982 kN.

---

## 4. Model in STAAD.Pro or ETABS

1. Grid and geometry. Fixed supports at base.
2. Assign sections and M25 / Fe500 material.
3. Define the load cases above. Use the software's IS 1893 seismic definition, and
   enter Z, I, R, soil type, and damping explicitly.
4. Generate load combinations.
5. Run analysis. **First check: does the reported base shear match `seismic.py`?**
   Within a few percent is fine — differences come from how the software computes
   seismic weight. If it is off by more than ~10%, find out why before continuing.
6. Check storey drift ≤ 0.004 × storey height (IS 1893 Cl 7.11.1). In Zone IV this
   may govern and force bigger columns. **If it does, that is a headline finding.**
7. Run concrete design to IS 456. Extract reinforcement.
8. Save both models separately: `ZoneII.std` and `ZoneIV.std`.

**No STAAD access?** Fallback: model a single 2D plane frame by hand using the
portal or cantilever method for lateral load, and design one interior frame. Smaller
scope, still a real comparison, still defensible. Say so in the report.

---

## 5. Hand-design one beam and one column

Non-negotiable. This is what separates you from a button-clicker.

**Beam (IS 456 limit state, flexure + shear)**
- Take the worst-case moment from the software for one critical beam
- Compute `Mu,lim = 0.133 fck b d²` for Fe500 — check singly vs doubly reinforced
- Solve for `Ast`, choose a practical bar arrangement
- Check shear: `τv = Vu/(bd)` vs `τc` from Table 19, design stirrups
- Check development length and minimum/maximum steel

**Column (IS 456, axial + biaxial bending)**
- Check slenderness — short or slender
- Use SP-16 interaction charts for `Pu`, `Mux`, `Muy`
- Check the biaxial interaction equation (Cl 39.6)

**Then compare to the software output and report the % difference.** They will not
match exactly. Common reasons: rigid-zone offsets at joints, the software's moment
redistribution, and how it treats the effective flange width. **Being able to explain
the gap is worth more than closing it.**

**Ductile detailing (IS 13920)** — you claimed R = 5, which is only valid for an SMRF.
So show the special confining reinforcement at member ends, the beam-column joint
detailing, and the strong-column-weak-beam check. Declaring R = 5 and then not
detailing for ductility is a genuine safety error, and a sharp interviewer will ask.

---

## 5b. The soft-storey case — do this, it is what makes the project distinctive

Add a **third model**: Zone IV, but with the ground storey left open for stilt parking
(no infill walls at ground level, infill modelled at all storeys above).

This configuration is near-universal in Indian apartment construction and is the most
notorious collapse mechanism in the country's earthquake record — Bhuj 2001 produced
many examples. Zone comparison alone is a common student topic; **zone comparison plus
a soft-storey study is a safety finding.**

**How to model the infill.** Two options, pick one and justify it:
- **Equivalent diagonal strut** (preferred) — replace each infill panel with a
  compression-only diagonal strut. Strut width per IS 1893:2016 Cl 7.9.2.2. More
  realistic and shows you know infill contributes stiffness even though it is
  "non-structural".
- **Stiffness comparison only** — model bare frame vs frame with infill mass, and
  discuss the limitation honestly.

**What to check**
1. **Soft storey check (IS 1893 Cl 7.1, Table 6).** A storey is soft if its lateral
   stiffness is less than 70% of the storey above, or less than 80% of the average of
   the three above. Compute storey stiffness as storey shear ÷ storey drift.
2. **Drift concentration.** Compare ground-storey drift against the upper storeys.
   Expect a sharp spike — that concentration is the failure mechanism.
3. **Column demand at ground level.** Moments and shears in ground-storey columns
   versus the fully infilled model.
4. **The IS 1893 remedy (Cl 7.10).** The code requires ground-storey members to be
   designed for 2.5× the forces from a bare-frame analysis, *or* the irregularity to be
   removed by adding stiffness. Apply the 2.5 factor and report what it costs.
5. **The fix, priced.** Compare two remedies: (a) the 2.5× design multiplier, (b) adding
   shear walls or bracing at ground level. Which is cheaper? That is a real developer
   decision and a genuinely good conclusion to end a report on.

**Interview payoff**
> "The Zone II to Zone IV comparison cost X% more steel. But leaving the ground storey
> open in Zone IV concentrated Y% of total drift into one storey and triggered a soft-
> storey irregularity — which the code then penalises with a 2.5× force multiplier on
> those columns. The parking bay was more expensive than the earthquake zone."

That is a finding. The zone table alone is a homework result.

---

## 6. Quantities and cost

1. Bar Bending Schedule for one typical floor, both zones. Bar mark, diameter, shape,
   cut length, quantity.
2. Total steel (tonnes) and concrete (m³) for both zones.
3. Rate analysis using current DSR or local market rates — **cite your source.**
4. Cost delta between zones, absolute and per m² of built-up area.
5. **Feed the Zone IV BBS into RebarOpt** and report achievable cutting waste.
   That cross-link between two of your own projects is a strong moment in an interview.

---

## 7. What to record

Fill this in as you go. These are your resume numbers.

- [ ] Base shear: Zone II ___ kN, Zone IV ___ kN, ratio ___
- [ ] Max storey drift both zones, and whether drift or strength governed
- [ ] Longitudinal steel: ___ kg → ___ kg (___% increase)
- [ ] Column size: ___ → ___ mm
- [ ] Concrete volume change: ___%
- [ ] Governing load combination in each zone
- [ ] Hand calc vs software: ___% difference, and the reason
- [ ] Cost delta: ₹ ___ total, ₹ ___ per m²
- [ ] % of beams that changed at all (expect: fewer than you think)

---

## 8. Deliverable

A PDF report, 12–20 pages:

1. Building description, plans, elevations
2. Load calculations with code clauses cited
3. Seismic analysis both zones, including your `seismic.py` cross-check
4. Analysis results — base shear, drift, member forces
5. Design results and reinforcement comparison
6. Hand calculation of one beam and one column, with the software comparison
7. Ductile detailing sketches per IS 13920
8. BBS and cost comparison
9. Conclusions

Put the report in the repo. Put two or three clean screenshots in the README.

---

## 9. Interview questions

**Why divide Z by 2 in Ah?**
Z is the peak ground acceleration for the Maximum Considered Earthquake. Design is
carried out for the Design Basis Earthquake, taken as half the MCE, with the
expectation that the structure survives the MCE with damage but without collapse.

**Why does R divide the demand?**
A ductile frame yields and dissipates energy, so it may be designed for less than
full elastic demand. R = 5 for an SMRF assumes IS 13920 detailing actually delivers
that ductility. Take R = 5 without the detailing and the assumption is void.

**Why h² in the storey force distribution?**
It approximates the first mode shape, roughly an inverted triangle of acceleration.
Upper storeys therefore attract disproportionate force — in this building the roof
takes about 33% of the base shear, not 17%.

**Base shear went up 2.4× but steel only X%. Why?**
Gravity load is unchanged, so gravity-governed members barely move. Only members
whose governing combination flipped from gravity to lateral changed — mostly columns
and the beams framing into them. The 2.4× applies to lateral demand, not total demand.

**Did drift or strength govern in Zone IV?**
[Answer from your own results.] If drift governed, say so — it means the section grew
for stiffness, not capacity, and that is a different design conversation.

**Your hand calc and STAAD differ by 8%. Which is right?**
Both, for different models. STAAD applies rigid-zone offsets at joints so its clear
span is shorter, giving lower moments. My hand calc used centre-to-centre span, which
is conservative. I would use the software value for design and the hand calc as a
sanity check.

**Why did you not do response spectrum analysis?**
Equivalent static is permitted by IS 1893 for regular buildings below the height limit,
and this building is regular. For an irregular or taller structure, dynamic analysis
would be mandatory. [If you have time, run response spectrum too and compare — it makes
a strong extra section.]

---

## 10. Order of work

| Day | Task |
|---|---|
| 1 | Fix geometry, compute loads by hand, run `seismic.py` |
| 2 | Build the STAAD/ETABS model, Zone II, verify base shear |
| 3 | Zone IV run, check drift, resize columns if needed |
| 4 | Extract reinforcement, tabulate the comparison |
| 5 | Hand-design one beam and one column, compare |
| 6 | BBS, rate analysis, feed into RebarOpt |
| 7 | Write the report, screenshots, push to GitHub |
