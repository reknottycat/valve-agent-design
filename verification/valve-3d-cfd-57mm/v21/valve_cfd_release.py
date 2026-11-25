#!/usr/bin/env python3
"""
3D CFD validation of AGR1 valve at 57mm opening.
Target: pressure drop at 100 m³/h should satisfy Кз≤6.
"""
import gzip
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Physical parameters (SI units)
RHO = 1024.9109328963  # kg/m³, seawater at 20 °C and 35 g/kg
NU = 1.0504609627009073e-6  # m²/s, same study state
Q_M3H = 100.0  # m³/h, volumetric flow rate
D = 0.2        # m, pipe diameter
A_INLET = math.pi * (D/2)**2  # m², inlet area

# Flow velocity from Q = U * A
U_INLET = (Q_M3H / 3600.0) / A_INLET  # m/s

# Quality gate tolerances
TOL = {
    'imbalance': 0.001,       # Mass balance: |inflow + outflow| / inflow < 0.1%
    'flux_error': 0.001,      # Flux consistency: |U*A - Q| / Q < 0.1%
    'dp_span': 0.005,         # Pressure drop stability: (max-min)/mean < 0.5%
    'target_kz': 6.0,         # Maximum resistance coefficient
}

# Target pressure drop: ΔP = Кз * (ρ * U² / 2)
TARGET_DP_PA = TOL['target_kz'] * (RHO * U_INLET**2 / 2)

print(f"=== Validation parameters ===")
print(f"Flow rate: {Q_M3H} m³/h = {Q_M3H/3600:.6f} m³/s")
print(f"Inlet velocity: {U_INLET:.6f} m/s")
print(f"Inlet area: {A_INLET:.6e} m²")
print(f"Reynolds number: {U_INLET * D / NU:.0f}")
print(f"Target ΔP (Кз={TOL['target_kz']}): {TARGET_DP_PA:.2f} Pa\n")


def run(cmd, cwd, log, of=False):
    """Execute command with OpenFOAM environment if needed."""
    if of:
        cmd = ['bash', '-c',
               'source /opt/openfoam11/etc/bashrc >/dev/null && exec "$@"',
               'foam', *cmd]
    with log.open('w') as f:
        rc = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        raise RuntimeError(
            f'{cmd[-1]} failed ({rc}): {log.read_text(errors="replace")[-2200:]}'
        )


def install_openfoam(work):
    """Install OpenFOAM 11 on Ubuntu (Jammy/Noble)."""
    if Path('/opt/openfoam11/etc/bashrc').is_file():
        return

    run(['bash', '-ec', '''set -o pipefail
. /etc/os-release
[ "$ID" = ubuntu ]
case "$VERSION_CODENAME" in jammy|noble) ;; *) exit 2;; esac
curl -fsSL --retry 2 https://dl.openfoam.org/gpg.key | gpg --dearmor > /tmp/valve3d-of11.gpg
printf 'deb [signed-by=/tmp/valve3d-of11.gpg] https://dl.openfoam.org/ubuntu %s main\n' "$VERSION_CODENAME" >/etc/apt/sources.list.d/valve3d-of11.list
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=2 update
pkg=$(apt-cache show --no-all-versions openfoam11)
path=$(printf '%s\\n' "$pkg" | grep '^Filename: ' | cut -d' ' -f2)
sha=$(printf '%s\\n' "$pkg" | grep '^SHA256: ' | cut -d' ' -f2)
[[ $sha =~ ^[a-f0-9]{64}$ && $path == dists/"$VERSION_CODENAME"/main/binary-amd64/openfoam11_*.deb ]]
curl --proto '=https' --proto-redir '=https' --retry 2 -fsSL "https://downloads.sourceforge.net/project/foam/foam/ubuntu/$path" -o /tmp/valve3d-openfoam11.deb
printf '%s  %s\\n' "$sha" /tmp/valve3d-openfoam11.deb | sha256sum -c -
apt-get -o Acquire::Retries=2 install -y --no-install-recommends /tmp/valve3d-openfoam11.deb
'''], work, work/'install.log')


