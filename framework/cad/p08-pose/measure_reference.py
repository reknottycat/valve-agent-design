"""Measure the frozen FDG1 reference STEP, NOT a pose reconstruction or a mesh."""
import argparse
import hashlib
import json
import math
from pathlib import Path
from qualify_inputs import pins, REFERENCE


def measure(path):
    import gmsh
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != pins()[REFERENCE]:
        raise ValueError('This face-pair and the probe coordinates are specific to the frozen STEP.')
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        occ = gmsh.model.occ; occ.importShapes(str(path)); occ.synchronize()
        volumes = gmsh.model.getEntities(3); faces = gmsh.model.getEntities(2)
        if len(volumes) != 1 or len(faces) != 132: raise ValueError('Unexpected reference topology')
        vol = volumes[0][1]; ports = {}
        for name, x in [('inlet', -600), ('outlet', 1200)]:
            matches = []
            for _, f in faces:
                box = gmsh.model.getBoundingBox(2, f)
                if max(abs(box[i]-x) for i in (0, 3)) < 1e-4: matches.append(f)
            if len(matches) != 1: raise ValueError(f'Expected one planar {name}')
            f = matches[0]; area = occ.getMass(2, f)
            if not math.isclose(area, math.pi*100**2, rel_tol=1e-8): raise ValueError(name+' area mismatch')
            ports[name] = {'center_mm': list(occ.getCenterOfMass(2, f)), 'area_mm2': area}
        # Fixed face identity, never reuse on a different STEP. Confirm liquid between both walls.
        distance = occ.getDistance(2, 64, 2, 108)[0]
        samples = [{'p_mm':[300+sign*r,.17,160], 'fluid':bool(gmsh.model.isInside(3,vol,[300+sign*r,.17,160]))}
                   for sign in (1,-1) for r in (30.95,31.5,32.05)]
        if not math.isclose(distance, 1, abs_tol=1e-5) or [s['fluid'] for s in samples] != [False,True,False]*2:
            raise ValueError('Reference guide fluid passage not reproduced')
        volume = occ.getMass(3, vol)
        if not math.isclose(volume, 64142426.14376342, rel_tol=1e-7): raise ValueError('Reference volume mismatch')
        return {'step_sha256':digest, 'gmsh_version':gmsh.__version__, 'fluid_solids':len(volumes), 'faces':len(faces),
                'main_fluid_volume_mm3':volume, 'ports':ports, 'guide_wall_distance_mm':float(distance), 'guide_section':samples,
                'scope':'Existing main wet domain only. Guide wall pair, not a global minimum, seat gap or actual lift. No rebuild or flow calculation.'}
    finally: gmsh.finalize()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('step',type=Path); print(json.dumps(measure(parser.parse_args().step),indent=2))
