#!/usr/bin/env python3

import argparse
import sys
import re
import inspect
import csv
import json
import sqlite3
from pathlib import Path

# def input_xed_dgen(dgen: str):

default_root = Path(__file__).resolve().parent.parent
default_dgen = default_root / 'build/obj/dgen'
default_pysrc = default_root / 'xed/pysrc'
default_mbuild = default_root / 'mbuild'

def main() -> None:
    parser = argparse.ArgumentParser(description='Extract a database from a XED build')
    parser.add_argument('--dgen', default=str(default_dgen), help=f'the dgen directory of a XED build (default: {default_dgen})')
    parser.add_argument('--pysrc', default=str(default_pysrc), help=f'pathname of xed/pysrc (default: {default_pysrc})')
    parser.add_argument('--mbuild', default=str(default_mbuild), help=f'pathname of mbuild (default: {default_mbuild})')
    parser.add_argument('-c', '--csv', type=str, help='output CSV file')
    parser.add_argument('-j', '--json', type=str, help='output JSON file')
    parser.add_argument('-s', '--sqlite', type=str, help='output SQLite database')
    args = parser.parse_args()
    args.__dict__['prefix'] = args.__dict__.pop('dgen')
    if args.csv:
        assert Path(args.csv).suffix == '.csv'
    if args.json:
        assert Path(args.json).suffix == '.json'
    if args.sqlite:
        assert Path(args.sqlite).suffix == '.db'
    
    print(args)

if __name__ == '__main__':
    main()
