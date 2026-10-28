#!/usr/bin/env python3
"""Read-only verification of the pinned P08 proxy STEP packing truncation.

Usage: python face80_check.py INPUT.step --output face80_check.json
Requires CadQuery with OCP. Refuses a different STEP hash. This only proves
properties of the proxy fluid solid, not sealing performance or a mesh patch.
"""
import argparse
import hashlib
import json
import math
import platform
from pathlib import Path
import cadquery as cq
import OCP

EXPECTED_SHA256 = 'a9aeb45996a388a3d894f69605205c70c25edd154adc6d3c71658329a730e787'
TOL_MM = 1e-5
TOL_AREA_MM2 = 1e-5
CLASSIFIER_TOL_MM = 1e-7

def near(a, b, tol=TOL_MM):
    return abs(a-b) <= tol

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    digest = hashlib.sha256(args.step.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit('Input SHA-256 mismatch; refused')
    solid = cq.importers.importStep(str(args.step)).val()
    faces = solid.Faces()
    candidates = []
    for idx, face in enumerate(faces, 1):
        bb = face.BoundingBox()
        if (face.geomType() == 'PLANE' and near(bb.zmin,332) and near(bb.zmax,332)
                and near(bb.xmin,278) and near(bb.xmax,322)
                and near(bb.ymin,-22) and near(bb.ymax,22)):
            candidates.append((idx, face))
    if len(candidates) != 1:
        raise SystemExit(f'Expected one matching face, found {len(candidates)}')
    index, face = candidates[0]
    edges = []
    for edge in face.Edges():
        bb = edge.BoundingBox()
        edges.append({'type': edge.geomType(), 'length_mm': edge.Length(),
                      'bbox_mm': [bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmin, bb.zmax]})
    edges.sort(key=lambda e: e['length_mm'])
    normal = face.normalAt().toTuple()
    samples = []
    for radius in (17.9, 18.1, 20.0, 21.9, 22.1):
        for z in (331.9, 332.1):
            expected = 18 < radius < 22 and z < 332
            inside = bool(solid.isInside(cq.Vector(300 + radius, 0, z), CLASSIFIER_TOL_MM))
            samples.append({'radius_mm': radius, 'z_mm': z, 'inside_fluid_solid': inside,
                            'expected_inside': expected, 'pass': inside == expected})
    checks = {
        'valid_solid': solid.isValid(),
        'solid_count_1': len(solid.Solids()) == 1,
        'face_count_132': len(faces) == 132,
        'matching_import_face_index_80': index == 80,
        'two_wires_two_circular_edges': len(face.Wires()) == 2 and len(edges) == 2 and all(x['type'] == 'CIRCLE' for x in edges),
        'inner_outer_circumferences': len(edges) == 2 and near(edges[0]['length_mm'], 2*math.pi*18) and near(edges[1]['length_mm'], 2*math.pi*22),
        'annular_area': near(face.Area(), math.pi*(22**2-18**2), TOL_AREA_MM2),
        'outward_normal_plus_z': all(near(a,b,1e-9) for a,b in zip(normal,(0,0,1))),
        'sampled_inside_outside': all(x['pass'] for x in samples),
    }
    result = {
        'schema': 'p08.face80_readonly_check/v1', 'status': 'PASS' if all(checks.values()) else 'FAIL',
        'input': {'filename': args.step.name, 'sha256': digest, 'scope': 'seal-omitted proxy fluid domain, nominal open57; not a verified manufactured valve'},
        'environment': {'cadquery': cq.__version__, 'ocp': getattr(OCP,'__version__','unknown'), 'python': platform.python_version()},
        'tolerances': {'coordinate_and_circumference_mm': TOL_MM, 'area_mm2': TOL_AREA_MM2, 'normal_component': 1e-9, 'point_classifier_mm': CLASSIFIER_TOL_MM},
        'geometry': {'import_face_index_1_based': index, 'surface_type': face.geomType(), 'center_mm': list(face.Center().toTuple()),
                     'area_mm2': face.Area(), 'normal': list(normal), 'wire_count': len(face.Wires()), 'edges': edges},
        'samples': samples, 'checks': checks,
        'limitations': ['Point classifications sample one radial line, not an exhaustive topology proof.',
                        'Face index is local to this import; final mesh patch correspondence is not established.',
                        'Dimensions match the GA1 D36/D44 packing candidate but do not prove assembled physical sealing or leak-tightness.',
                        'Only the packing cap was examined; other omitted seal and assembly features remain open.']}
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'output': str(args.output), 'checks': checks}, ensure_ascii=False))
    if result['status'] != 'PASS':
        raise SystemExit(1)

if __name__ == '__main__':
    main()
