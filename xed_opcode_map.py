#!/usr/bin/env python3

import sys
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser

python_version = sys.version_info
if not (python_version.major == 3 and python_version.minor >= 10):
    print('ERROR: this script needs Python 3.10 or above')
    sys.exit()

max_num_maps = 11

Iclass = str
InstDef = sqlite3.Row
IclassDefs = list[InstDef]
OpcodeMapCell = dict[Iclass, IclassDefs]
OneOpcodeMap = list[OpcodeMapCell]
AllOpcodeMaps = list[OneOpcodeMap]
SdmUrls = dict[Iclass, str]

def html_final(maps_html: str, modals_click_js: str, modals_exit_js) -> str:
    return f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, Initial-scale=1">
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

table, tr, td {{
  border:1px solid black;
  text-align: left;
  vertical-align: text-top;
}}

/* The Modal (background) */
.modal {{
  display: none; /* Hidden by default */
  position: fixed; /* Stay in place */
  z-index: 1; /* Sit on top */
  padding-top: 100px; /* Location of the box */
  left: 0;
  top: 0;
  width: 100%; /* Full width */
  height: 100%; /* Full height */
  overflow: auto; /* Enable scroll if needed */
  background-color: rgb(0,0,0); /* Fallback color */
  background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
}}

/* Modal Content */
.modal-content {{
  background-color: #fefefe;
  margin: auto;
  padding: 20px;
  border: 1px solid #888;
  width: 80%;
}}

/* The Close Button */
.close {{
  color: #aaaaaa;
  float: right;
  font-size: 28px;
  font-weight: bold;
}}

