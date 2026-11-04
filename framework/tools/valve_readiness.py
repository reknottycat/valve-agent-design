#!/usr/bin/env python3
"""Read-only scope/readiness checks. Only incompressible 0/U, 0/p cases; findings are not CFD certification."""
import argparse
import json
import re
import os
import stat
import sys
from types import ModuleType
from pathlib import Path


# Exact reviewed sibling source, never an upstream/sys.path plugin. exec avoids
# import-time bytecode writes and works with python -I.
_adapter_path = Path(__file__).resolve().parents[1] / 'standards/standards_adapter.py'
_adapter = ModuleType('_readiness_standards_adapter')
_adapter.__file__ = str(_adapter_path)
exec(compile(_adapter_path.read_bytes(), str(_adapter_path), 'exec', dont_inherit=True), _adapter.__dict__)
ReadinessError = _adapter.AdapterError
BASE_CONFIGURATION = '522-35.4179'
USES = {'RESEARCH_REFERENCE', 'CALCULATION_SUPPORT', 'NORMATIVE_BASIS'}


def _case_file(root, relative):
    """Check existence/type only. Large mesh files are not read or size-gated."""
    path = _adapter._file_path(root, relative)
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_NOFOLLOW', 0))
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ReadinessError('Expected regular case file: ' + relative)
        return True
    except FileNotFoundError:
        if path.is_symlink():
            raise ReadinessError('Unsafe case symlink: ' + relative)
        return None
    finally:
        if fd is not None:
            os.close(fd)


def _physical_preflight(meta, case=None):
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
                if _case_file(case, name) is None:
                    errors.append('MISSING_FILE:' + name)
            if not any([_case_file(case, 'constant/' + n) is not None for n in ('transportProperties', 'physicalProperties')]):
                errors.append('MISSING_PHYSICAL_PROPERTIES')
            exists = _case_file(case, 'system/fvSolution')
            if exists:
                raw = _adapter._read(_adapter._file_path(case, 'system/fvSolution'))
                s = re.sub(r'/\*.*?\*/|//[^\n]*', '', raw.decode('utf-8'), flags=re.S)
                if re.search(r'\bsolvers\s*\{\s*\}', s):
                    errors.append('EMPTY_SOLVERS')
                elif not re.search(r'\bsolvers\s*\{', s):
                    errors.append('SOLVER_DICTIONARY_NOT_RESOLVED')
            for n in ('points', 'faces', 'owner', 'neighbour', 'boundary'):
                if _case_file(case, 'constant/polyMesh/' + n) is None:
                    errors.append('MISSING_MESH_FILE:' + n)
    if meta.get('pressure_stability_pass') is True:
        notes.append('Pressure stability alone does not prove all residuals converged, grid independence or full-valve validity.')
    notes.append('Physical preflight_pass means listed legacy checks only; no boundary parsing, topology verification or engineering approval is implied.')
    return {'schema': 'valve.readiness/v1', 'requested_action': requested,
            'domain_scope': meta.get('domain_scope'), 'preflight_pass': not errors,
            'errors': errors, 'notes': notes, 'mutated_case': False, 'solver_started': False}


def _validate_meta(meta):
    """Bound the API to the same finite JSON data contract as the CLI."""
    if not isinstance(meta, dict):
        raise ReadinessError('Manifest must be a JSON object')
    def validate_value(value, depth=0):
        if depth > 64:
            raise ReadinessError('Manifest nesting exceeds 64 levels')
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise ReadinessError('JSON object keys must be strings')
            for child in value.values():
                validate_value(child, depth + 1)
        elif type(value) is list:
            for child in value:
                validate_value(child, depth + 1)
        elif value is not None and type(value) not in (str, int, float, bool):
            raise ReadinessError('Manifest must contain only JSON types')
    validate_value(meta)
    try:
        encoded = json.dumps(meta, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, RecursionError) as exc:
        raise ReadinessError('Manifest must contain finite JSON data') from exc
    if len(encoded) > _adapter.MAX_INPUT_BYTES:
        raise ReadinessError('Manifest exceeds input resource limit')
    allowed = {'requested_action', 'domain_scope', 'execution_budget', 'milestone_complete',
               'new_objective', 'boundary_conditions_verified', 'pressure_role', 'mesh_stage',
               'mesh_quality_pass', 'pressure_stability_pass', 'source_note', 'standards'}
    if set(meta) - allowed:
        raise ReadinessError('Unknown manifest fields: ' + str(sorted(set(meta) - allowed)))
    for name in ('requested_action', 'domain_scope', 'new_objective', 'pressure_role', 'mesh_stage', 'source_note'):
        if name in meta and (not isinstance(meta[name], str) or not meta[name].strip()):
            raise ReadinessError(name + ' must be a nonempty string')
    budget = meta.get('execution_budget')
    if 'execution_budget' in meta:
        if not isinstance(budget, dict) or set(budget) - {'scope', 'cells', 'meaning'}:
            raise ReadinessError('Invalid execution_budget object')
        for name in ('scope', 'meaning'):
            if name in budget and (not isinstance(budget[name], str) or not budget[name].strip()):
                raise ReadinessError('Budget ' + name + ' must be a nonempty string')
        if 'cells' in budget and (type(budget['cells']) is not int or budget['cells'] <= 0):
            raise ReadinessError('Budget cells must be a positive integer')


