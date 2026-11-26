"""Decision before another attempt on a named engineering gate, not solver certification."""
import gzip
from pathlib import Path
import re
import zipfile

CASE = Path(__file__).resolve().parents[2]/'verification/valve-3d-cfd-57mm'
# Single history for the fixed-input automatic tetra mesh and in-place repairs.
# A different job name, relaxation, tolerance, or code version is not a different gate.
RECEIPTS = (
    ('v22/checkMesh.log.gz', None),
    ('ring-localization/native-candidate.zip','checkMesh.log'),
    ('opus-repair/native-record.zip','candidate.log'),
    ('opus-repair/native-strict-face-plane.zip','candidate.log'),
)


def decision(outcomes, *, paused):
    """Three successive engineering failures force a different method; two force reflection."""
    streak=0
    for value in outcomes:
        if type(value) is not bool: raise ValueError('Gate result must be supported by a completed check.')
        streak=0 if value else streak+1
    if paused: return 'paused'
    if streak>=3: return 'change_method'
    if streak==2: return 'review_before_retry'
    return 'no_retry_hold'  # Not authorization to run or proof of quality.


def archived_outcomes(root=CASE):
    outcomes=[]
    for path,member in RECEIPTS:
        if member:
            with zipfile.ZipFile(root/path) as z: data=z.read(member)
        else: data=gzip.decompress((root/path).read_bytes())
        log=data.decode(); passed='\nMesh OK.\n' in log; failed=bool(re.search(r'^Failed [1-9]\d* mesh checks?\.$',log,re.M))
        if not log.rstrip().endswith('End') or passed==failed: raise ValueError('Incomplete/ambiguous native result: '+path)
        outcomes.append(passed)
    return outcomes


OPERATOR_PAUSED = True  # Project decision, not an environment override or CLI option.


def require_fixed_study_run():
    if OPERATOR_PAUSED:
        raise RuntimeError('本阀研究已暂停：不重跑旧网格或启动求解。见 CURRENT_PLAN.md。')
    action=decision(archived_outcomes(), paused=False)
    if action!='no_retry_hold':
        raise RuntimeError(action+': 同一网格验收关口重复失败，见 CURRENT_PLAN.md 的复盘与换方法条件。')
