#!/usr/bin/env python3
"""Read-only scope/readiness checks. Only incompressible 0/U, 0/p cases; findings are not CFD certification."""
import argparse
import json
import re
from pathlib import Path


def audit(meta, case=None):
    errors, notes = [], []
    requested = meta.get('requested_action', 'inspect')
    if requested not in ('inspect', 'solve'):
        errors.append('UNKNOWN_REQUESTED_ACTION')
    if requested == 'solve' and not meta.get('domain_scope'):
        errors.append('MISSING_DOMAIN_SCOPE')
    if meta.get('execution_budget'):
        b = meta['execution_budget']
        if b.get('scope') != meta.get('domain_scope'):
            errors.append('BUDGET_SCOPE_MISMATCH')
        if b.get('meaning') == 'engineering_required_cells':
            errors.append('EXECUTION_CAP_IS_NOT_REQUIRED_RESOLUTION')
    if requested == 'solve' and meta.get('milestone_complete') is True and not meta.get('new_objective'):
        errors.append('COMPLETED_MILESTONE_RERUN_WITHOUT_NEW_OBJECTIVE')
    if requested == 'solve':
        if meta.get('boundary_conditions_verified') is not True:
            errors.append('BOUNDARY_CONDITIONS_UNVERIFIED')
        if meta.get('pressure_role') == 'design_pressure_as_pressure_drop':
            errors.append('DESIGN_PRESSURE_IS_NOT_VERIFIED_PRESSURE_DROP')
        if meta.get('mesh_stage') != 'retained_fluid_mesh':
            errors.append('NO_CONFIRMED_RETAINED_FLUID_MESH')
        if meta.get('mesh_quality_pass') is not True:
            errors.append('MESH_QUALITY_NOT_PASSED')
        if case is None:
            errors.append('CASE_BYTES_NOT_CHECKED')
        else:
            case = Path(case)
            for name in ('0/U', '0/p', 'system/controlDict', 'system/fvSchemes', 'system/fvSolution'):
                if not (case / name).is_file():
                    errors.append('MISSING_FILE:' + name)
            if not any((case / 'constant' / n).is_file() for n in ('transportProperties', 'physicalProperties')):
                errors.append('MISSING_PHYSICAL_PROPERTIES')
            f = case / 'system/fvSolution'
            if f.is_file():
                s = re.sub(r'/\*.*?\*/|//[^\n]*', '', f.read_text(), flags=re.S)
                if re.search(r'\bsolvers\s*\{\s*\}', s):
                    errors.append('EMPTY_SOLVERS')
                elif not re.search(r'\bsolvers\s*\{', s):
                    errors.append('SOLVER_DICTIONARY_NOT_RESOLVED')
            for n in ('points', 'faces', 'owner', 'neighbour', 'boundary'):
                if not (case / 'constant/polyMesh' / n).is_file():
                    errors.append('MISSING_MESH_FILE:' + n)
    if meta.get('pressure_stability_pass') is True:
        notes.append('Pressure stability alone does not prove all residuals converged, grid independence or full-valve validity.')
    notes.append('Pass means listed preflight checks only; no boundary parsing, topology verification or engineering approval is implied.')
    return {'schema': 'valve.readiness/v1', 'requested_action': requested,
            'domain_scope': meta.get('domain_scope'), 'preflight_pass': not errors,
            'errors': errors, 'notes': notes, 'mutated_case': False, 'solver_started': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    p.add_argument('--case', type=Path)
    a = p.parse_args()
    result = audit(json.loads(a.manifest.read_text()), a.case)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['preflight_pass'] else 2)
