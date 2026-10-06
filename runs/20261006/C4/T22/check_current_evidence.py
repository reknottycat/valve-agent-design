#!/usr/bin/env python3
"""Freshness/assumption gate for a completed C4 study; release remains HOLD."""
import hashlib
import json
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'T06'));sys.path.insert(0,str(BASE/'T15'))
from basis_gate import validate
from calculate_loads import pressure_area_integrity, calculate
from seawater_study import validate_dataset
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    out=BASE/'T22/evidence_gate.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'study_gate':'RUNNING','manufacturing_authorized':False}))
    try:
        paths={'basis':BASE/'T06/research_basis.json','pressure_areas':BASE/'T19/pressure_areas.json','parameters':BASE.parent/'C2/T11/parameters.json','interfaces':BASE.parent/'C3/T11/interface_candidates.json'}
        b,a,p,c=[json.loads(paths[k].read_text()) for k in ('basis','pressure_areas','parameters','interfaces')]
        validate(b);pressure_area_integrity(a)
        loads=json.loads((BASE/'T15/load_study.json').read_text())
        if loads['input_hashes']!={k:sha(v) for k,v in paths.items()} or loads['calculator_sha256']!=sha(BASE/'T15/calculate_loads.py'):
            raise ValueError('Stale load evidence')
        recalculated=calculate(b,a,p,c)
        for key,value in recalculated.items():
            if loads[key]!=value:raise ValueError('Load evidence does not reproduce: '+key)
        if a['extractor_sha256']!=sha(BASE/'T19/extract_pressure_faces.py'):raise ValueError('Stale geometry extractor')
        for relative,digest in a['input_asset_sha256'].items():
            if digest!=sha(BASE.parent/'C2/T12/out'/relative):raise ValueError('Modified STEP input '+relative)
        fluid=json.loads((BASE/'T06/seawater_study_cases.json').read_text())
        validate_dataset(fluid)
        if fluid['script_sha256']!=sha(BASE/'T06/seawater_study.py') or len(fluid['rows'])!=9 or fluid['cold_endpoint_status']!='OUTSIDE_IMPLEMENTED_CORRELATION_DOMAIN_AND_PHASE_UNRESOLVED':raise ValueError('Invalid/stale property evidence')
        source=json.loads((BASE/'T06/research_sources/source_proposal.json').read_text())
        if source['selected_study_basis']['design_pressure_MPa_gauge']!=b['selected_study_inputs']['internal_design_pressure']['value'] or source['selected_study_basis']['physical_proof_test_pressure_MPa'] is not None:
            raise ValueError('Source proposal and project basis disagree')
        plots=json.loads((BASE/'T40/out/plot_sources.json').read_text())
        if plots['load_study_sha256']!=sha(BASE/'T15/load_study.json') or plots['seawater_table_sha256']!=sha(BASE/'T06/seawater_study_cases.json') or plots['plot_script_sha256']!=sha(BASE/'T40/draw_load_study.py'):raise ValueError('Stale graph provenance')
        for name,digest in plots['images'].items():
            if digest!=sha(BASE/'T40/out'/name):raise ValueError('Changed plot')
        negative=[r for r in loads['cases'] if r['pressure_only_unilateral_contact']=='WOULD_REQUIRE_TENSILE_SEAT_REACTION']
        if len(negative)!=4 or not all('forward-free-diagnostic' in r['case'] and r['pressure_only_equilibrium_seat_reaction_z_N']<0 for r in negative):raise ValueError('Missing expected-red free-disc contact cases')
        report={'schema':'valve.c4-evidence-gate/1.0','study_gate':'PASS','load_cases':20,'drive_scenarios':12,'joint_scenarios':9,'property_reference_points':9,'expected_red_free_disc_cases':4,
                'engineering_gates':{'source_pressure_and_selected_assumption':'DISTINCT','physical_proof_test':'NOT_SELECTED','cold_minus2_liquid_properties':'HOLD','property_pressure_dependence':'HOLD','allowables_and_strength':'HOLD','actual_drive_joint_seal_selection':'HOLD','CFD_FEA':'ACTUAL_VALVE_NOT_RUN_IN_C4_STANDARD_BENCHMARKS_SEPARATE'},
                'manufacturing_release':'HOLD','manufacturing_authorized':False,'source_hashes':{k:sha(v) for k,v in paths.items()},'solver_execution_performed':False}
        out.write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    except Exception as exc:
        out.write_text(json.dumps({'study_gate':'FAIL','error':str(exc),'manufacturing_authorized':False}));raise


if __name__=='__main__':main()
