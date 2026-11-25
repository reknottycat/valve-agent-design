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


def setup_mesh_case(case_dir, stl_path, metadata):
    """Set up snappyHexMesh case to generate volume mesh from STL."""
    case = Path(case_dir)
    case.mkdir(exist_ok=True)

    # Create directory structure
    for d in ['0', 'constant/triSurface', 'system']:
        (case / d).mkdir(parents=True, exist_ok=True)

    # Copy STL to triSurface directory (convert mm → m)
    stl_dest = case / 'constant/triSurface/valve.stl'
    print(f"Converting STL from mm to m and writing to {stl_dest}")
    with open(stl_path, 'r') as fin, open(stl_dest, 'w') as fout:
        for line in fin:
            stripped = line.strip()
            if stripped.startswith('vertex'):
                parts = stripped.split()
                x, y, z = float(parts[1]) / 1000.0, float(parts[2]) / 1000.0, float(parts[3]) / 1000.0
                fout.write(f'    vertex {x:.10f} {y:.10f} {z:.10f}\n')
            else:
                fout.write(line)
    print(f"STL converted")

    # Generate background mesh with blockMesh
    # Domain covers STL range (mm→m): X=[-0.65,1.25], Y=[-0.15,0.15], Z=[-0.165,0.345]
    # STL actual range: X[-0.6,1.2], Y[-0.145,0.145], Z[-0.145,0.332]
    write_dict(str(case / 'system/blockMeshDict'), 'dictionary', 'blockMeshDict', '''
vertices
(
    (-0.65 -0.165 -0.165)
    ( 1.25 -0.165 -0.165)
    ( 1.25  0.165 -0.165)
    (-0.65  0.165 -0.165)
    (-0.65 -0.165  0.345)
    ( 1.25 -0.165  0.345)
    ( 1.25  0.165  0.345)
    (-0.65  0.165  0.345)
);

blocks
(
    hex (0 1 2 3 4 5 6 7) (212 104 92) simpleGrading
    (
        ((0.909 73 0.08) (0.082 66 1) (0.909 73 12.5))
        ((0.124 19 0.1) (0.082 66 1) (0.124 19 10))
        ((0.255 28 0.18) (0.255 64 1))
    )
);

edges ();
boundary ();
defaultPatch { type patch; }
mergePatchPairs ();
''')

    # snappyHexMeshDict configuration
    # STL valve_split.stl has 3 named solids: inlet, outlet, walls
    write_dict(str(case / 'system/snappyHexMeshDict'), 'dictionary', 'snappyHexMeshDict', f'''
castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    valve.stl
    {{
        type triSurfaceMesh;
        name valve;
        regions
        {{
            inlet  {{ name inlet;  }}
            outlet {{ name outlet; }}
            walls  {{ name valve;  }}
        }}
    }}
}}

castellatedMeshControls
{{
    maxLocalCells 5000000;
    maxGlobalCells 4500000;
    minRefinementCells 10;
    maxLoadUnbalance 0.10;
    nCellsBetweenLevels 3;

    features
    (
    );

    refinementSurfaces
    {{
        valve
        {{
            level (1 2);
            regions
            {{
                inlet  {{ level (2 2); patchInfo {{ type patch; }} }}
                outlet {{ level (2 2); patchInfo {{ type patch; }} }}
                walls  {{ level (1 2); patchInfo {{ type wall; inGroups (wall); }} }}
            }}
        }}
    }}

    resolveFeatureAngle 30;

    refinementRegions
    {{
    }}

    locationInMesh (-0.5 0.0 0.0);  // 入口管道中心，肯定在流体域内
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3;
    tolerance 2.0;
    nSolveIter 100;
    nRelaxIter 5;
    nFeatureSnapIter 10;
    implicitFeatureSnap false;
    explicitFeatureSnap true;
    multiRegionFeatureSnap false;
}}

addLayersControls
{{
    relativeSizes true;
    layers {{}}
    expansionRatio 1.0;
    finalLayerThickness 0.3;
    minThickness 0.1;
    nGrow 0;
    featureAngle 30;
    nRelaxIter 3;
    nSmoothSurfaceNormals 1;
    nSmoothNormals 3;
    nSmoothThickness 10;
    maxFaceThicknessRatio 0.5;
    maxThicknessToMedialRatio 0.3;
    minMedianAxisAngle 90;
    nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    maxNonOrtho 70;
    maxBoundarySkewness 20;
    maxInternalSkewness 4;
    maxConcave 80;
    minFlatness 0.5;
    minVol 1e-18;
    minTetQuality -1;
    minArea -1;
    minTwist 0.02;
    minDeterminant 0.001;
    minFaceWeight 0.02;
    minVolRatio 0.01;
    minTriangleTwist -1;

    nSmoothScale 4;
    errorReduction 0.75;
}}

writeFlags (scalarLevels layerSets layerFields);
mergeTolerance 1e-6;
''')

    # Dummy initial fields (not used for meshing)
    write_dict(str(case / '0/U'), 'volVectorField', 'U',
               'dimensions [0 1 -1 0 0 0 0]; internalField uniform (0 0 0); boundaryField {}')
    write_dict(str(case / '0/p'), 'volScalarField', 'p',
               'dimensions [0 2 -2 0 0 0 0]; internalField uniform 0; boundaryField {}')

    # controlDict for meshing
    write_dict(str(case / 'system/controlDict'), 'dictionary', 'controlDict', '''
application     snappyHexMesh;
startFrom       startTime;
startTime       0;
stopAt          endTime;
endTime         1;
deltaT          1;
writeControl    timeStep;
writeInterval   1;
writePrecision  14;
''')


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
        'model': 'valve_3d_57mm_mesh_only',
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
            'valve_endplanes.stl.gz': '8c99ffe22a67b05d0f386548eae574400e4a99f2539529646bca41089c471a8b',
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

        # Stage 1: Generate mesh
        print("\n=== Stage 1: Mesh generation ===")
        mesh_case = work / 'mesh'
        stl_file = work / 'valve_endplanes.stl.gz'

        # Decompress STL
        stl_uncompressed = work / 'valve_split.stl'
        print(f"Decompressing {stl_file.name}...")
        with gzip.open(stl_file, 'rb') as f_in:
            stl_uncompressed.write_bytes(f_in.read())

        setup_mesh_case(mesh_case, stl_uncompressed, metadata)

        # Run blockMesh
        print("Running blockMesh...")
        run(['blockMesh'], mesh_case, mesh_case / 'blockMesh.log', of=True)

        # Run snappyHexMesh
        print("Running snappyHexMesh (this may take 10-20 minutes)...")
        run(['snappyHexMesh', '-overwrite'], mesh_case, mesh_case / 'snappyHexMesh.log', of=True)

        # Check mesh quality
        print("Running checkMesh...")
        run(['checkMesh'], mesh_case, mesh_case / 'checkMesh.log', of=True)

        mesh_log = (mesh_case / 'checkMesh.log').read_text()
        if 'Mesh OK.' not in mesh_log:
            raise ValueError(f"Mesh quality check failed:\n{mesh_log[-1800:]}")

        # Extract cell count
        cell_match = re.search(r'(?m)^\s*cells:\s*(\d+)', mesh_log)
        if cell_match:
            result['cells'] = int(cell_match.group(1))
            print(f"Mesh generated: {result['cells']} cells")

        # These six points were checked inside the exact STEP volume in mm using OCC.
        points = [(-.5,.00017,.00013),(1.1,.00017,.00013),(.320,.00017,.331),(.280,.00017,.331),(.3315,.00017,.160),(.2685,.00017,.160)]
        result['study'] = 'Mesh-only diagnostic; no pressure or acceptance result'
        result['cad_fluid_probes_m'] = points
        matches = re.findall(r'Overall domain bounding box[^\n]+', mesh_log)
        result['mesh_bbox'] = matches[-1] if matches else None
        if not re.search(r'Number of regions:\s*1\s*\(OK\)', mesh_log):
            raise ValueError('Expected one connected cell region')
        coords = ' '.join('('+' '.join(map(str,p))+')' for p in points)
        write_dict(str(mesh_case/'system/topoSetDict'), 'dictionary', 'topoSetDict', 'actions ( { name checkedFluid; type cellSet; action new; source regionToCell; insidePoints ('+coords+'); } );')
        run(['topoSet'],mesh_case,mesh_case/'probeCells.log',of=True)
        locs = re.findall(r'Found location .*? in global region (\d+) out of (\d+) regions', (mesh_case/'probeCells.log').read_text())
        if len(locs)!=len(points) or any(x!=('0','1') for x in locs):
            raise ValueError('No proof that every CAD probe lies in the port-connected mesh')
        import tarfile
        with tarfile.open(output/'retained-polyMesh.tar.gz','w:gz', compresslevel=2) as archive:
            archive.add(mesh_case/'constant/polyMesh',arcname='polyMesh')
        result['mesh_probe_check_passed'] = True
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
