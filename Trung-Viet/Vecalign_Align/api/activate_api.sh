#!/bin/sh
export VECALIGN=/workspace/ntha/Vecalign_Align/vecalign
export LASER=/workspace/ntha/Vecalign_Align/LASER
cd /workspace/ntha/Vecalign_Align/api
. /workspace/ntha/anaconda3/etc/profile.d/conda.sh
conda activate vecalign
python api_align.py
