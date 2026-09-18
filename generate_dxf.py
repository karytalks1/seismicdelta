"""
Write the SeismicDelta building as an AutoCAD drawing (DXF): floor plan and frame elevation.

    python generate_dxf.py        ->  drawings/seismicdelta_plan_elevation.dxf

Open the file in AutoCAD (File > Open, file type DXF). All units are millimetres.
Pure standard library - the DXF is written as plain text (AutoCAD R12 format, which
every version of AutoCAD still opens).

Layers:  GRID (grid lines and bubbles), COLUMNS, BEAMS, TEXT, DIMENSIONS
"""
from pathlib import Path

# Building - must match seismic.py and README
BAYS_X, BAYS_Y = 4, 3            # 4 bays along X, 3 along Y
BAY = 5000                       # mm
STOREYS = 6                      # ground + 5
STOREY_H = 3200                  # mm
COL = 400                        # column 400 x 400
BEAM_W, BEAM_D = 300, 450        # beam 300 wide x 450 deep

COLOURS = {"GRID": 8, "COLUMNS": 1, "BEAMS": 5, "TEXT": 7, "DIMENSIONS": 3}

OUT = Path(__file__).parent / "drawings" / "seismicdelta_plan_elevation.dxf"
ents: list[str] = []


def line(x1, y1, x2, y2, layer):
    ents.extend(["0", "LINE", "8", layer, "62", str(COLOURS[layer]),
                 "10", f"{x1:.1f}", "20", f"{y1:.1f}", "30", "0.0",
                 "11", f"{x2:.1f}", "21", f"{y2:.1f}", "31", "0.0"])


def rect(x1, y1, x2, y2, layer):
    line(x1, y1, x2, y1, layer)
    line(x2, y1, x2, y2, layer)
    line(x2, y2, x1, y2, layer)
    line(x1, y2, x1, y1, layer)


def circle(x, y, r, layer):
    ents.extend(["0", "CIRCLE", "8", layer, "62", str(COLOURS[layer]),
                 "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0", "40", f"{r:.1f}"])


def text(x, y, h, s, layer="TEXT", centred=False):
    ents.extend(["0", "TEXT", "8", layer, "62", str(COLOURS[layer]),
                 "10", f"{x:.1f}", "20", f"{y:.1f}", "30", "0.0", "40", f"{h:.1f}", "1", s])
    if centred:                                   # middle-centre alignment
        ents.extend(["72", "1", "73", "2", "11", f"{x:.1f}", "21", f"{y:.1f}", "31", "0.0"])


def dim_h(x1, x2, y, label):
    """A simple horizontal dimension drawn from lines and text (explode-free, any AutoCAD)."""
    line(x1, y, x2, y, "DIMENSIONS")
    for x in (x1, x2):
        line(x, y - 250, x, y + 250, "DIMENSIONS")
        line(x - 150, y - 150, x + 150, y + 150, "DIMENSIONS")   # architectural tick
    text((x1 + x2) / 2, y + 350, 250, label, "DIMENSIONS", centred=True)


def dim_v(x, y1, y2, label):
    line(x, y1, x, y2, "DIMENSIONS")
    for y in (y1, y2):
        line(x - 250, y, x + 250, y, "DIMENSIONS")
        line(x - 150, y - 150, x + 150, y + 150, "DIMENSIONS")
    text(x - 450, (y1 + y2) / 2, 250, label, "DIMENSIONS", centred=True)


# ---------------------------------------------------------------- floor plan
W, D = BAYS_X * BAY, BAYS_Y * BAY
ext = 1500
letters = "ABCDE"
for i in range(BAYS_X + 1):                       # grid lines along X: A..E
    x = i * BAY
    line(x, -ext, x, D + ext, "GRID")
    circle(x, D + ext + 400, 400, "GRID")
    text(x, D + ext + 400, 350, letters[i], centred=True)
