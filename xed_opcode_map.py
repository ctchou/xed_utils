#!/usr/bin/env python3

import argparse
import sqlite3
from pathlib import Path
from typing import Any, List, Tuple, Dict, Optional

def one_map(map_id: int) -> str:
    assert 0 <= map_id <= 7
    return f'''
<button class="collapsible">Map {map_id}</button>
<div class="content">
  <p>Map {map_id} here</p>
</div>
'''

def all_maps() -> str:
    return f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
.collapsible {{
  background-color: #777;
  color: white;
  cursor: pointer;
  padding: 18px;
  width: 100%;
  border: none;
  text-align: left;
  outline: none;
  font-size: 15px;
}}

.active, .collapsible:hover {{
  background-color: #555;
}}

.collapsible:after {{
  content: '\002B';
  color: white;
  font-weight: bold;
  float: right;
  margin-left: 5px;
}}

.active:after {{
  content: "\2212";
}}

.content {{
  padding: 0 18px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
  background-color: #f1f1f1;
}}
</style>
</head>
<body>

<h2>x86 opcode map</h2>

<button class="collapsible">Legend</button>
<div class="content">
  <p>Legend here</p>
</div>

{one_map(0)}
{one_map(1)}
{one_map(2)}
{one_map(3)}
{one_map(4)}
{one_map(5)}
{one_map(6)}
{one_map(7)}

<script>
var coll = document.getElementsByClassName("collapsible");
var i;

for (i = 0; i < coll.length; i++) {{
  coll[i].addEventListener("click", function() {{
    this.classList.toggle("active");
    var content = this.nextElementSibling;
    if (content.style.maxHeight){{
      content.style.maxHeight = null;
    }} else {{
      content.style.maxHeight = content.scrollHeight + "px";
    }} 
  }});
}}
</script>

</body>
</html>
'''

def output_opcode_map(out_file: str) -> str:
    with open(out_file, 'w') as out_fp:
        out_fp.write(all_maps())

def main() -> None:
    parser = argparse.ArgumentParser(description='Make HTML opcopde map from SQLite database extracted from a XED build')
    parser.add_argument('sqlite', type=str, help='input SQLite database')
    parser.add_argument('html', type=str, help='output HTML opcode map')
    args = parser.parse_args()
    output_opcode_map(args.html)

if __name__ == '__main__':
    main()
