import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from valve_readiness import audit

class TestReadiness(unittest.TestCase):
    def test_budget_scope(self):
        r=audit({'domain_scope':'whole_valve','execution_budget':{'scope':'local_metadata','cells':4096}})
        self.assertIn('BUDGET_SCOPE_MISMATCH',r['errors'])
    def test_large_cap_not_required(self):
        r=audit({'domain_scope':'whole_valve','execution_budget':{'scope':'whole_valve','cells':12000000,'meaning':'engineering_required_cells'}})
        self.assertIn('EXECUTION_CAP_IS_NOT_REQUIRED_RESOLUTION',r['errors'])
    def test_completed_not_repeated(self):
        self.assertIn('COMPLETED_MILESTONE_RERUN_WITHOUT_NEW_OBJECTIVE',audit({'requested_action':'solve','milestone_complete':True})['errors'])
    def test_new_objective_not_forbidden(self):
        self.assertNotIn('COMPLETED_MILESTONE_RERUN_WITHOUT_NEW_OBJECTIVE',audit({'requested_action':'solve','milestone_complete':True,'new_objective':'grid sensitivity'})['errors'])
    def test_pressure_not_guessed(self):
        self.assertIn('DESIGN_PRESSURE_IS_NOT_VERIFIED_PRESSURE_DROP',audit({'requested_action':'solve','pressure_role':'design_pressure_as_pressure_drop'})['errors'])
    def test_empty_case(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'system').mkdir();(p/'system/fvSolution').write_text('solvers { /* nothing */ }')
            r=audit({'requested_action':'solve'},p)
            self.assertIn('EMPTY_SOLVERS',r['errors']);self.assertIn('MISSING_FILE:0/U',r['errors'])
    def test_inspect_not_solver_gate(self):
        self.assertTrue(audit({'requested_action':'inspect','pressure_stability_pass':True})['preflight_pass'])
    def test_quality_not_waived(self):
        self.assertIn('MESH_QUALITY_NOT_PASSED',audit({'requested_action':'solve','mesh_quality_pass':False})['errors'])


    def test_unknown_action(self):
        self.assertIn('UNKNOWN_REQUESTED_ACTION',audit({'requested_action':'slove'})['errors'])
    def test_domain_required(self):
        self.assertIn('MISSING_DOMAIN_SCOPE',audit({'requested_action':'solve'})['errors'])
    def test_string_false_not_verification(self):
        self.assertIn('BOUNDARY_CONDITIONS_UNVERIFIED',audit({'requested_action':'solve','boundary_conditions_verified':'false'})['errors'])
    def test_presence_positive_is_not_physics(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            names=['0/U','0/p','system/controlDict','system/fvSchemes','system/fvSolution','constant/transportProperties']
            names += ['constant/polyMesh/'+n for n in ('points','faces','owner','neighbour','boundary')]
            for name in names:
                f=p/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_text('synthetic presence fixture')
            (p/'system/fvSolution').write_text('solvers { p { solver PCG; } U { solver smoothSolver; } }')
            r=audit({'requested_action':'solve','domain_scope':'synthetic','boundary_conditions_verified':True,'mesh_stage':'retained_fluid_mesh','mesh_quality_pass':True},p)
            self.assertTrue(r['preflight_pass']);self.assertFalse(r['solver_started'])

if __name__=='__main__':unittest.main()
