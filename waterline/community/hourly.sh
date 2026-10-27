#!/bin/bash
# Waterline hourly: arXiv incremental → local db → D1 → Matrix rooms. Quiet unless something fails.
cd ~/architect/waterline/index || exit 1
python3 harvest.py since "$(date -u -v-2d +%Y-%m-%d)" >> hourly.log 2>&1
python3 sync_d1.py 500 >> hourly.log 2>&1
cd ~/architect/waterline/community && python3 waterline_bots.py both >> hourly.log 2>&1
