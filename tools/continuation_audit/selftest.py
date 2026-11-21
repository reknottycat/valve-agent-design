#!/usr/bin/env python3
"""Portable tiny synthetic checks only; no real field or solver fixture."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from window_contract import WindowContract
from checkpoint_io import scan_outputs


def rejected(call):
    try:
        call()
    except (ValueError, TypeError, AssertionError):
        return
    raise AssertionError('negative case was accepted')


def main():
    if not __debug__:
        raise RuntimeError('run without Python -O')
    spec = dict(schema_version=1,start=19,end=21,restart_index=99,delta_t=1,delta_t0=1,cumulative_continuity=-1e-7)
    c = WindowContract.from_dict(spec)
    assert c.index_for(20) == 100 and c.time_name(20) == '20'
    rejected(lambda: WindowContract.from_dict(dict(spec,start=True)))
    rejected(lambda: WindowContract.from_dict(dict(spec,unknown=1)))
    rejected(lambda: WindowContract.from_dict(dict(spec,end=22)))
    with tempfile.TemporaryDirectory(prefix='continuation-audit-test-') as temp:
        root=Path(temp); case=root/'case';case.mkdir();(case/'system').mkdir();(root/'tmp').mkdir()
        for name in ('19','constant'):
            target=root/('source-'+name);target.mkdir();(case/name).symlink_to(target,target_is_directory=True)
        bindings={name:str((case/name).resolve()) for name in ('19','constant')}
        stages={}
        for state in c.output_states:
            n=str(state);out=case/n;(out/'uniform').mkdir(parents=True)
            for field,kind in [('U','volVectorField'),('p','volScalarField'),('phi','surfaceScalarField')]:
                (out/field).write_text('FoamFile\n{\nclass '+kind+';\nobject '+field+';\n}\n// synthetic headers, no field values\n')
            (out/'uniform/time').write_text(f'value {state};\nname "{n}";\nindex {c.index_for(state)};\ndeltaT 1;\ndeltaT0 1;\n')
            (out/'uniform/cumulativeContErr').write_text('value -1e-7;\n')
            stages[n]={'index':c.index_for(state),'cumulativeContErr':-1e-7}
        status=scan_outputs(case,bindings,c,require_complete=True,expected_stages=stages)
        assert status['complete'] and not status['restart_qualified']
        (case/'20/uniform/time').write_text('value 20;\nname "20";\nindex 20;\ndeltaT 1;\ndeltaT0 1;\n')
        assert scan_outputs(case,bindings,c,require_complete=True,expected_stages=stages)['violations']
        (root/'contract.json').write_text(json.dumps(spec));(root/'ids.json').write_text(json.dumps(list(range(38))))
        (root/'incomplete.log').write_text('SIMPLE_CONTINUATION_COMPLETE\n')
        result=subprocess.run([sys.executable,'-I','-B',str(Path(__file__).with_name('audit.py')),
            '--log',str(root/'incomplete.log'),'--ids',str(root/'ids.json'),'--contract',str(root/'contract.json'),
            '--output',str(root/'must-not-exist.json')],capture_output=True,text=True,timeout=3)
        assert result.returncode==1 and 'AUDIT_REJECTED' in result.stderr and not (root/'must-not-exist.json').exists()
    print('PASS: synthetic contract/index/checkpoint metadata and actual CLI rejection; not native restart validation')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
