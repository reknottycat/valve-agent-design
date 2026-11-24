import tempfile
import unittest
from pathlib import Path
from mesh_axis import generate
from verify_axis import verify
from set_wedge_patches import convert
from prepare_case import bc_block

class AxisTests(unittest.TestCase):
    def test_pipe_and_nozzle(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'case.msh'
            for fraction in (1.,.5):
                ref=generate(path,fraction)
                self.assertLess(verify(path,ref)['volume_relative_error'],.001)
            with self.assertRaisesRegex(ValueError,'wrong throat'):
                verify(path,dict(ref,throat_radius_m=.1))

    def test_boundary_types(self):
        names=['inlet','outlet','walls','wedgeMinus','wedgePlus']
        text='\n'.join(n+'\n{\n type patch;\n nFaces 10;\n}' for n in names)
        new=convert(text)
        self.assertEqual(new.count('type wedge;'),2)
        self.assertIn('type wall;',new)
        self.assertEqual(bc_block(names[3:],'inlet','outlet',{}).count('type wedge;'),2)
        with self.assertRaises(ValueError): convert(text.replace('wedgePlus','frontback'))

if __name__=='__main__': unittest.main()
