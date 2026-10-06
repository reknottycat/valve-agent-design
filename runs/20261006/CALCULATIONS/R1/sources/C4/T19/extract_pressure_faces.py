#!/usr/bin/env python3
"""Axial pressure-area integration on frozen C2 disc/stem STEP faces, not CFD/FEA."""
import hashlib
import json
import math
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[1]
C2 = BASE.parent / 'C2'


def checked_number(value, label, nonnegative=False):
    if type(value) not in (float, int) or not math.isfinite(value) or (nonnegative and value < 0):
        raise ValueError('Invalid ' + label)
    return value


def classify_compartments(solids, length):
    if len(solids) != 2:
        raise ValueError('Closed case requires exactly two pressure compartments')
    result = {}
    for solid in solids:
        if not solid.isValid() or checked_number(solid.Volume(1e-9), 'fluid volume', True) <= 0:
            raise ValueError('Invalid pressure compartment')
        box = solid.BoundingBox()
        inlet, outlet = box.xmin < -1e-3, box.xmax > length + 1e-3
        if inlet == outlet:
            raise ValueError('Disconnected or bypassing pressure compartment')
        label = 'inlet' if inlet else 'outlet'
        if label in result:
            raise ValueError('Duplicate end compartment')
        result[label] = solid
    if set(result) != {'inlet', 'outlet'}:
        raise ValueError('Missing pressure compartment')
    return result


def pressure_area(part, fluid):
    """Pressure force is -p*integral(n_part dA). Only verified axial-zero cylinders omitted."""
    rows = []
    force_area_z = 0.
    for index, fa in enumerate(part.Faces()):
        kind = fa.geomType()
        if kind == 'CYLINDER':
            direction = fa._geomAdaptor().Cylinder().Axis().Direction()
            if abs(abs(direction.Z()) - 1.) > 1e-8:
                raise ValueError('Non-axial cylinder cannot be omitted from axial force')
            continue
        if kind != 'PLANE':
            raise ValueError('Unsupported force-bearing surface ' + kind)
        normal = fa.normalAt()
        nz = checked_number(normal.z, 'face normal')
        if abs(nz) < 1e-10:
            continue
        area = 0.
        ba = fa.BoundingBox()
        for fb in fluid.Faces():
            if fb.geomType() != 'PLANE' or normal.dot(fb.normalAt()) > -1 + 1e-7:
                continue
            if abs((fa.Center()-fb.Center()).dot(normal)) > 1e-6:
                continue
            bb = fb.BoundingBox()
            if any(getattr(ba, k+'max') < getattr(bb, k+'min')-1e-6 or
                   getattr(bb, k+'max') < getattr(ba, k+'min')-1e-6 for k in 'xyz'):
                continue
            common = fa.intersect(fb)
            if not common.isValid():
                raise ValueError('Invalid wetted-face intersection')
            area += checked_number(common.Area(), 'wetted area', True)
        if area > fa.Area() + 1e-3:
            raise ValueError('Duplicate or excessive wetted coverage')
        if area > 1e-6:
            coefficient = -nz * area
            force_area_z += coefficient
            rows.append({'part_face_index': index, 'z_mm': fa.Center().z,
                         'outward_normal_z': nz, 'wetted_area_mm2': area,
                         'axial_force_coefficient_mm2': coefficient})
    return {'axial_force_coefficient_N_per_MPa': force_area_z, 'faces': rows}


def measure():
    import cadquery as cq
    sys.path.insert(0, str(BASE.parent / 'CLOUD/T04'))
    from geometry_gate import step_length_unit
    parameters_path = C2 / 'T11/parameters.json'
    params = json.loads(parameters_path.read_text())
    p = {key: row['value'] for key, row in params['values'].items()}
    expected_hashes = json.loads((C2/'T12/out/build_report.json').read_text())['asset_hashes']
    asset_hashes = {}
    poses = {}
    for pose in ('closed', 'check_closed'):
        def read(name):
            relative = f'{pose}/{name}.step'
            path = C2 / 'T12/out' / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if expected_hashes.get(relative) != digest or step_length_unit(path)['unit'] != 'mm':
                raise ValueError('Unverified input STEP ' + relative)
            asset_hashes[relative] = digest
            shape = cq.importers.importStep(str(path)).val()
            if not shape.isValid():
                raise ValueError('Invalid STEP ' + relative)
            return shape
        fluid = read('fluid_domain_mm')
        compartments = classify_compartments(fluid.Solids(), p['face_to_face'])
        result = {}
        for name in ('disc_guide', 'stem'):
            part = read(name)
            if len(part.Solids()) != 1:
                raise ValueError('Part must be one valid solid')
            result[name] = {side: pressure_area(part, solid) for side, solid in compartments.items()}
        area = lambda d: math.pi*d*d/4
        expected = {
            'disc_guide': {'inlet': area(p['bore']), 'outlet': -area(p['seat_od']) + (area(p['stem_od']) if pose == 'closed' else 0.)},
            'stem': {'inlet': 0., 'outlet': area(p['stem_od']) if pose == 'check_closed' else 0.}}
        for name, sides in expected.items():
            for side, expected_value in sides.items():
                actual = result[name][side]['axial_force_coefficient_N_per_MPa']
                if not math.isclose(actual, expected_value, rel_tol=1e-7, abs_tol=1e-3):
                    raise ValueError(f'Independent analytical projected-area mismatch: {pose}/{name}/{side}')
        poses[pose] = {'pressure_compartments': 2, 'parts': result,
                       'independent_projected_area_control': expected, 'analytical_check': 'PASS'}
    return {'schema': 'valve.c4-pressure-areas/1.0', 'status': 'GEOMETRIC_PRESSURE_AREA_PASS',
            'force_sign': '+Z lifts disc/retracts spindle',
            'length_unit': 'mm', 'pressure_unit': 'MPa', 'force_unit': 'N',
            'input_asset_sha256': asset_hashes,
            'parameters_sha256': hashlib.sha256(parameters_path.read_bytes()).hexdigest(),
            'extractor_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'poses': poses, 'manufacturing_authorized': False, 'solver_execution_performed': False,
            'limitations': ['Frozen geometric compartments, uniform compartment pressures and dry contact faces are modeling assumptions',
                           'No leakage, elastic opening, seat contact-pressure penetration or hydrostatic head distribution is solved',
                           'Cylinder surfaces are included only as analytically zero axial projected area after checking their axes',
                           'Forces are pressure components, excluding weight, inertia, contact reactions, friction and preload',
                           'No valid material allowable or engineering acceptance is inferred from load calculation']}


def main():
    output = BASE / 'T19/pressure_areas.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({'status': 'RUNNING', 'manufacturing_authorized': False}))
    try:
        result = measure()
        output.write_text(json.dumps(result, indent=2))
    except Exception as exc:
        output.write_text(json.dumps({'status': 'FAIL', 'error': str(exc), 'manufacturing_authorized': False}, indent=2))
        raise
    print(json.dumps({'status': result['status'], 'poses': {name: {part: {side: x['axial_force_coefficient_N_per_MPa'] for side, x in sides.items()} for part, sides in pose['parts'].items()} for name, pose in result['poses'].items()}}, indent=2))


if __name__ == '__main__':
    main()
