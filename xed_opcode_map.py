#!/usr/bin/env python3

import argparse
import sqlite3
from pathlib import Path
from typing import Any, List, Tuple, Dict, Optional

def gen_cell(map_id: int, row_id: int, col_id: int) -> str:
    opc_int = 16 * row_id + col_id
    opc_hex = f'{opc_int:02X}'
    return f'''
<td style="padding: 0px">
<div id="cell">
<style>
#cell td {{
  border: 0px none;
  text-align: left;
}}
</style>
<table style="width: 100%">
<tr>
<td style="width: 1%">
<b>{opc_hex}</b>
</td>
<td> </td>
</tr>
<tr>
<td> </td>
<td>
FOO
<br>
BAR
</td>
</tr>
</table>
</div>
</td>
'''

def gen_row(map_id: int, row_id: int) -> str:
    all_cols = '\n'.join([ gen_cell(map_id, row_id, col_id) for col_id in range(16) ])
    return f'''
<tr>
{all_cols}
</tr>
'''

def gen_map(map_id: int) -> str:
    all_rows = '\n'.join([ gen_row(map_id, row_id) for row_id in range(16) ])
    return f'''
<button class="collapsible">Map {map_id}</button>
<div class="content">
<br>
<table style="width:100%">
{all_rows}
</table>
<br>
</div>
'''

def gen_final() -> str:
    all_maps = '\n'.join([ gen_map(map_id) for map_id in range(8) ])
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
  text-align: center;
  outline: none;
  font-weight: bold;
  font-size: 24px;
}}

.active, .collapsible:hover {{
  background-color: #555;
}}

.collapsible:after {{
  content: '\\002B';
  color: white;
  font-weight: bold;
  float: right;
  margin-left: 5px;
}}

.active:after {{
  content: "\\2212";
}}

.content {{
  padding: 0 18px;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.2s ease-out;
}}

table, th, td {{
  border:1px solid black;
}}

</style>
</head>
<body>

<h1 style="text-align: center">
x86 opcode map
</h1>

<button class="collapsible">Legend</button>
<div class="content">
  <p>Legend here</p>
</div>

{all_maps}

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
        out_fp.write(gen_final())

def main() -> None:
    parser = argparse.ArgumentParser(description='Make HTML opcopde map from SQLite database extracted from a XED build')
    parser.add_argument('sqlite', type=str, help='input SQLite database')
    parser.add_argument('html', type=str, help='output HTML opcode map')
    args = parser.parse_args()
    output_opcode_map(args.html)

if __name__ == '__main__':
    main()
