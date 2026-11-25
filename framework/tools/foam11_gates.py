"""Evidence gates for generated single-region Foundation 11 steady incompressible cases.
Not a general OpenFOAM dictionary parser or product acceptance certificate.
"""
import math
import re
from valve_readiness import audit


def liquid(state):
    rho, nu, mu = (float(state[k]) for k in ('density_kg_m3', 'kinematic_viscosity_m2_s', 'dynamic_viscosity_Pa_s'))
    if not all(math.isfinite(v) and v > 0 for v in (rho, nu, mu)) or not math.isclose(rho*nu, mu, rel_tol=1e-6):
        raise ValueError('物性来源不一致：用同一工况的密度及动力/运动黏度核对 μ = ρν。')
    return rho, nu


def mesh_checks(log, probes, *, bbox_m, tolerance_m, points, cells):
    triplet = r'\(([^()]+)\)'
    def vector(text):
        return tuple(map(float, text.split()))
    box = re.search(r'Overall domain bounding box '+triplet+r'\s+'+triplet, log)
    actual = tuple(x for g in box.groups() for x in vector(g)) if box else ()
    found = [(vector(pos), region, count) for pos,region,count in re.findall('Found location '+triplet+r' in cell \d+ .*? in global region (\d+) out of (\d+) regions', probes)]
    n = re.search(r'^\s*cells:\s*(\d+)\s*$', log, re.M)
    return {
        'foundation11_full_check': bool(re.search(r'Build\s*:\s*11-', log) and re.search(r'^Exec\s*:\s*checkMesh -allGeometry -allTopology\s*$', log,re.M)),
        'native_quality': bool(re.search(r'^Mesh OK\.\s*$', log,re.M) and not re.search(r'Failed \d+ mesh checks?',log) and log.rstrip().endswith('End')),
        'extent_in_metres': len(actual)==len(bbox_m)==6 and all(abs(x-y)<=tolerance_m for x,y in zip(actual,bbox_m)),
        'cell_count': n is not None and int(n[1])==cells and cells>0,
        'connected_fluid_points': bool(points) and len(set(map(tuple,points)))==len(points) and len(found)==len(points) and all(p==tuple(q) and reg=='0' and count=='1' for (p,reg,count),q in zip(found,points)) and probes.rstrip().endswith('End'),
    }


def require_case(case, mesh, expected_patches, nu):
    required = ('foundation11_full_check','native_quality','extent_in_metres','cell_count','connected_fluid_points')
    errors = [k for k in required if mesh.get(k) is not True]
    def text(rel):
        f=case/rel
        return re.sub(r'/\*.*?\*/|//[^\n]*','', f.read_text(),flags=re.S) if f.is_file() else ''
    b=text('constant/polyMesh/boundary'); actual={n:t for n,t,c in re.findall(r'(\w+)\s*\{\s*type\s+(\w+);[^{}]*?nFaces\s+(\d+);',b) if int(c)>0}
    patches_ok=actual==expected_patches
    for field in ('U','p','k','omega','nut'):
        body=text('0/'+field).partition('boundaryField')[2]
        names=re.findall(r'(\w+)\s*\{[^{}]*\}',body)
        if sorted(names)!=sorted(expected_patches): errors.append('边界名称不一致：0/'+field);patches_ok=False
    if actual!=expected_patches: errors.append('原生网格边界名称、类型或面数有误')
    material=text('constant/physicalProperties'); m=re.search(r'\bnu\s+\[0 2 -1 0 0 0 0\]\s+([^;]+);',material)
    momentum=text('constant/momentumTransport')
    if not (m and math.isclose(float(m[1]),nu,rel_tol=1e-8) and re.search(r'\bviscosityModel\s+constant;',material) and re.search(r'\bclass\s+dictionary;',momentum) and re.search(r'\bmodel\s+kOmegaSST;',momentum)):
        errors.append('请按 Foundation 11 生成 physicalProperties 和 momentumTransport 并核对研究物性')
    readiness=audit({'requested_action':'solve','domain_scope':'whole_valve','mesh_stage':'retained_fluid_mesh','mesh_quality_pass':all(mesh.values()) and bool(mesh),'boundary_conditions_verified':patches_ok},case)
    errors.extend(readiness['errors'])
    if errors: raise ValueError('禁止启动求解：'+'；'.join(errors))


def assess(result, limits):
    fields=('dp_Pa','kz','dp_span','imbalance','flux_error')
    if any(not isinstance(result.get(k),(int,float)) or isinstance(result.get(k),bool) or not math.isfinite(result[k]) for k in fields):
        return 'no_valid_result'
    if result.get('residual_converged') is not True or result['dp_Pa']<=0 or result['kz']<=0 or any(not 0<=result[k]<=limits[k] for k in ('dp_span','imbalance','flux_error')):
        return 'quality_not_passed'
    return 'within_study_limit' if result['kz']<=limits['target_kz'] else 'above_study_limit'
