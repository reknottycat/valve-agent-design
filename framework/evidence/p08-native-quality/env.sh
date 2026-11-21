B=/workspace/shared/valve-openfoam-quality-20261023
export WM_PROJECT_DIR=$B/root/usr/share/openfoam
export FOAM_ETC=$WM_PROJECT_DIR/etc
export LD_LIBRARY_PATH=$B/root/usr/lib/dummy:$B/root/usr/lib
export PATH=$B/root/usr/bin:$PATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