def _standards_checks(meta):
    declaration = meta.get('standards')
    result = {'status': 'NOT_CHECKED', 'source_use_pass': None, 'errors': [], 'warnings': [],
              'references': [], 'acceptance': {'status': 'NOT_CHECKED'},
              'project_applicability': {'status': 'NOT_ASSESSED', 'approved': False},
              'identity_binding': {'mode': 'DECLARED_IDENTITY_ONLY', 'configuration_authenticated': False}}
    if 'standards' not in meta:
        if meta.get('requested_action') == 'solve':
            result['status'] = 'INCOMPLETE'
            result['errors'].append('MISSING_STANDARDS_DECLARATION')
        return result
    required = {'root', 'configuration_id', 'references'}
    if not isinstance(declaration, dict) or set(declaration) != required:
        raise ReadinessError('standards requires exactly root, configuration_id, references')
    for name in ('root', 'configuration_id'):
        if not isinstance(declaration[name], str) or not declaration[name].strip():
            raise ReadinessError('standards.' + name + ' must be a nonempty string')
    refs = declaration['references']
    if not isinstance(refs, list) or not refs or len(refs) > 95:
        raise ReadinessError('standards.references must contain 1 to 95 explicit references')
    seen = set()
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {'id', 'use'}:
            raise ReadinessError('Each reference requires exactly id and use')
        if not isinstance(ref['id'], str) or not ref['id'].strip():
            raise ReadinessError('Reference id must be a nonempty string')
        if not isinstance(ref['use'], str) or ref['use'] not in USES:
            raise ReadinessError('Unknown reference use')
        if ref['id'] in seen:
            raise ReadinessError('Duplicate reference ID: ' + ref['id'])
        seen.add(ref['id'])
    # The adapter supports only one pinned, unconfirmed card, not arbitrary variants.
    if declaration['configuration_id'] != BASE_CONFIGURATION:
        result.update(status='INCOMPLETE', source_use_pass=False)
        result['errors'].append('UNSUPPORTED_CONFIGURATION_FOR_PINNED_BASELINE')
        return result
    adapter = _adapter.StandardsAdapter(declaration['root'])
    assessment = adapter.assess_acceptance()
    if assessment['project_applicability']['configuration_id'] != declaration['configuration_id']:
        raise ReadinessError('Consumer identity differs from adapter baseline')
    result.update(status='CHECKED', source_use_pass=True,
                  provenance={key: assessment[key] for key in ('repository', 'commit', 'scope', 'manifest_sha256', 'record_count')},
                  acceptance=assessment['acceptance'], pending_numeric_limits=assessment['pending_numeric_limits'],
                  card_binding=assessment['card_binding'], project_applicability=assessment['project_applicability'])
    for ref in refs:
        query = adapter.query(record_id=ref['id'])
        if query['count'] != 1:
            raise ReadinessError('Unknown source record ID: ' + ref['id'])
        record = query['results'][0]
        usable = record['upstream_calc_eligibility']['usable']
        reference = dict(ref, source_status=record['source_status'], source_grade=record['source_grade'],
                         upstream_calc_eligibility=record['upstream_calc_eligibility'], provenance=record['provenance'])
        reference['declared_use_pass'] = usable or ref['use'] == 'RESEARCH_REFERENCE'
        result['references'].append(reference)
        if not usable:
            if ref['use'] == 'RESEARCH_REFERENCE':
                result['warnings'].append('RESEARCH_ONLY_INELIGIBLE_SOURCE:' + ref['id'])
            else:
                result['source_use_pass'] = False
                result['errors'].append('SOURCE_INELIGIBLE_FOR_DECLARED_USE:' + ref['id'])
    return result


def audit(meta, case=None):
    """Inspect finite metadata, bounded case bytes, and explicitly declared sources.

    Raises ReadinessError for malformed/unsafe inputs. A successful audit is not
    a calculation, product applicability decision, or permission to start a solver.
    """
    _validate_meta(meta)
    try:
        result = _physical_preflight(meta, case)
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError) as exc:
        raise ReadinessError('Unsafe/unreadable case input: ' + str(exc)) from exc
    for name in ('milestone_complete', 'boundary_conditions_verified', 'mesh_quality_pass', 'pressure_stability_pass'):
        if name in meta and type(meta[name]) is not bool:
            result['errors'].append('INVALID_BOOLEAN:' + name)
    result['preflight_pass'] = not result['errors']
    result['schema'] = 'valve.readiness/v2'
    result['standards'] = _standards_checks(meta)
    result['requested_checks_pass'] = result['preflight_pass'] and not result['standards']['errors']
    result['engineering_release'] = False
    result['engineering_acceptance'] = 'NOT_ASSESSED'
    result['notes'].extend([
        'preflight_pass covers only legacy physical metadata/file checks; standards is a separate dimension.',
        'requested_checks_pass is not engineering approval. Missing standards on inspect means NOT_CHECKED.',
        'Pinned-card HOLD does not prohibit source inspection or all limited research; source eligibility does not approve calculations.',
        'No solver is launched, even if all requested checks pass.'
    ])
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--case', type=Path)
    args = parser.parse_args(argv)
    try:
        result = audit(_adapter._json(_adapter._read(args.manifest), 'readiness manifest'), args.case)
    except ReadinessError as exc:
        print(json.dumps({'schema': 'valve.readiness/v2', 'status': 'INVALID', 'error': str(exc),
                          'requested_checks_pass': False, 'engineering_release': False,
                          'engineering_acceptance': 'NOT_ASSESSED', 'mutated_case': False,
                          'solver_started': False}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result['requested_checks_pass'] else 2


if __name__ == '__main__':
    sys.exit(main())