.close:hover,
.close:focus {{
  color: #000;
  text-decoration: none;
  cursor: pointer;
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

{maps_html}

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

{modals_click_js}

window.onclick = function(event) {{
  switch (event.target) {{
    {modals_exit_js}
  }}
}}

</script>
</body>
</html>
'''

def html_modal_button(modal_id: str, iclass: str, url: str | None) -> str:
    button = f'<div style="display: inline" id="modal_button_{modal_id}">&emsp;{iclass}</div>'
    sdm_link = f' <sup><a href="{url}" target="_blank">*</a></sup>' if url else ''
    return button + sdm_link

def html_modal_popup(modal_id: str, inst_strs: list[str]) -> str:
    all_inst_strs = '\n    '.join(inst_strs)
    return f'''
<div id="modal_popup_{modal_id}" class="modal">
  <div class="modal-content">
    <span id="modal_close_{modal_id}" class="close">&times;</span>
    {all_inst_strs}
  </div>
</div>
'''

def js_modal_click(modal_id: str) -> str:
    return f'''
var modal_button_{modal_id} = document.getElementById("modal_button_{modal_id}");
var modal_popup_{modal_id} = document.getElementById("modal_popup_{modal_id}");
var modal_close_{modal_id} = document.getElementById("modal_close_{modal_id}");

modal_button_{modal_id}.onclick = function() {{
  modal_popup_{modal_id}.style.display = "block";
}}
modal_close_{modal_id}.onclick = function() {{
  modal_popup_{modal_id}.style.display = "none";
}}
window.addEventListener('keydown', function (event) {{
  if (event.key === 'Escape') {{
    modal_popup_{modal_id}.style.display = 'none'
  }}
}})
'''

def js_modal_exit(modal_id: str) -> str:
    return f'''
    case modal_popup_{modal_id}:
      modal_popup_{modal_id}.style.display = "none";
      break;
'''

def make_modal_id(map_id: int, opcode: int, iclass: str):
    return f'map_{map_id:02d}_opc_{opcode:02X}_{iclass}'

def make_prefix_str(inst: InstDef) -> str:
    space = inst['space'].upper()
    map = int(inst['map'])
    pp = inst['pp']
    if space == 'LEGACY':
        pfx = f'{pp}: ' if pp != '' else ''
        return pfx
    else:
        return f'{space}-MAP{map}-{pp}: '

def make_opcode_str(inst: InstDef) -> str:
    iclass = inst['iclass']
    space = inst['space'].upper()
    map = int(inst['map'])
    opcode_esc = ''
    if space == 'LEGACY':
        if map == 1:
            opcode_esc = '0F '
        elif map == 2:
            opcode_esc = '0F 38 '
        elif map == 3:
            opcode_esc = '0F 3A '
    opcode_hex = inst['opcode_hex']
    pattern = inst['pattern']
    partial_opcode = inst['partial_opcode']
    reg_required = inst['reg_required']
    opcode_ext = ''
    if 'MOD[' in pattern:
        if reg_required == 'unspecified':
            opcode_ext = ' /r'
        else:
            assert int(reg_required) in range(8)
            opcode_ext = f' /{reg_required}'
    else:
        if partial_opcode == 1 and iclass not in ['NOP', 'PAUSE']:
            opcode_ext = '+r'
    return f'{opcode_esc}{opcode_hex}{opcode_ext}'

def make_disasm_str(inst: InstDef):
    mnemonic = inst['disasm_intel']
    if mnemonic is None:
        mnemonic = inst['disasm']
    if mnemonic is None:
        mnemonic = inst['iclass']
    mnemonic = mnemonic.lower()
    explicit_opnds = inst['explicit_operands'].lower().replace(' ', ', ')
    implicit_opnds = inst['implicit_operands'].lower().replace(' ', ', ')
    items = [mnemonic]
    if explicit_opnds != 'none':
        items.append(explicit_opnds)
    if implicit_opnds != 'none':
        items.append('&lt;' + implicit_opnds + '&gt;')
    return ' '.join(items)

def make_inst_div(inst: InstDef) -> str:
    prefix_str = make_prefix_str(inst)
    opcode_str = make_opcode_str(inst)
    disasm_str = make_disasm_str(inst)

    iform = inst['iform']
    return f'<div>{prefix_str}{opcode_str} {disasm_str} {iform}</div>'

def html_cell(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int, opcode: int) -> str:
    opcode_hex = f'{opcode:02X}'
    iclasses = sorted(all_maps[map_id][opcode].keys())
    cell_info = []
    for iclass in iclasses:
        modal_id = make_modal_id(map_id, opcode, iclass)
        url = sdm_urls.get(iclass, None)
        modal_button = html_modal_button(modal_id, iclass, url)
        inst_defs = all_maps[map_id][opcode][iclass]
        inst_divs = [ make_inst_div(inst) for inst in inst_defs ]
        modal_popup = html_modal_popup(modal_id, inst_divs)
        cell_info.append('\n'.join([modal_button, modal_popup]))
    cell_info_html = '<br>\n'.join(cell_info)
    return f'''
<td>
<b style="font-size: 120%">{opcode_hex}</b><br>
{cell_info_html}
</td>
'''

def html_row(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int, row_id: int) -> str:
    all_cols_html = '\n'.join([ html_cell(sdm_urls, all_maps, map_id, 16 * row_id + col_id) for col_id in range(16) ])
    return f'''
<tr>
{all_cols_html}
</tr>
'''

def html_one_map(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int) -> str:
    all_rows_html = '\n'.join([ html_row(sdm_urls, all_maps, map_id, row_id) for row_id in range(16) ])
    return f'''
<button class="collapsible">Map {map_id}</button>
<div class="content">
<br>
<table style="width:100%">
{all_rows_html}
</table>
<br>
</div>
'''

def collect_maps_info(all_maps: AllOpcodeMaps) -> tuple[list[bool], list[str]]:
    empty_maps = [ True for map_id in range(max_num_maps) ]
    modal_ids = []
    for map_id in range(max_num_maps):
        for opcode in range(256):
            for iclass in all_maps[map_id][opcode]:
                iclass_size = len(all_maps[map_id][opcode][iclass])
                assert iclass_size > 0
                empty_maps[map_id] = False
                modal_ids.append(make_modal_id(map_id, opcode, iclass))
    return (empty_maps, modal_ids)

def html_all_maps(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps) -> str:
    empty_maps, modal_ids = collect_maps_info(all_maps)
    maps_html = '\n'.join([ html_one_map(sdm_urls, all_maps, map_id)
                            for map_id in range(max_num_maps) if not empty_maps[map_id] ])
    modals_click_js = '\n'.join([ js_modal_click(modal_id) for modal_id in modal_ids ])
    modals_exit_js = '\n'.join([ js_modal_exit(modal_id) for modal_id in modal_ids ])
    return html_final(maps_html, modals_click_js, modals_exit_js)

def collect_all_maps(db: sqlite3.Cursor) -> AllOpcodeMaps:
    all_maps = [ [ dict([]) for opcode in range(256) ] for map_id in range(max_num_maps) ]
    for inst in db:
        map_id = inst['map']
        opcode = inst['opcode_int']
        iclass = inst['iclass']
        if inst['partial_opcode'] and iclass not in ['NOP', 'PAUSE']:
            for i in range(8):
                iclass_defs = all_maps[map_id][opcode + i].get(iclass, [])
                iclass_defs.append(inst)
                all_maps[map_id][opcode + i][iclass] = iclass_defs
        else:
            iclass_defs = all_maps[map_id][opcode].get(iclass, [])
            iclass_defs.append(inst)
            all_maps[map_id][opcode][iclass] = iclass_defs
    return all_maps

def input_sdm_urls(sdm_urls_json) -> SdmUrls:
    with open(sdm_urls_json, 'r') as sdm_urls_json_fp:
        return json.load(sdm_urls_json_fp)

def input_sqlite_db(db_file: str) -> sqlite3.Cursor:
    with sqlite3.connect(db_file) as db:
        db.row_factory = InstDef
        sql_query = 'SELECT DISTINCT * from Instructions order by map, opcode_int, iclass;'
        insts = db.execute(sql_query)
        return insts

def output_all_maps(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, out_file: str) -> None:
    with open(out_file, 'w') as out_fp:
        out_fp.write(html_all_maps(sdm_urls, all_maps))

this_dir = Path(__file__).resolve().parent
default_sdm_urls_json = str(this_dir / 'sdm_urls.json')

def main() -> None:
    parser = ArgumentParser(description='Make HTML opcopde map from SQLite database extracted from a XED build')
    parser.add_argument('xed_sqlite', type=str, help='input SQLite database extracted from a XED build')
    parser.add_argument('opcmap_html', type=str, help='output HTML opcode map')
    parser.add_argument('--sdm-urls-json', default=default_sdm_urls_json,
                        help=f'input JSON file containing SDM instruction reference URLs (default: {default_sdm_urls_json})')
    args = parser.parse_args()
    sdm_urls = input_sdm_urls(args.sdm_urls_json)
    xed_db = input_sqlite_db(args.xed_sqlite)
    all_maps = collect_all_maps(xed_db)
    output_all_maps(sdm_urls, all_maps, args.opcmap_html)

if __name__ == '__main__':
    main()