for j in range(BAYS_Y + 1):                       # grid lines along Y: 1..4
    y = j * BAY
    line(-ext, y, W + ext, y, "GRID")
    circle(-ext - 400, y, 400, "GRID")
    text(-ext - 400, y, 350, str(j + 1), centred=True)

h = COL / 2
for i in range(BAYS_X + 1):                       # columns
    for j in range(BAYS_Y + 1):
        rect(i * BAY - h, j * BAY - h, i * BAY + h, j * BAY + h, "COLUMNS")

b = BEAM_W / 2
for j in range(BAYS_Y + 1):                       # beams along X, between column faces
    for i in range(BAYS_X):
        x1, x2, y = i * BAY + h, (i + 1) * BAY - h, j * BAY
        line(x1, y - b, x2, y - b, "BEAMS")
        line(x1, y + b, x2, y + b, "BEAMS")
for i in range(BAYS_X + 1):                       # beams along Y
    for j in range(BAYS_Y):
        y1, y2, x = j * BAY + h, (j + 1) * BAY - h, i * BAY
        line(x - b, y1, x - b, y2, "BEAMS")
        line(x + b, y1, x + b, y2, "BEAMS")

for i in range(BAYS_X):
    dim_h(i * BAY, (i + 1) * BAY, -ext - 900, f"{BAY}")
dim_h(0, W, -ext - 2100, f"{W}")
for j in range(BAYS_Y):
    dim_v(W + ext + 900, j * BAY, (j + 1) * BAY, f"{BAY}")
dim_v(W + ext + 2100, 0, D, f"{D}")

text(0, -ext - 3700, 500, "TYPICAL FLOOR PLAN")
text(0, -ext - 4500, 300, f"Columns {COL} x {COL}, beams {BEAM_W} x {BEAM_D}, M25 / Fe500. All dimensions in mm.")

# ---------------------------------------------------------------- frame elevation (along grid 1)
ox = W + 13000                                    # place elevation to the right of the plan
top = STOREYS * STOREY_H
for i in range(BAYS_X + 1):                       # columns
    x = ox + i * BAY
    line(x - h, 0, x - h, top, "COLUMNS")
    line(x + h, 0, x + h, top, "COLUMNS")
    line(x, -ext, x, top + ext, "GRID")
    circle(x, top + ext + 400, 400, "GRID")
    text(x, top + ext + 400, 350, letters[i], centred=True)
for k in range(1, STOREYS + 1):                   # beams at each floor, soffit 450 below level
    y = k * STOREY_H
    for i in range(BAYS_X):
        x1, x2 = ox + i * BAY + h, ox + (i + 1) * BAY - h
        line(x1, y, x2, y, "BEAMS")
        line(x1, y - BEAM_D, x2, y - BEAM_D, "BEAMS")
    text(ox + BAYS_X * BAY + ext, y, 250, f"+{y / 1000:.3f}")
line(ox - ext, 0, ox + BAYS_X * BAY + ext, 0, "GRID")    # ground line
text(ox + BAYS_X * BAY + ext, 0, 250, "+0.000")
dim_v(ox - ext - 900, 0, STOREY_H, f"{STOREY_H}")
dim_v(ox - ext - 2100, 0, top, f"{top}")

text(ox, -ext - 1200, 500, "FRAME ELEVATION ON GRID 1")
text(ox, -ext - 2000, 300, f"G+{STOREYS - 1}, storey height {STOREY_H} mm, total {top} mm. SMRF, R = 5.")

# ---------------------------------------------------------------- write R12 DXF
OUT.parent.mkdir(exist_ok=True)
dxf = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC",
       "0", "SECTION", "2", "ENTITIES", *ents, "0", "ENDSEC", "0", "EOF"]
OUT.write_text("\n".join(dxf) + "\n", encoding="ascii")
print(f"wrote {OUT}  ({len(ents) // 2} DXF codes)")
