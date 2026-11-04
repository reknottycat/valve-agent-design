"""Read-only binding of one reviewed native observation, not a capacity calculator.

The immutable profile authenticates selected bytes only. It does not authenticate
an entire case, mesh, R1, product configuration, or physical validity.
"""
import math
import re
from pathlib import Path

PROFILE = 'native-simple-state21/v1'
LOCK_SHA256 = '23ff01987d8813fc51c4ca7decb11976e69c8e5baccb31f794cdb9fb31712ae1'
ROLES = {'raw_log', 'observation', 'observer_source', 'runner_source', 'transport', 'model', 'numerics'}
FORMULAS = ('F-FLW-001', 'F-FLW-002')
STATE = 21
SEMANTICS = 'static_area_mean_kinematic_inlet_reference'
STAGE = 'final conservative phi correction2; post-p.relax and U correction; endpoint observer before nonmutating checkpoint write'


def _need(condition, message, adapter):
    if not condition:
        raise adapter.AdapterError('Flow binding: ' + message)


def _real_path(value, adapter):
    _need(type(value) is str and bool(value.strip()), 'path must be a nonempty string', adapter)
    path = Path(value)
    _need(path.is_absolute() and str(path) == value and '..' not in path.parts,
          'path must be canonical absolute realpath', adapter)
    for component in (path, *path.parents):
        _need(not component.is_symlink(), 'symlink not allowed; supply explicit resolved path', adapter)
    _need(str(path.resolve(strict=False)) == value, 'noncanonical realpath', adapter)
    return path


def _one(lines, prefix, adapter):
    matches = [(i + 1, line.split()) for i, line in enumerate(lines) if line.startswith(prefix + ' ')]
    _need(len(matches) == 1, 'missing/duplicate record ' + prefix, adapter)
    return matches[0]


def _number(value, adapter):
    _need(type(value) in (int, float) and math.isfinite(value), 'expected finite numeric value (not bool)', adapter)
    return value


def _close(a, b, adapter):
    _number(a, adapter); _number(b, adapter)
    _need(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-30), 'arithmetic/source disagreement', adapter)


