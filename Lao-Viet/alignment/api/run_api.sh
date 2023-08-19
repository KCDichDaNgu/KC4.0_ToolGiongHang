#!/bin/sh
echo "Start activate align_api for Viet-Lao"
cd /workspace/ntha/Lao_Viet/alignment/api
kill -INT $(lsof -i:9988 -t)
screen -XS api_align_lo_vi quit
if [ -z "$STY" ]; then exec screen -dm -S api_align_lo_vi /bin/bash activate_api.sh; fi
