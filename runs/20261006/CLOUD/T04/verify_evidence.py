"""Verify measured C0 negative controls, not merely a generic HOLD decision."""
import json
from pathlib import Path


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    here = Path(__file__).resolve().parent
    audit = json.loads((here / 'evidence/c0_audit.json').read_text())
    require(audit['decision']['decision'] == 'HOLD', 'Original C0 must be held')
    require(audit['decision']['product_solver_authorized'] is False, 'No solver authorization')
    for task in ('fluid_t12', 'fluid_t23'):
        require(audit[task]['measurement_mm']['solid_count'] == 2, task + ' disconnected solid count changed')
        failures = audit[task]['gate']['failures']
        require('UNEXPECTED_SOLID_COUNT' in failures, task + ' missing topology gate')
        require('UNITS_OR_EXTENT_MISMATCH' in failures, task + ' missing unit/extent gate')
    require('STEP_METADATA_DISAGREES_WITH_SOURCE_METRE_CONVENTION' in audit['fluid_t23']['gate']['failures'],
            'Missing explicit STEP metadata rejection')
    require(bool(audit['design_contract_parse_error']), 'Original malformed contract unexpectedly accepted')
    for part in ('lever', 'seat_ring'):
        require(audit['parts'][part]['measurement_mm']['solid_count'] == 2, part + ' topology changed')
        require(audit['parts'][part]['single_component_screen']['status'] == 'FAIL', part + ' missing component screen')
    require(all(v['step_exchange']['status'] == 'PASS' for v in audit['parts'].values()), 'STEP exchange failed')
    print('Observed-red evidence verified: both topology/unit failures, metadata mismatch, malformed contract, multi-solid parts')


if __name__ == '__main__':
    main()