def _extract(files, adapter):
    """Called only after every selected input is authenticated; never execute sources."""
    text = {role: raw.decode('utf-8') for role, raw in files.items() if role != 'observation'}
    doc = adapter._json(files['observation'], 'authenticated state21 observation')
    lines = text['raw_log'].splitlines()
    line, record = _one(lines, 'CONT_PORTS 21', adapter)
    _need(len(record) == 12 and record[-1] == SEMANTICS and record[9] == '1',
          'port role/unit/validity mismatch', adapter)
    keys = ('Ain_m2', 'Aout_m2', 'Qin_m3_s', 'Qout_m3_s', 'pinMean_m2_s2',
            'poutMean_m2_s2', 'DeltaPkin_m2_s2', 'K')
    values = [float(x) for x in record[2:9]] + [float(record[10])]
    ports = doc['ports']['21']
    _need(ports['K_valid'] is True, 'K_valid must be true arithmetic guard', adapter)
    for key, value in zip(keys, values):
        _close(value, ports[key], adapter)
    a, ao, qi, qo, pi, po, dp, k = values
    _need(a > 0 and ao > 0 and qi < -1e-12 and qo > 0 and dp > 0 and k > 0,
          'invalid area/flow orientation/positive proxy branch', adapter)
    _close(dp, pi - po, adapter)
    speed = abs(qi) / a
    _close(k, 2 * dp / speed ** 2, adapter)
    for idx, name, area, pressure, flow in [(78, 'inlet', a, pi, qi), (33, 'outlet', ao, po, qo)]:
        _, patch = _one(lines, 'CONT_PATCH 21 ' + str(idx), adapter)
        matches = [p for p in doc['patches']['21'] if p['id'] == idx]
        _need(len(matches) == 1 and matches[0]['name'] == name and patch[3] == name,
              'port identity mismatch', adapter)
        for key, expected, raw in zip(('area_m2', 'mean_pkin_m2_s2', 'signedQ_m3_s'),
                                      (area, pressure, flow), patch[9:12]):
            _close(matches[0][key], expected, adapter); _close(float(raw), expected, adapter)
    _, begin = _one(lines, 'CONT_STATE_BEGIN 21', adapter)
    _, end = _one(lines, 'CONT_STATE_END 21', adapter)
    _, checkpoint = _one(lines, 'CONT_CHECKPOINT_WRITTEN 21', adapter)
    identity = doc['state_fields_nuEff_hashes']['21'][0]
    written = doc['native_stages']['written_checkpoints']['21']
    _need(identity == begin[2] == end[2] == written['physical_hidden_state_hash']
          and written['index'] == 21 and identity in checkpoint,
          'state/stage identity mismatch', adapter)
    _need(doc['native_stages']['actual_final_phi']['21'] ==
          {'actual_corr': 2, 'oriented': True, 'adjustClosed': False}, 'final conservative phi mismatch', adapter)
    for key in ('sustained_nonlinear_steady_convergence', 'research_continuation_signal',
                'engineering_release', 'imposed_Q_and_derived_K_independent_validation'):
        _need(doc[key] is False, 'unexpected physical/status claim: ' + key, adapter)
    # Cross-check implementation definitions, not merely names in a derived JSON.
    for token in ('psa+=ap[j]*p.boundaryField()[k][j]', 'q+=fp[j]',
                  'K=2*dp/(speed*speed)', 'mag(flows[0])/areas[0]',
                  'k==78?"inlet":"outlet"', SEMANTICS):
        _need(token in text['observer_source'], 'observer definition mismatch', adapter)
    for token in ('p.dimensions()==dimensionSet(0,2,-2,0,0,0,0)',
                  'phi.dimensions()==dimensionSet(0,3,-1,0,0,0,0)',
                  'turbulence->type()=="Stokes"', 'p.relax();U=HbyA-rAtU()*fvc::grad(p)',
                  'observeContinuation(label(runTime.value())'):
        _need(token in text['runner_source'], 'runner unit/stage/model mismatch', adapter)
    _need('transportModel Newtonian;' in text['transport'] and
          re.search(r'\bsimulationType\s+laminar\s*;', text['model']), 'model mismatch', adapter)
    nu = re.search(r'\bnu\s+\[0 2 -1 0 0 0 0\]\s+([^;]+);', text['transport'])
    _need(nu is not None, 'unknown viscosity units', adapter)
    nu_value = _number(float(nu.group(1)), adapter)
    _need(nu_value > 0, 'nonpositive viscosity', adapter)
    relaxation = re.search(r'relaxationFactors\s*\{\s*fields\s*\{\s*p\s+(\S+);\s*\}\s*equations\s*\{\s*U\s+(\S+);', text['numerics'])
    _need(relaxation is not None, 'unknown relaxation inputs', adapter)
    _close(float(relaxation[1]), 0.3, adapter); _close(float(relaxation[2]), 0.7, adapter)
    change = _number(doc['DeltaP_relative_change20to21'], adapter)
    _close(change, abs(dp - doc['ports']['20']['DeltaPkin_m2_s2']) /
           abs(doc['ports']['20']['DeltaPkin_m2_s2']), adapter)
    return {'state': STATE, 'state_kind': 'SIMPLE iteration endpoint, not demonstrated physical seconds',
            'stage': STAGE, 'physical_hidden_state_hash': identity,
            'raw_record_line': line, 'json_locator': 'ports.21',
            'pressure_role': 'area-weighted static kinematic pressure; not wall-tap or total pressure',
            'pressure_dimensions': [0, 2, -2, 0, 0, 0, 0],
            'flux_role': 'signed conservative phi; outward positive; reference speed uses abs(Qin)',
            'reference_area': 'inlet patch78 reduced face area, not nominal DN',
            'port_ids': {'inlet': 78, 'outlet': 33},
            'inputs': {key: {'value': value, 'unit': ('m^2' if key.startswith('A') else
                       'm^3/s' if key.startswith('Q') else '1' if key == 'K' else 'm^2/s^2')}
                       for key, value in zip(keys, values)},
            'model': {'transport': 'Newtonian', 'simulation': 'laminar', 'stress': 'Stokes',
                      'nu': {'value': nu_value, 'unit': 'm^2/s',
                             'role': 'frozen numerical research constant, not measured actual-fluid property'}},
            'arithmetic_witness': {'status': 'PASS', 'scope': 'identity and arithmetic only, not physics',
                                   'formula': 'K_proxy = 2*(pin_static_kin-pout_static_kin)/(|Qin|/Ain)^2',
                                   'u_reference_m_s': speed, 'K_proxy': 2 * dp / speed ** 2},
            'numerics': {'p_relaxation': float(relaxation[1]), 'U_relaxation': float(relaxation[2]),
                         'unit': '1', 'role': 'dimensionless relaxation, not pressure'},
            'steady_evidence': {'sustained_steady': False, 'research_signal': False,
                                'relative_static_dp_change20to21': change,
                                'acceptance_threshold': None}}


