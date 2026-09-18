# Finishing the SeismicDelta drawings in AutoCAD

About 30 minutes. `generate_dxf.py` writes the geometry; you turn it into a proper sheet.

```bash
python generate_dxf.py
```

## 1. Open

1. AutoCAD > Open > file type **DXF** > `drawings/seismicdelta_plan_elevation.dxf`.
2. Type `Z` Enter `E` Enter (zoom extents). You should see the floor plan on the
   left and the frame elevation on grid 1 on the right.
3. Type `UNITS` and set insertion units to **Millimetres**. Everything is drawn in mm.

## 2. Tidy the layers

Layers already exist: GRID, COLUMNS, BEAMS, TEXT, DIMENSIONS.

1. `LA` (Layer Properties): set GRID linetype to **CENTER** (Load > CENTER), colour 8.
2. COLUMNS lineweight 0.35 mm, BEAMS 0.25 mm, others 0.18 mm.
3. Hatch the columns: `H`, pattern SOLID, pick inside each column square (plan only).

## 3. Replace the drawn dimensions with real AutoCAD dimensions

The script draws dimensions as plain lines and text so the file opens anywhere.
Redo them properly so they update if the geometry changes:

1. `DIMSTYLE` > New > text height 250, arrows *Architectural tick*, units mm.
2. `DIMLINEAR` for each 5000 bay and the 20000 and 15000 overall dimensions;
   `DIMLINEAR` on the elevation for 3200 and 19200.
3. Delete the old DIMENSIONS-layer lines and text.

## 4. Sheet and plot

1. Switch to a **Layout** tab, set page size A3 landscape.
2. Add a title block: project *SeismicDelta, G+5 RC frame*, drawn by *Kartik Taneja*,
   scale 1:100, date.
3. `PLOT` > printer *DWG To PDF* > save `drawings/seismicdelta_plan_elevation.pdf`.
4. Save the drawing as `drawings/seismicdelta_plan_elevation.dwg`.

```bash
git add drawings
git commit -m "AutoCAD plan and frame elevation"
git push
```

## What to say in an interview

"I generated the grid, columns and beams from the same parameters as the analysis
so drawing and model could not disagree, then finished the sheet in AutoCAD:
layers, linetypes, real dimension styles, title block and a plotted PDF."