def write_dict(path, class_name, object_name, content):
    """Write OpenFOAM dictionary file with header."""
    header = f'''FoamFile
{{
    version     2.0;
    format      ascii;
    class       {class_name};
    object      {object_name};
}}
'''
    Path(path).write_text(header + content)


def setup_solver_case(mesh_case, solver_case, metadata):
    """Set up simpleFoam solver case with the generated mesh."""
    mesh = Path(mesh_case)
    case = Path(solver_case)
    case.mkdir(exist_ok=True)

    # Copy mesh
    if (case / 'constant/polyMesh').exists():
        shutil.rmtree(case / 'constant/polyMesh')
    shutil.copytree(mesh / 'constant/polyMesh', case / 'constant/polyMesh')

    # Create system directory
    (case / 'system').mkdir(exist_ok=True)

    # physicalProperties (OpenFOAM 11 format)
    (case / 'constant').mkdir(exist_ok=True)
    write_dict(str(case / 'constant/physicalProperties'), 'dictionary', 'physicalProperties', f'''
viscosityModel  constant;
nu              [0 2 -1 0 0 0 0] {NU};
''')

    # momentumTransport
    write_dict(str(case / 'constant/momentumTransport'), 'dictionary', 'momentumTransport', '''
simulationType RAS;
RAS
{
    model kOmegaSST;
    turbulence on;
    printCoeffs on;
}
''')

    # Initial conditions
    (case / '0').mkdir(exist_ok=True)

    # Turbulent kinetic energy: k = 1.5 * (U * I)^2, I = 5% for developed flow
    I = 0.05
    k = 1.5 * (U_INLET * I)**2

    # Turbulent frequency: omega = k^0.5 / (0.09^0.25 * L), L = 0.07 * D
    L = 0.07 * D
    omega = k**0.5 / (0.09**0.25 * L)

    write_dict(str(case / '0/U'), 'volVectorField', 'U', f'''
dimensions      [0 1 -1 0 0 0 0];
internalField   uniform (0 0 0);
boundaryField
{{
    inlet
    {{
        type            flowRateInletVelocity;
        volumetricFlowRate constant {Q_M3H / 3600:.16g};
        value           uniform ({U_INLET:.8f} 0 0);
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    valve
    {{
        type            noSlip;
    }}
}}
''')

    write_dict(str(case / '0/p'), 'volScalarField', 'p', f'''
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform 0;
boundaryField
{{
    inlet
    {{
        type            zeroGradient;
    }}
    outlet
    {{
        type            fixedValue;
        value           uniform 0;
    }}
    valve
    {{
        type            zeroGradient;
    }}
}}
''')

    write_dict(str(case / '0/k'), 'volScalarField', 'k', f'''
dimensions      [0 2 -2 0 0 0 0];
internalField   uniform {k:.8e};
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {k:.8e};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    valve
    {{
        type            kqRWallFunction;
        value           uniform {k:.8e};
    }}
}}
''')

    write_dict(str(case / '0/omega'), 'volScalarField', 'omega', f'''
dimensions      [0 0 -1 0 0 0 0];
internalField   uniform {omega:.8e};
boundaryField
{{
    inlet
    {{
        type            fixedValue;
        value           uniform {omega:.8e};
    }}
    outlet
    {{
        type            zeroGradient;
    }}
    valve
    {{
        type            omegaWallFunction;
        value           uniform {omega:.8e};
    }}
}}
''')

    write_dict(str(case / '0/nut'), 'volScalarField', 'nut', '''
dimensions      [0 2 -1 0 0 0 0];
internalField   uniform 0;
boundaryField
{
    inlet
    {
        type            calculated;
        value           uniform 0;
    }
    outlet
    {
        type            calculated;
        value           uniform 0;
    }
    valve
    {
        type            nutkWallFunction;
        value           uniform 0;
    }
}
''')

    # fvSchemes
    write_dict(str(case / 'system/fvSchemes'), 'dictionary', 'fvSchemes', '''
ddtSchemes
{
    default         steadyState;
}

gradSchemes
{
    default         Gauss linear;
}

divSchemes
{
    default         none;
    div(phi,U)      bounded Gauss linearUpwind grad(U);
    div(phi,k)      bounded Gauss upwind;
    div(phi,omega)  bounded Gauss upwind;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}

laplacianSchemes
{
    default         Gauss linear corrected;
}

interpolationSchemes
{
    default         linear;
}

snGradSchemes
{
    default         corrected;
}

wallDist
{
    method meshWave;
}
''')

    # fvSolution
    write_dict(str(case / 'system/fvSolution'), 'dictionary', 'fvSolution', '''
solvers
{
    p
    {
        solver          GAMG;
        smoother        GaussSeidel;
        tolerance       1e-11;
        relTol          0.01;
    }

    pFinal
    {
        $p;
        relTol 0;
    }

    "(U|k|omega)(Final)?"
    {
        solver          smoothSolver;
        smoother        symGaussSeidel;
        tolerance       1e-12;
        relTol          0.01;
    }
}

SIMPLE
{
    nNonOrthogonalCorrectors 1;
    consistent          no;

    residualControl
    {
        p               1e-6;
        U               1e-6;
        "(k|omega)"     1e-6;
    }
}

relaxationFactors
{
    fields
    {
        p               0.15;
    }
    equations
    {
        U               0.3;
        k               0.35;
        omega           0.35;
    }
}
''')

    # controlDict with function objects for monitoring
    write_dict(str(case / 'system/controlDict'), 'dictionary', 'controlDict', f'''
application     foamRun;
solver          incompressibleFluid;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         7500;
deltaT          1;
writeControl    timeStep;
writeInterval   7500;
writePrecision  14;
writeCompression off;
timeFormat      general;
timePrecision   6;

functions
{{
    pInlet
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        log             yes;
        writeFields     no;
        select          patch;
        patch           inlet;
        operation       areaAverage;
        fields          (p);
    }}

    pOutlet
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        log             yes;
        writeFields     no;
        select          patch;
        patch           outlet;
        operation       areaAverage;
        fields          (p);
    }}

    qInlet
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        log             yes;
        writeFields     no;
        select          patch;
        patch           inlet;
        operation       sum;
        fields          (phi);
    }}

    qOutlet
    {{
        type            surfaceFieldValue;
        libs            ("libfieldFunctionObjects.so");
        writeControl    timeStep;
        writeInterval   1;
        log             yes;
        writeFields     no;
        select          patch;
        patch           outlet;
        operation       sum;
        fields          (phi);
    }}
}}
''')


