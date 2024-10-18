#!/usr/bin/env python3

import sys
import re
import json
import sqlite3
from pathlib import Path
from argparse import ArgumentParser

python_version = sys.version_info
if not (python_version.major == 3 and python_version.minor >= 10):
    print('ERROR: this script requires Python 3.10 or above')
    sys.exit()

max_num_maps = 11

color_x86 = 'Black'
color_knl = 'DarkBlue'
color_amd = 'DarkGreen'
color_via = 'DarkMagenta'

def merge_colors(colors: list[str]) -> str:
    if color_x86 in colors:
        return color_x86
    return colors[0]

def get_family_color(family: str) -> str:
    if 'KNL' in family:
        return color_knl
    if 'AMD' in family:
        return color_amd
    if 'VIA' in family:
        return color_via
    assert family == 'X86'
    return color_x86

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
  font-family: "Monaco", "Lucida Console", monospace;
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
  width: 50%;
}}

/* The Close Button */
.close {{
  color: #aaaaaa;
  float: right;
  font-size: 200%;
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

cell_indent = '&emsp;&emsp;&emsp;'

def html_modal_button(modal_id: str, iclass: str, color: str, url: str | None) -> str:
    button = f'<div style="display: inline; color: {color}" id="modal_button_{modal_id}">{cell_indent}{iclass}</div>'
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

def make_mode_str(inst: InstDef) -> str:
    mode = inst['mode_restriction']
    if mode == 'not64':
        return '!64b mode'
    if mode == 0:
        return '16b mode'
    if mode == 1:
        return '32b mode'
    if mode == 2:
        return '64b mode'
    assert mode == 'unspecified'
    return 'Any mode'

def make_cpl_str(inst: InstDef) -> str:
    cpl = inst['cpl']
    if int(cpl) == 0:
        return ' CPL0'
    else:
        return ''

def make_legacy_prefix_str(inst: InstDef) -> str:
    pattern = inst['pattern']
    pfx = inst['pp'].split()
    if 'LOCK=1' in pattern:
        pfx.append('F0')
    if 'LOCK=0' in pattern:
        pfx.append('!F0')
    if 'ASZ=1' in pattern:
        pfx.append('67')
    if 'ASZ=0' in pattern:
        pfx.append('!67')
    if 'OSZ=1' in pattern and '66' not in pfx:
        pfx.append('66')
    if 'OSZ=0' in pattern and 'NP' not in pfx:
        pfx.append('!66')
    if 'REP=2' in pattern and 'F2' not in pfx:
        pfx.append('F2')
    if 'REP!=2' in pattern and 'NP' not in pfx:
        pfx.append('!F2')
    if 'REP=3' in pattern and 'F3' not in pfx:
        pfx.append('F3')
    if 'REP!=3' in pattern and 'NP' not in pfx:
        pfx.append('!F3')
    if 'REP=0' in pattern and 'NP' not in pfx:
        pfx.append('!F2')
        pfx.append('!F3')
    if ' REX2=1' in pattern:
        pfx.append('REX2')
    if ' NOREX2=1' in pattern:
        pfx.append('!REX2')
    if ' REXW=0' in pattern:
        pfx.append('W0')
    if ' REXW=1' in pattern:
        pfx.append('W1')
    if pfx == []:
        return ''
    else:
        return '-'.join(pfx) + ': '

re_nd_eq = re.compile(r'ND=(?P<val>0|1)')
re_nf_eq = re.compile(r'NF=(?P<val>0|1)')

def make_vex_evex_prefix_str(inst: InstDef) -> str:
    space = inst['space'].upper()
    map = int(inst['map'])
    pp = inst['pp']
    vl = inst['vl']
    pattern = inst['pattern']
    if vl is None or vl == 'n/a' or map == 4:
        vlen = ''
    else:
        vlen = f'-{vl}'
    rexw_prefix = inst['rexw_prefix']
    if rexw_prefix is None:
        rexw = ''
    elif rexw_prefix == 'unspecified':
        rexw = '-WIG'
    else:
        rexw = f'-W{rexw_prefix}'
    m = re_nd_eq.search(pattern)
    if m:
        val = m.group('val')
        nd_val = f'-ND{val}'
    else:
        nd_val = ''
    m = re_nf_eq.search(pattern)
    if m:
        val = m.group('val')
        nf_val = f'-NF{val}'
    else:
        nf_val = ''

    return f'{space}-MAP{map}-{pp}{vlen}{rexw}{nd_val}{nf_val}: '

def make_prefix_str(inst: InstDef) -> str:
    if inst['space'] == 'legacy':
        return make_legacy_prefix_str(inst)
    else:
        return make_vex_evex_prefix_str(inst)

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

def make_disasm_str(inst: InstDef) -> str:
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

def get_inst_family(inst: InstDef) -> str:
    extension = inst['extension']
    isa_set = inst['isa_set']
    if 'AVX512ER' in isa_set or 'AVX512PF' in isa_set:
        return f'KNL_{isa_set}'
    if '3DNOW' in extension or 'XOP' in extension or 'TBM' in extension or 'FMA4' in extension:
        if inst['iclass'] == 'PREFETCHW' and inst['opcode_hex'] == '0D' and int(inst['reg_required']) == 1:
            return 'X86'
        else:
            return f'AMD_{extension}'
    if 'AMD' in extension:
        return f'{extension}'
    if 'VIA' in extension:
        return f'{extension}'
    else:
        return 'X86'

def make_inst_div(inst: InstDef) -> tuple[str, str]:
    mode_str = make_mode_str(inst)
    cpl_str = make_cpl_str(inst)
    prefix_str = make_prefix_str(inst)
    opcode_str = make_opcode_str(inst)
    disasm_str = make_disasm_str(inst)
    family = get_inst_family(inst)
    color = get_family_color(family)
    if family == 'X86':
        family_str = ''
    else:
        family_str = f' ({family})'

    pattern = inst['pattern']
    return (f'<div style="color: {color}">{mode_str}{cpl_str} | {prefix_str}{opcode_str} | {disasm_str}{family_str} >>> {pattern}</div>',
            color)
        
prefix_opcode_dict = {
    0x66: 'OSIZE:', 0x67: 'ASIZE:',
    0xF0: 'LOCK:', 0xF2: 'REPNE:', 0xF3: 'REPE:',
    0x2E: 'CS:', 0x36: 'SS:', 0x3E: 'DS:', 0x26: 'ES:', 0x64: 'FS:', 0x65: 'GS:',
    0xC5: 'VEX2:', 0xC4: 'VEX3:',
    0x62: 'EVEX:',
    0xD5: 'REX2:',
}

def get_map0_special(opcode: int) -> list[str]:
    pfx = prefix_opcode_dict.get(opcode, None)
    if pfx:
        return [f'<div style="display: inline; color: {color_x86}">{cell_indent}{pfx}</div>']
    if opcode in range(0x40, 0x50):
        return [f'<div style="display: inline; color: {color_x86}">{cell_indent}REX:</div>']
    if opcode == 0x8F:
        return [f'<div style="display: inline; color: {color_amd}">{cell_indent}XOP:</div>']
    return []

def inst_sort_key(inst: InstDef):
    space = inst['space']
    space_key = 0 if space == 'legacy' else 1 if space == 'vex' else 2
    return (space_key, inst['vl'], inst['pattern'])

def html_cell(sdm_urls: SdmUrls, all_maps: AllOpcodeMaps, map_id: int, opcode: int) -> str:
    opcode_hex = f'{opcode:02X}'
    iclasses = sorted(all_maps[map_id][opcode].keys())
    cell_info = []
    if map_id == 0:
        cell_info += get_map0_special(opcode)
    for iclass in iclasses:
        modal_id = make_modal_id(map_id, opcode, iclass)
        iclass_url = sdm_urls.get(iclass, None)
        inst_defs = sorted(all_maps[map_id][opcode][iclass], key=inst_sort_key)
        inst_divs, inst_colors = zip(*[ make_inst_div(inst) for inst in inst_defs ])
        iclass_color = merge_colors(inst_colors)
        modal_button = html_modal_button(modal_id, iclass, iclass_color, iclass_url)
        modal_popup = html_modal_popup(modal_id, inst_divs)
        cell_info.append('\n'.join([modal_button, modal_popup]))
    cell_info_html = '<br>\n'.join(cell_info)
    return f'''
<td>
<b style="color: rgb(128,128,128); text-weight: 120%; padding: 4px">{opcode_hex}</b><br>
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
    amd_xop = 'AMD XOP ' if map_id >= 8 else ''
    return f'''
<button class="collapsible">{amd_xop}Map {map_id}</button>
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
        pattern = inst['pattern']
        if inst['partial_opcode']:
            for i in range(8):
                if iclass == 'PAUSE' and i > 0:
                    break
                if iclass == 'NOP' and (i > 0 or 'P4=0' in pattern):
                    break
                if iclass == 'XCHG' and opcode == 0x90 and i > 0 and 'SRM=0' in pattern:
                    break
                if iclass == 'XCHG' and opcode == 0x90 and i == 0:
                    continue
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
