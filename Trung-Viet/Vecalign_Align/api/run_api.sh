#!/bin/sh
echo "Start activate align_api for Viet-Trung"
cd /workspace/ntha/Vecalign_Align/api
kill -INT $(lsof -i:9977 -t)
screen -XS api_align_Viet-Trung quit
if [ -z "$STY" ]; then exec screen -dm -S api_align_Viet-Trung /bin/bash activate_api.sh; fi

