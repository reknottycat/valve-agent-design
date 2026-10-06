import sys, json, math
from pathlib import Path
sys.path.append(sys.argv[2])
import FreeCAD as App, Part
out = Path(sys.argv[1])
doc = App.newDocument("T04Smoke")
box = doc.addObject("Part::Box", "EditableBox")
box.Length=10; box.Width=20; box.Height=30; doc.recompute()
original = box.Shape.Volume
box.Length=12; doc.recompute()
if not (math.isclose(original,6000) and math.isclose(box.Shape.Volume,7200)):
    raise RuntimeError("FreeCAD parameter rebuild failed")
doc.saveAs(str(out/"smoke_editable.FCStd"))
box.Shape.exportStep(str(out/"freecad_smoke.step"))
App.closeDocument(doc.Name)
doc=App.openDocument(str(out/"smoke_editable.FCStd"))
shape=Part.Shape();shape.read(str(out/"freecad_smoke.step"))
if not (shape.isValid() and len(shape.Solids)==1 and math.isclose(shape.Volume,7200,rel_tol=1e-8)):
    raise RuntimeError("FreeCAD STEP exchange failed")
if doc.EditableBox.Length.Value!=12:
    raise RuntimeError("FreeCAD FCStd parameter persistence failed")
(out/"freecad_result.json").write_text(json.dumps({"status":"VERIFIED","version":App.Version(),
 "scope":"editable parametric box rebuild, FCStd reopen and STEP roundtrip; independent smoke only",
 "before_mm3":original,"after_mm3":shape.Volume,"solid_count":len(shape.Solids)},indent=2))
App.closeDocument(doc.Name)