def bind(declaration, standards, adapter, standards_root=None):
    _need(type(declaration) is dict and set(declaration) == {'profile', 'paths'},
          'requires exactly profile and paths; values/status/units cannot be supplied', adapter)
    _need(declaration['profile'] == PROFILE, 'unknown profile/state', adapter)
    paths = declaration['paths']
    _need(type(paths) is dict and set(paths) == ROLES, 'requires exact seven evidence roles', adapter)
    lock_raw = adapter._read(Path(__file__).with_name('state21-input.lock.json'))
    _need(adapter._digest(lock_raw) == LOCK_SHA256, 'immutable input lock mismatch', adapter)
    lock = adapter._json(lock_raw, 'state21 input lock')
    result = {'profile': PROFILE, 'status': 'HOLD', 'source_binding_status': 'HOLD',
              'applicability_status': 'HOLD', 'missing_reasons': [], 'sources': [], 'formulas': [],
              'observation': None, 'Kv_m3_h': None, 'Cv': None, 'delta_p_Pa': None,
              'rho_actual_kg_m3': None, 'rho_ref': None, 'engineering_release': False,
              'integrity_scope': 'selected seven file bytes only; checkpoint21 U/p/phi bytes and full mesh NOT revalidated at runtime; no full case/R1/product authentication',
              'configuration_authenticated': False, 'legacy_case_preflight_performed_by_binding': False}
    captured = {}
    for role in sorted(ROLES):
        path = _real_path(paths[role], adapter)
        try:
            path.stat()
        except FileNotFoundError:
            result['missing_reasons'].append('MISSING_SOURCE:' + role)
            continue
        raw = adapter._read(path)
        entry = lock['files'][role]
        _need(len(raw) == entry['bytes'] and adapter._digest(raw) == entry['sha256'],
              'source digest/size mismatch: ' + role, adapter)
        captured[role] = raw
        result['sources'].append({'role': role, 'path': str(path), 'sha256': entry['sha256'], 'bytes': len(raw)})
    if len(captured) == len(ROLES):
        try:
            result['observation'] = _extract(captured, adapter)
        except (KeyError, IndexError, TypeError, ValueError, UnicodeError, OverflowError) as exc:
            raise adapter.AdapterError('Flow binding source semantics invalid: ' + str(exc)) from exc
        result['source_binding_status'] = 'PASS'
    refs = {r['id']: r for r in standards.get('references', [])}
    if not all(fid in refs for fid in FORMULAS):
        result['missing_reasons'].append('MISSING_EXPLICIT_CURRENT_FFLW001_002_DECLARATIONS')
    else:
        current = adapter.StandardsAdapter(standards_root)
        for fid in FORMULAS:
            item = current.query(record_id=fid)['results'][0]
            record = item['record']
            result['formulas'].append(dict(id=fid, use=refs[fid]['use'],
                source_status=item['source_status'], source_grade=item['source_grade'],
                upstream_calc_eligibility=item['upstream_calc_eligibility'], provenance=item['provenance'],
                expression=record['expression'], applicability=record['applicability'], variables=record['variables']))
        contract = current.query(record_id='F-FLW-001')['results'][0]['record']['research_contract']
        _need(contract['rho_ref_kg_m3'] == 1000 and contract['sufficiently_turbulent_nonchoked'] is True
              and contract['steady_single_phase_Newtonian_incompressible'] is True
              and contract['same_reference_area_taps_opening_required'] is True
              and contract['installation_corrections_not_included'] is True
              and contract['IEC_clause_verified'] is False, 'current formula contract mismatch', adapter)
        # Source records were authenticated by the current adapter before bind().
        result['required_research_contract'] = dict(contract)
        result['rho_ref'] = {'value': contract['rho_ref_kg_m3'], 'unit': 'kg/m^3', 'role': 'explicit F-FLW-001 research convention; not actual rho or verified exact IEC value'}
    observation = result['observation']
    candidate_area = observation['inputs']['Ain_m2']['value'] if observation else None
    proxy_k = observation['inputs']['K']['value'] if observation else None
    source_locator = ({'role': 'observation', 'locator': 'ports.21',
                       'crosscheck_role': 'raw_log', 'line': observation['raw_record_line']}
                      if observation else None)
    result['variable_bindings'] = {
        'F-FLW-001': {
            'A': {'value': None, 'unit': 'm^2', 'candidate_value': candidate_area,
                  'candidate_source': source_locator,
                  'role': 'numerical inlet reference area only; not approved formula substitution',
                  'status': 'HOLD', 'reason': 'product geometry/opening/taps/reference-area mapping unverified'},
            'zeta': {'value': None, 'unit': '1', 'observed_proxy_K': proxy_k,
                     'candidate_source': source_locator, 'status': 'HOLD',
                     'reason': ('laminar nonsteady static CFD proxy is not applicable product zeta; no direct substitution'
                                if observation else 'authenticated observation unavailable; no zeta input')},
            'rho_ref': {'value': result['rho_ref']['value'] if result['rho_ref'] else None,
                        'unit': 'kg/m^3', 'role': 'current formula research convention; not actual rho',
                        'source': 'F-FLW-001.research_contract.rho_ref_kg_m3' if result['rho_ref'] else None},
            'Kv': {'value': None, 'unit': 'm^3/h', 'status': 'HOLD',
                   'reason': 'formula not evaluated; required applicable inputs unavailable'}},
        'F-FLW-002': {
            'Kv': {'value': None, 'unit': 'm^3/h at reference 1 bar', 'status': 'HOLD',
                   'dependency': 'F-FLW-001.Kv', 'reason': 'upstream capacity remains HOLD'},
            'Cv_US': {'value': None, 'unit': 'US gal/min at reference 1 psi', 'status': 'HOLD',
                      'reason': 'no eligible Kv to convert; conversion adds no capacity evidence'}}}
    if result['source_binding_status'] != 'PASS':
        result['missing_reasons'].append('OBSERVATION_SEMANTICS_NOT_CHECKED_MISSING_AUTHENTICATED_SOURCES')
        return result
    result['missing_reasons'].extend([
        'LAMINAR_STOKES_INCOMPATIBLE_WITH_SUFFICIENTLY_TURBULENT_FFLW001_BRANCH',
        'SUSTAINED_STEADY_NOT_ESTABLISHED', 'ACTUAL_DENSITY_MISSING',
        'PRODUCT_GEOMETRY_OPENING_AND_REFERENCE_AREA_MAPPING_UNVERIFIED',
        'STANDARD_TAPS_INSTALLATION_AND_STATIC_PRESSURE_EQUIVALENCE_UNVERIFIED',
        'PHASE_TEMPERATURE_ABSOLUTE_PRESSURE_NONCAVITATION_NONCHOKING_UNKNOWN',
        'INDEPENDENT_PHYSICAL_VALIDATION_AND_APPROVED_ACCEPTANCE_MISSING',
        'FFLW001_002_SOURCE_CLAUSES_NOT_VERIFIED'])
    return result
