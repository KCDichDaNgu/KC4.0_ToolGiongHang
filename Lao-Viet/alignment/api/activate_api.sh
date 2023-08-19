#!/bin/sh
export VECALIGN_LO_VI=/workspace/ntha/Lao_Viet/alignment/vecalign
export LASER=/workspace/ntha/Vecalign_Align/LASER
cd /workspace/ntha/Lao_Viet/alignment/api
. /workspace/ntha/anaconda3/etc/profile.d/conda.sh
conda activate vecalign
python api_align_lo_vi.py
