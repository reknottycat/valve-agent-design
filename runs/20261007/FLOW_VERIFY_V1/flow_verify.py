#!/usr/bin/env python3
"""Pinned, additive Re10 valve diagnostic. No installs, source edits or implicit resume."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
MANIFEST = HERE / 'manifest.json'
MANIFEST_SHA256 = '7559f772e025b4d3ec27cc31ec43b0ca02ec92713992a5b71e7dca26f0cc0a9b'

def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n')

def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}

def run(argv, log, cwd=None):
    with Path(log).open('w') as stream:
        result = subprocess.run([str(x) for x in argv], cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    need(result.returncode == 0, 'Command failed (%s): %s; see %s' % (result.returncode, argv[0], log))
    return result.returncode

def source_check(manifest, repo=REPO):
    checked = {}
    for entry in manifest['sources']:
        path = repo / entry['path']
        need(path.is_file() and not path.is_symlink(), 'Missing/linked fixed source: ' + entry['path'])
        need(sha(path) == entry['sha256'], 'Fixed source changed: ' + entry['path'])
        checked[entry['path']] = entry['sha256']
    if 'selected' in manifest:
        plan = json.loads((repo / manifest['sources'][0]['path']).read_text())
        selected = manifest['selected']
        expected = {**plan['selected_study_property_state'], **plan['cases'][0],
                    'nominal_diameter_m':plan['nominal_diameter_m'],
                    'nominal_circle_area_m2':plan['nominal_circle_area_m2'],
                    'pose':plan['pose'], 'domain':plan['domain'],
                    'pressure_interpretation':plan['pressure_interpretation']}
        need(selected == expected, 'Selected case differs from fixed current-flow Re10 input')
    return checked

def verify_mesh(root, manifest, output):
    root = root.resolve()
    pinned = manifest['mesh']['manifest_sha256']
    need(sha(root / 'revalidation_manifest.json') == pinned, 'Mesh v2 manifest differs from R1 pin')
    # Full official v2 inventory seal (not just the five core arrays).
    run([sys.executable, '-B', '-O', root / 'scripts/finalize_v2.py',
         '--manifest', root / 'revalidation_manifest.json', '--manifest-sha256', pinned,
         '--output', output / 'mesh-seal.json'], output / 'mesh-seal.log')
    need(json.loads((output / 'mesh-seal.json').read_text())['status'] == 'PASS', 'Mesh seal failed')
    original = root / 'data/final_candidate/constant/polyMesh'
    for name, expected in manifest['mesh']['files'].items():
        need(sha(original / name) == expected, 'Wrong final mesh file: ' + name)
    return original

def foam(path, name, content, cls='dictionary'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('FoamFile { version 2.0; format ascii; class ' + cls + '; object ' + name + '; }\n' + content + '\n')

def prepare_case(output, original, manifest):
    case = output / 'case'
    (case / 'constant').mkdir(parents=True)
    shutil.copytree(original, case / 'constant/polyMesh')
    s = manifest['selected']
    u = format(s['inlet_fixed_face_speed_m_s'], '.17g')
    # Exact BC types taken from C0 write_case; numeric inputs from current-flow.
    foam(case/'0/U', 'U', 'dimensions [0 1 -1 0 0 0 0];\ninternalField uniform (0 0 0);\nboundaryField {\n'
         'inlet { type fixedValue; value uniform ('+u+' 0 0); }\n'
         'outlet { type zeroGradient; }\nwall { type noSlip; }\n}', 'volVectorField')
    foam(case/'0/p', 'p', 'dimensions [0 2 -2 0 0 0 0];\ninternalField uniform 0;\nboundaryField {\n'
         'inlet { type zeroGradient; }\noutlet { type fixedValue; value uniform 0; }\nwall { type zeroGradient; }\n}', 'volScalarField')
    foam(case/'constant/transportProperties', 'transportProperties',
         'transportModel Newtonian;\nnu [0 2 -1 0 0 0 0] '+format(s['kinematic_viscosity_m2_s'], '.17g')+';')
    foam(case/'constant/turbulenceProperties', 'turbulenceProperties', 'simulationType laminar;')
    functions = []
    for name, patch, operation, field in [('qIn','inlet','sum','phi'), ('qOut','outlet','sum','phi'),
                                         ('qWall','wall','sum','phi'), ('pIn','inlet','areaAverage','p'),
                                         ('pOut','outlet','areaAverage','p')]:
        functions.append(name+' { type surfaceFieldValue; libs ("libfieldFunctionObjects.so"); '
                         'regionType patch; name '+patch+'; operation '+operation+'; fields ('+field+'); '
                         'writeFields false; log true; writePrecision 17; '
                         'executeControl timeStep; executeInterval 1; writeControl timeStep; writeInterval 1; }')
    foam(case/'system/controlDict','controlDict',
         'application simpleFoam; startFrom startTime; startTime 0; stopAt endTime; endTime 5000; deltaT 1;\n'
         'writeControl timeStep; writeInterval 100; purgeWrite 2; writeFormat ascii; writePrecision 17;\n'
         'writeCompression off; timeFormat general; timePrecision 12; runTimeModifiable false;\n'
         'functions {\n'+'\n'.join(functions)+'\n}')
    foam(case/'system/fvSchemes','fvSchemes',
         'ddtSchemes { default steadyState; }\ngradSchemes { default Gauss linear; }\n'
         'divSchemes { default none; div(phi,U) bounded Gauss upwind; div((nuEff*dev2(T(grad(U))))) Gauss linear; }\n'
         'laplacianSchemes { default Gauss linear corrected; }\ninterpolationSchemes { default linear; }\n'
         'snGradSchemes { default corrected; }\nfluxRequired { default no; p; }')
    # Fixed iteration budget supports a 100-iteration stabilization window; no early residual-only success.
    foam(case/'system/fvSolution','fvSolution',
         'solvers { p { solver GAMG; tolerance 1e-11; relTol 0; smoother GaussSeidel; maxIter 1000; } '
         'U { solver smoothSolver; smoother symGaussSeidel; tolerance 1e-12; relTol 0; maxIter 1000; } }\n'
         'SIMPLE { nNonOrthogonalCorrectors 3; consistent no; }\n'
         'relaxationFactors { fields { p 0.3; } equations { U 0.7; } }')
    return case

def environment():
    commands = {name: shutil.which(name) for name in ['simpleFoam', 'checkMesh', 'wmake']}
    return {'platform': platform.platform(), 'python': sys.version, 'commands': commands,
            'WM_PROJECT_VERSION': os.environ.get('WM_PROJECT_VERSION'),
            'WM_OPTIONS': os.environ.get('WM_OPTIONS'),
            'missing_commands': [k for k,v in commands.items() if not v]}

def runtime_fingerprint(env, output):
    result = {}
    for name, path in env['commands'].items():
        item = {'path': str(Path(path).resolve()), 'sha256': sha(path)}
        if name != 'wmake':
            proc = subprocess.run(['ldd', path], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (output/('ldd.'+name+'.log')).write_text(proc.stdout)
            need(proc.returncode == 0 and 'not found' not in proc.stdout, 'Unresolved solver libraries: '+name)
            libraries = re.findall(r'(?:=>\s+)?(/[^\s()]+)', proc.stdout)
            item['libraries'] = {x: sha(x) for x in libraries if Path(x).is_file()}
        result[name] = item
    write_json(output/'runtime-fingerprints.json', result)

def check_mesh_log(path):
    text = path.read_text()
    need('OPENFOAM=1912' in text, 'Expected OpenCFD OpenFOAM 1912 runtime, do not silently switch distribution')
    need('scalar=64' in text, 'Double-precision OpenFOAM required')
    need('Mesh OK.' in text and not re.search(r'FOAM FATAL|Failed \d+ mesh checks', text), 'Fresh native mesh check failed')
    def value(pattern):
        found = re.search(pattern, text)
        need(found is not None, 'Missing checkMesh metric: '+pattern)
        return float(found[1].rstrip('.'))
    metrics = {
        'cells': value(r'\bcells:\s+(\d+)'), 'points': value(r'\bpoints:\s+(\d+)'),
        'faces': value(r'\bfaces:\s+(\d+)'),
        'nonorth_max_degrees': value(r'Mesh non-orthogonality Max:\s+([\d.eE+-]+)'),
        'faces_over_70_degrees': value(r'non-orthogonal \(> 70 degrees\) faces:\s+(\d+)'),
        'max_skewness': value(r'Max skewness\s*=\s*([\d.eE+-]+)'),
        'min_determinant': value(r'Cell determinant \(wellposedness\) : minimum:\s*([\d.eE+-]+)'),
        'total_volume_m3': value(r'Total volume\s*=\s*([\d.eE+-]+)')}
    need(all(math.isfinite(x) for x in metrics.values()), 'Non-finite mesh metric')
    need((metrics['cells'],metrics['points'],metrics['faces']) == (411099,90900,865251), 'Wrong mesh counts')
    need(metrics['faces_over_70_degrees'] == 54 and metrics['nonorth_max_degrees'] <= 77.471485,
         'Changed nonorthogonality warning set')
    need(metrics['max_skewness'] <= 1.60 and metrics['min_determinant'] >= 0.001,
         'Mesh diagnostic threshold failed')
    need(abs(metrics['total_volume_m3'] - 0.064435406187606445) < 1e-12, 'Mesh volume drift')
    need('Number of regions: 1 (OK)' in text, 'Mesh not a single connected region')
    return {'status':'PASS_WITH_RETAINED_WARNINGS', 'metrics':metrics, 'log_sha256':sha(path),
            'warning_policy':'54 faces >70 degrees are retained; this does not establish PDE accuracy'}

def finite_fields(case, manifest):
    times = sorted((float(p.name), p) for p in case.iterdir() if p.is_dir() and re.fullmatch(r'\d+(?:\.\d+)?',p.name) and float(p.name)>0)
    need(bool(times), 'No final solved fields')
    time, directory = times[-1]
    need(time == 5000, 'Solver did not reach fixed 5000-iteration budget')
    result = {'time':time,'files':{}}
    for name, components in [('U',3),('p',1),('phi',1)]:
        path = directory/name
        need(path.is_file(), 'Missing final field '+name)
        text = re.sub(r'/\*.*?\*/|//[^\n]*', '', path.read_text(), flags=re.S)
        need(not re.search(r'(?i)\b(?:nan|inf|infinity)\b',text),'Non-finite field '+name)
        need(re.search(r'format\s+ascii\s*;', text) is not None,'Expected ASCII field '+name)
        arrays = re.findall(r'(?:internalField|value)\s+nonuniform\s+List<\w+>\s+(\d+)\s*\((.*?)\)\s*;',text,re.S)
        values = []
        for count, body in arrays:
            numbers = [float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',body)]
            need(len(numbers) == int(count)*components,'Malformed field list '+name)
            values.extend(numbers)
        for body in re.findall(r'(?:internalField|value)\s+uniform\s+([^;]+);',text):
            values.extend(float(x) for x in re.findall(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?',body))
        need(bool(values) and all(math.isfinite(x) for x in values),'Empty/nonfinite values '+name)
        maximum = max(abs(x) for x in values)
        if name == 'U':
            need(maximum <= 100*manifest['selected']['inlet_fixed_face_speed_m_s'],'Velocity numerical blow-up guard failed')
        if name == 'p':
            need(maximum <= 1,'Kinematic-pressure numerical blow-up guard failed')
        if name == 'phi':
            wall = re.search(r'\bwall\s*\{([^{}]*)\}', text, re.S)
            need(wall is not None, 'Wall phi missing')
            b = wall[1]
            if re.search(r'value\s+uniform\s+0(?:\.0*)?\s*;',b):
                leakage = 0.0
            else:
                a = re.search(r'value\s+nonuniform\s+List<scalar>\s+(\d+)\s*\((.*?)\)\s*;',b,re.S)
                need(a is not None,'Wall phi values unreadable')
                vv=[float(x) for x in a[2].split()]
                need(len(vv)==84534==int(a[1]),'Wall phi size mismatch')
                leakage=sum(abs(x) for x in vv)
            # Fixed inlet area flux is nonzero; final postprocessor also checks Qin/Qout.
            need(leakage <= manifest['selected']['nominal_circle_flow_m3_s']*1e-10,'Wall absolute flux leakage')
            result['wall_absolute_flux_m3_s']=leakage
        result['files'][name]={'sha256':sha(path),'maximum_absolute_component':maximum}
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New empty output path outside frozen sources')
    parser.add_argument('--run', action='store_true', help='Run native prechecks, then exactly one Re10 solve')
    args=parser.parse_args()
    output=args.output.resolve()
    need(not output.exists(),'Output must be a new path; no implicit resume/overwrite')
    need(not output.is_relative_to(REPO) and not output.is_relative_to(args.mesh_root.resolve()),
         'Execution output must be outside repository and mesh archive tree')
    output.mkdir(parents=True)
    report={'status':'RUNNING','started_utc':datetime.now(timezone.utc).isoformat(),
            'manufacturing_authorized':False,'actual_mesh_flux_m3_s':None,
            'computed_pressure_drop_Pa':None,'computed_loss_coefficient':None}
    write_json(output/'run_record.json',report)
    write_json(output/'results.json', dict(report))
    try:
        need(sha(MANIFEST)==MANIFEST_SHA256, 'Package manifest differs from reviewed fixed digest')
        m=json.loads(MANIFEST.read_text())
        report['source_hashes']=source_check(m)
        report['package_sha256']={k:v for k,v in inventory(HERE).items() if not k.startswith('evidence/')}
        report['manifest_sha256']=sha(MANIFEST)
        original=verify_mesh(args.mesh_root,m,output)
        case=prepare_case(output,original,m)
        inputs={p:sha(case/p) for p in inventory(case)}
        write_json(output/'case-inputs.json',inputs)
        report['case_inputs_sha256']=sha(output/'case-inputs.json')
        env=environment();write_json(output/'environment.json',env)
        report['environment']=env
        if env['missing_commands']:
            report.update(status='BLOCKED', blocker={'id':'OPENFOAM_1912_RUNTIME_UNAVAILABLE',
                          'detail':'A loaded double-precision OpenCFD 1912 development runtime is required (simpleFoam/checkMesh/wmake).',
                          'missing':env['missing_commands']}, case_prepared=True)
            write_json(output/'run_record.json',report)
            write_json(output/'results.json',report)
            print(json.dumps({'status':report['status'],'blocker':report['blocker'],'output':str(output)},indent=2))
            return 3
        if not args.run:
            report.update(status='PREPARED_NOT_RUN',case_prepared=True)
            write_json(output/'run_record.json',report);write_json(output/'results.json',report)
            return 0
        runtime_fingerprint(env,output)
        mesh_before=inventory(case/'constant/polyMesh')
        run(['checkMesh','-case',case,'-allTopology','-allGeometry'],case/'log.checkMesh')
        mesh_report=check_mesh_log(case/'log.checkMesh')
        write_json(output/'mesh-check.json',mesh_report)
        need(inventory(case/'constant/polyMesh')==mesh_before,'Native check changed frozen mesh bytes')
        run([sys.executable,'-B',HERE/'native_gate.py','--case',case,'--output',output/'native'],output/'native-gate.log')
        native=json.loads((output/'native/report.json').read_text())
        need(native['status']=='PASS','Native field/PDE prerequisites not passed')
        need(all(sha(case/p)==v for p,v in inputs.items()),'Case inputs changed before solve')
        report['solver_returncode']=run(['simpleFoam','-case',case],case/'log.simpleFoam')
        solver_log=(case/'log.simpleFoam').read_text()
        need('OPENFOAM=1912' in solver_log and 'scalar=64' in solver_log,
             'Actual simpleFoam runtime is not double-precision OpenFOAM 1912')
        need(all(sha(case/p)==v for p,v in inputs.items()),'Case inputs changed during solve')
        report['field_check']=finite_fields(case,m)
        write_json(output/'field-check.json',report['field_check'])
        report['status']='SOLVER_COMPLETED';write_json(output/'run_record.json',report)
        try:
            run([sys.executable,'-B',HERE/'postprocess.py','--run-root',output,'--manifest',MANIFEST],output/'postprocess.log')
        finally:
            shutil.copy2(output/'results.json',output/'postprocess-results.json')
        results=json.loads((output/'results.json').read_text())
        need(results['status']=='DIAGNOSTIC_PASS','Flow convergence/conservation gate failed')
        source_check(m)
        report.update(status='DIAGNOSTIC_PASS',raw_case_inventory=inventory(case),
                      native_report_sha256=sha(output/'native/report.json'),results_sha256=sha(output/'results.json'))
        for key in ('actual_mesh_flux_m3_s','computed_pressure_drop_Pa','computed_loss_coefficient'):
            report[key]=results[key]
        write_json(output/'run_record.json',report)
        print('DIAGNOSTIC_PASS: fixed held-open Re10 only; manufacturing/contact/joint remain HOLD')
        return 0
    except Exception as exc:
        report.update(status='FAIL',error=str(exc))
        write_json(output/'run_record.json',report)
        # Never leave a stale success or engineering result after any failure.
        previous=json.loads((output/'results.json').read_text())
        if previous.get('status')=='DIAGNOSTIC_PASS':write_json(output/'superseded-results.json',previous)
        write_json(output/'results.json',report)
        print(str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':
    sys.exit(main())