def evaluate_results(case_dir, area_inlet):
    """Extract and evaluate final pressure drop results."""
    case = Path(case_dir)

    # Read postProcessing data
    series = []
    for name in ('pInlet', 'pOutlet', 'qInlet', 'qOutlet'):
        files = list((case / 'postProcessing' / name).glob('0/surfaceFieldValue.dat'))
        if not files:
            raise ValueError(f"No results found for {name}")

        data_file = files[0]
        rows = []
        for line in data_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                rows.append(list(map(float, line.split())))

        if len(rows) < 20:
            raise ValueError(f"{name}: insufficient data points (need 20, got {len(rows)})")

        series.append(rows[-20:])  # Last 20 iterations

    # Verify time consistency
    times = [r[0] for r in series[0]]
    if len(times) != 20:
        raise ValueError(f"Expected 20 samples, got {len(times)}")

    for s in series[1:]:
        if [r[0] for r in s] != times:
            raise ValueError("Time mismatch between function objects")

    # Check for finite values
    for s in series:
        for row in s:
            for val in row:
                if not math.isfinite(val):
                    raise ValueError("Non-finite values in results")

    # Calculate statistics over final 20 iterations
    dp_values = []
    imbalance_values = []
    flux_error_values = []

    for pi, po, qi, qo in zip(*series):
        # Pressure drop (kinematic pressure * density)
        dp_pa = RHO * (pi[1] - po[1])
        dp_values.append(dp_pa)

        # Mass balance: |inflow + outflow| / |inflow|
        imb = abs(qi[1] + qo[1]) / abs(qi[1]) if qi[1] != 0 else 1.0
        imbalance_values.append(imb)

        # Flux error: max(|inlet_flux - target|, |outlet_flux - target|) / target
        target_flux = U_INLET * area_inlet
        fe_in = abs(abs(qi[1]) / target_flux - 1.0) if target_flux != 0 else 1.0
        fe_out = abs(qo[1] / target_flux - 1.0) if target_flux != 0 else 1.0
        flux_error_values.append(max(fe_in, fe_out))

    # Statistical summary
    dp_mean = sum(dp_values) / len(dp_values)
    dp_min = min(dp_values)
    dp_max = max(dp_values)
    dp_span = (dp_max - dp_min) / dp_mean if dp_mean > 0 else None

    imbalance_max = max(imbalance_values)
    flux_error_max = max(flux_error_values)

    # Calculate resistance coefficient: Кз = ΔP / (ρ * U² / 2)
    kz = dp_mean / (RHO * U_INLET**2 / 2) if U_INLET > 0 else None

    result = {
        'dp_Pa': dp_mean,
        'dp_min_Pa': dp_min,
        'dp_max_Pa': dp_max,
        'dp_span': dp_span,
        'imbalance': imbalance_max,
        'flux_error': flux_error_max,
        'kz': kz,
        'window_iterations': [times[0], times[-1]],
    }

    # Quality gate checks
    result['residual_converged'] = ' solution converged in ' in (case / 'foamRun.log').read_text()
    result['pass'] = (
        result['residual_converged'] and
        dp_mean > 0 and
        dp_span is not None and dp_span <= TOL['dp_span'] and
        imbalance_max <= TOL['imbalance'] and
        flux_error_max <= TOL['flux_error']
    )

    result['meets_target'] = result['pass'] and kz is not None and kz <= TOL['target_kz']

    return result


