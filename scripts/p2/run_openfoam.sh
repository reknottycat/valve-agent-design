#!/bin/bash
# ---------------------------------------------------------------------------
# P2 / A-04 cloud CFD: convert the gmsh mesh, check it, solve it and extract
# the results. Runs OpenFOAM v11 either from the apt installation on the
# runner or, if that is not available, from the openfoam/openfoam11-paraview510
# docker image.
#
# usage: run_openfoam.sh <case_name> <msh_file> <mode> <velocity> [end_time]
#   mode: laminar | ras
# ---------------------------------------------------------------------------
set -uo pipefail

CASE_NAME=$1
MSH=$2
MODE=$3
VELOCITY=$4
END_TIME=${5:-2000}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)

RHO=${RHO:-1024}
NU=${NU:-1.025e-6}
WRITE_INTERVAL=${WRITE_INTERVAL:-50}
OF_BASHRC=/usr/lib/openfoam/openfoam11/etc/bashrc
FOAM_IMAGE=${FOAM_IMAGE:-openfoam/openfoam11-paraview510}

WORK="$ROOT/work/$CASE_NAME"
CASE="$WORK/case"

echo "=== [$CASE_NAME] work dir: $WORK"
rm -rf "$WORK"
mkdir -p "$WORK"
cp -r "$HERE/case" "$CASE"
cp "$MSH" "$CASE/fluid_flow.msh"

if [ -f "$OF_BASHRC" ]; then
    USE_DOCKER=0
    echo "=== [$CASE_NAME] using local OpenFOAM ($OF_BASHRC)"
else
    USE_DOCKER=1
    echo "=== [$CASE_NAME] local OpenFOAM not found -> docker fallback ($FOAM_IMAGE)"
fi

# Run a command inside the OpenFOAM environment.
foam() {
    if [ "$USE_DOCKER" = "0" ]; then
        bash -c ". $OF_BASHRC >/dev/null 2>&1; $1"
    else
        docker run --rm --entrypoint /bin/bash \
            -v "$WORK:/work" -w /work/case "$FOAM_IMAGE" \
            -c "if [ -f $OF_BASHRC ]; then . $OF_BASHRC >/dev/null 2>&1; fi; $1"
    fi
}

cd "$CASE" || exit 1

echo "=== [$CASE_NAME] gmshToFoam"
foam "gmshToFoam fluid_flow.msh" > log.gmshToFoam 2>&1
echo "    exit=$? ; patches:"
grep -E "^Patch .* gets name" log.gmshToFoam | sed 's/^/      /'

if [ ! -f constant/polyMesh/boundary ]; then
    echo "=== [$CASE_NAME] FATAL: gmshToFoam produced no mesh"
    tail -40 log.gmshToFoam
    exit 3
fi

echo "=== [$CASE_NAME] checkMesh"
foam "checkMesh" > log.checkMesh 2>&1
grep -E "cells:|points:|faces:|Mesh OK|Failed|Max skewness|Max aspect ratio|Maximum non-orthogonality" log.checkMesh | sed 's/^/      /'

echo "=== [$CASE_NAME] write case files"
python3 "$HERE/prepare_case.py" "$CASE" \
    --mode "$MODE" --velocity "$VELOCITY" --rho "$RHO" --nu "$NU" \
    --end-time "$END_TIME" --write-interval "$WRITE_INTERVAL" \
    > log.prepareCase 2>&1
if [ $? -ne 0 ]; then
    echo "=== [$CASE_NAME] FATAL: prepare_case.py failed"
    cat log.prepareCase
    exit 4
fi
sed 's/^/      /' log.prepareCase

echo "=== [$CASE_NAME] simpleFoam"
foam "simpleFoam" > log.simpleFoam 2>&1
SOLVER_RC=$?
echo "    exit=$SOLVER_RC"
tail -5 log.simpleFoam | sed 's/^/      /'

echo "=== [$CASE_NAME] foamPostProcess (final values)"
foam "foamPostProcess -funcs '(pInlet pOutlet qInlet qOutlet)' -time latest" \
    > log.postProcess 2>&1
echo "    exit=$?"

echo "=== [$CASE_NAME] extract results"
mkdir -p "$ROOT/results"
python3 "$HERE/extract_results.py" "$CASE" \
    --out "$ROOT/results/${CASE_NAME}.json" \
    --label "$CASE_NAME" --mode "$MODE" --velocity "$VELOCITY" \
    --rho "$RHO" --nu "$NU" > "$ROOT/results/${CASE_NAME}_extract.log" 2>&1
EXTRACT_RC=$?
tail -40 "$ROOT/results/${CASE_NAME}_extract.log" | sed 's/^/      /'

# copy the logs into results/ for the artifact
mkdir -p "$ROOT/results/${CASE_NAME}_logs"
cp -f "$CASE"/log.* "$ROOT/results/${CASE_NAME}_logs/" 2>/dev/null
cp -f "$CASE"/fluid_flow.msh_info.json "$ROOT/results/${CASE_NAME}_logs/" 2>/dev/null

exit $SOLVER_RC
