#!/bin/bash
python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1
python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1 --repair

python3 baseline.py --nogui -n 8 -c 0.5 -b 3 -m 6
python3 baseline.py --nogui -n 8 -c 0.5 -b 3 -m 6 --repair

python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1.5
python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1.5 --repair

python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1.5
python3 baseline.py --nogui -n 8 -c 0.5 -b 2 -m 1.5 --repair

python3 baseline.py --nogui -n 12 -c 0.5 -b 2 -m 1
python3 baseline.py --nogui -n 12 -c 0.5 -b 2 -m 1 --repair

python3 baseline.py --nogui -n 12 -c 0.5 -b 3 -m 1
python3 baseline.py --nogui -n 12 -c 0.5 -b 3 -m 1 --rapair