def main():
    """Main execution pipeline."""
    work = Path(tempfile.mkdtemp(prefix='valve-cfd-'))
    output = Path(os.environ.get('OUTPUT_DIR', '/kaggle/working/valve-3d'))
    output.mkdir(parents=True, exist_ok=True)
    output_json = output / 'result.json'
    result = {
        'model': 'valve_3d_57mm_opening',
        'flow_rate_m3h': Q_M3H,
        'inlet_velocity_ms': U_INLET,
        'reynolds': U_INLET * D / NU,
        'limits': TOL,
        'target_dp_Pa': TARGET_DP_PA,
        'pressure_basis': 'area-mean static pressure between pipe end planes, including straight extensions',
        'seawater_study': {'temperature_C': 20, 'salinity_g_kg': 35, 'density_kg_m3': RHO, 'kinematic_viscosity_m2_s': NU},
    }

    try:
        # Install OpenFOAM
        print("=== Installing OpenFOAM 11 ===")
        install_openfoam(work)

        # Load geometry metadata
        assets = 'https://github.com/reknottycat/valve-agent-design/releases/download/valve-3d-v1'
        for name, digest in {
            'geometry_metadata.json': 'ed0bbb43dec32dd3a3846b183780c8bbf70b25c4b761eaf30ded18cbd02d125c',
            'open57-occ-v21-si.msh.gz': 'a7b4753b58dbbeb0344111430195da5e035c0bddf2e5d210bd1ad14953f99b75',
        }.items():
            path = work / name
            subprocess.run(['curl', '-fsSL', '--retry', '2', '-o', str(path), f'{assets}/{name}'], check=True)
            if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f'Checksum mismatch: {name}')
        metadata_file = work / 'geometry_metadata.json'
        if not metadata_file.exists():
            raise FileNotFoundError(f"Geometry metadata not found: {metadata_file}")

        metadata = json.loads(metadata_file.read_text())
        result['geometry'] = metadata

        mesh_case = work / 'mesh'
        (mesh_case/'system').mkdir(parents=True)
        (mesh_case/'constant').mkdir()
        write_dict(str(mesh_case/'system/controlDict'), 'dictionary', 'controlDict', 'application checkMesh; startFrom startTime; startTime 0; stopAt endTime; endTime 1; deltaT 1; writeControl timeStep; writeInterval 1; writeFormat ascii; writePrecision 14;')
        for name in ('fvSolution','fvSchemes'):
            write_dict(str(mesh_case/'system'/name), 'dictionary', name, '' if name=='fvSolution' else 'ddtSchemes {default steadyState;} gradSchemes {default Gauss linear;} divSchemes {default none;} laplacianSchemes {default Gauss linear corrected;} interpolationSchemes {default linear;} snGradSchemes {default corrected;}')
        msh = work/'volume.msh'
        with gzip.open(work/'open57-occ-v21-si.msh.gz','rb') as src, msh.open('wb') as dst: shutil.copyfileobj(src,dst)
        run(['gmshToFoam',str(msh)],mesh_case,mesh_case/'gmshToFoam.log',of=True)
        boundary = mesh_case/'constant/polyMesh/boundary'; b=boundary.read_text(); b,n=re.subn(r'(\bvalve\s*\{[^{}]*?\btype\s+)patch;',r'\1wall;',b); assert n==1, b; boundary.write_text(b); (output/'boundary.txt').write_text(b)
        run(['checkMesh','-allGeometry','-allTopology'],mesh_case,mesh_case/'checkMesh.log',of=True); mesh_log=(mesh_case/'checkMesh.log').read_text(); result['cells']=int(re.search(r'(?m)^\s*cells:\s*(\d+)',mesh_log)[1]);result['native_mesh_ok']='Mesh OK.' in mesh_log
        points=[(-.5,.00017,.00013),(1.1,.00017,.00013),(.320,.00017,.331),(.280,.00017,.331),(.3315,.00017,.160),(.2685,.00017,.160)]
        coords=' '.join('('+' '.join(map(str,p))+')' for p in points);write_dict(str(mesh_case/'system/topoSetDict'),'dictionary','topoSetDict','actions ( { name checkFluid; type cellSet; action new; source regionToCell; insidePoints ('+coords+'); } );');run(['topoSet'],mesh_case,mesh_case/'probeCells.log',of=True); hits=re.findall(r'Found location .*? in global region (\d+) out of (\d+) regions',(mesh_case/'probeCells.log').read_text());result['single_region_probes']=len(hits)==6 and all(i==('0','1') for i in hits)
        if not(result['native_mesh_ok'] and result['single_region_probes'] and result['cells']==498572): raise ValueError('Mesh not qualified for solving: '+mesh_log[-2200:])
        # Stage 2: Run solver
        print("\n=== Stage 2: CFD simulation ===")
        solver_case = work / 'solver'
        setup_solver_case(mesh_case, solver_case, metadata)

        # Run foamRun (OpenFOAM 11 replaces simpleFoam)
        print("Running foamRun -solver incompressibleFluid (steady RANS, k-omega SST)...")
        run(['foamRun', '-solver', 'incompressibleFluid'], solver_case, solver_case / 'foamRun.log', of=True)

        # Stage 3: Evaluate results
        print("\n=== Stage 3: Results evaluation ===")
        cfd_result = evaluate_results(solver_case, metadata['inlet_area_m2'])
        result.update(cfd_result)

        print(f"\nResults:")
        print(f"  Pressure drop: {result['dp_Pa']:.2f} Pa")
        print(f"  Resistance coefficient Кз: {result['kz']:.3f}")
        print(f"  Target: Кз ≤ {TOL['target_kz']} (ΔP ≤ {TARGET_DP_PA:.2f} Pa)")
        print(f"  Quality gates: {'PASS' if result['pass'] else 'FAIL'}")
        print(f"  Meets target: {'YES' if result['meets_target'] else 'NO'}")

        result['success'] = True

    except Exception as exc:
        result.update({
            'success': False,
            'pass': False,
            'error': str(exc)
        })
        print(f"\nERROR: {exc}")
        raise

    finally:
        output_json.write_text(json.dumps(result, indent=2, allow_nan=False))
        print("\n===RESULT_JSON_START===")
        print(json.dumps(result, indent=2, allow_nan=False))
        print("===RESULT_JSON_END===")
        print(f"\nResults written to: {output_json}")

        for log in work.rglob('*.log'):
            with log.open('rb') as src, gzip.open(output / (log.name + '.gz'), 'wb') as dst:
                shutil.copyfileobj(src, dst)
        traces = work / 'solver/postProcessing'
        if traces.is_dir():
            shutil.copytree(traces, output / 'postProcessing', dirs_exist_ok=True)


if __name__ == '__main__':
    main()
