import os, zipfile, json, re, datetime

# 1. Crear carpeta de salida 'generated-diff'
output_dir = 'generated-diff'
os.makedirs(output_dir, exist_ok=True)

# 2. Descomprimir zip de contratos si existe
if os.path.exists('contracts-ios.zip'):
    with zipfile.ZipFile('contracts-ios.zip', 'r') as z:
        z.extractall('extracted_contracts')

contracts_dir = 'extracted_contracts/contracts-ios' if os.path.exists('extracted_contracts/contracts-ios') else '.'

# 3. Leer HTML base
html_files = [f for f in os.listdir('.') if f.endswith('.html') and 'Actualizado' not in f and not f.startswith('Reporte_Contratos_20')]
if not html_files:
    html_files = [f for f in os.listdir('.') if f.endswith('.html')]

if not html_files:
    print('❌ No se encontró ningún archivo HTML base en la carpeta.')
    exit()

with open(html_files[0], 'r', encoding='utf-8') as f:
    raw_html = f.read()

# 4. Extraer eventos de CleverTap
blocks = re.findall(r'<details[\s\S]*?</details>', raw_html)
ct_events = {}

for block in blocks:
    codes = re.findall(r'<div class="diff-code">([\s\S]*?)</div>\s*</div>', block)
    if len(codes) >= 2:
        divs = codes[1].split('<div style="display: flex;')
        lines = []
        for d in divs[1:]:
            spans = re.findall(r'<span[^>]*>([\s\S]*?)</span>', d)
            if len(spans) >= 2 and spans[0].strip() != "":
                lines.append(spans[1].replace('&nbsp;', ' ').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>'))
        proc = []
        for i, l in enumerate(lines):
            s = l.strip()
            if i < len(lines) - 1:
                ns = lines[i+1].strip()
                if not s.endswith('{') and not s.endswith('[') and not ns.startswith('}') and not ns.startswith(']'):
                    l += ','
            proc.append(l)
        try:
            obj = json.loads("\n".join(proc))
            evt = obj.get('eventName')
            if evt == 'load_refund_finish_ok':
                if 'load_refund_finish_ok_BACK' not in ct_events: ct_events['load_refund_finish_ok_BACK'] = obj
                else: ct_events['load_refund_finish_ok'] = obj
            else: ct_events[evt] = obj
        except: pass

def build_tree(contract, actual, name=None, depth=0, path_str='', parent_is_array=False):
    rows = []
    in_c, in_a = contract is not None, actual is not None
    is_obj_c = in_c and isinstance(contract, (dict, list))
    is_obj_a = in_a and isinstance(actual, (dict, list))

    if is_obj_c or is_obj_a:
        is_arr = (is_obj_c and isinstance(contract, list)) or (is_obj_a and isinstance(actual, list))
        rows.append({'key': name, 'depth': depth, 'type': 'array_start' if is_arr else 'object_start', 'inC': in_c, 'inA': in_a, 'path': path_str, 'parentIsArray': parent_is_array})
        
        keys_c = list(range(len(contract))) if (is_obj_c and isinstance(contract, list)) else (list(contract.keys()) if is_obj_c else [])
        keys_a = list(range(len(actual))) if (is_obj_a and isinstance(actual, list)) else (list(actual.keys()) if is_obj_a else [])
        
        all_keys = []
        for k in keys_c + keys_a:
            if k not in all_keys: all_keys.append(k)
        if not is_arr: all_keys.sort(key=lambda x: str(x))

        for k in all_keys:
            child_path = f"{path_str}[{k}]" if parent_is_array or is_arr else (f"{path_str}.{k}" if path_str else str(k))
            val_c = contract[k] if (is_obj_c and ((isinstance(contract, list) and k < len(contract)) or (isinstance(contract, dict) and k in contract))) else None
            val_a = actual[k] if (is_obj_a and ((isinstance(actual, list) and k < len(actual)) or (isinstance(actual, dict) and k in actual))) else None
            rows.extend(build_tree(val_c, val_a, str(k), depth + 1, child_path, is_arr))

        rows.append({'key': name, 'depth': depth, 'type': 'array_end' if is_arr else 'object_end', 'inC': in_c, 'inA': in_a, 'path': path_str, 'parentIsArray': parent_is_array})
    else:
        rows.append({'key': name, 'depth': depth, 'type': 'primitive', 'valC': contract, 'valA': actual, 'inC': in_c, 'inA': in_a, 'path': path_str, 'parentIsArray': parent_is_array})
    return rows

target_id = "-v7db58013ca9c4539aaa6ed74beb6ae59"
search_sum = ct_events.get('click_search_home_button_search')
search_has_arrive = search_sum is not None and ('arrive_date_selected' in search_sum)

charged_sum = ct_events.get('Charged')
is_roundtrip = False
if charged_sum and 'Items' in charged_sum and isinstance(charged_sum['Items'], list) and len(charged_sum['Items']) > 0:
    if charged_sum['Items'][0].get('back_date', '') != '': is_roundtrip = True

diff_cards_html = ""
files = sorted([f for f in os.listdir(contracts_dir) if f.endswith('.json')])

for i, f_name in enumerate(files):
    f_path = os.path.join(contracts_dir, f_name)
    with open(f_path, 'r', encoding='utf-8') as jf: ref_contract = json.load(jf)
    evt_raw = f_name.replace('.json', '')
    if evt_raw == 'load_refund_finish_ok_BACK' and not is_roundtrip: continue
    if evt_raw == 'click_search_home_button_search_roundtrip' and not search_has_arrive: continue
    if evt_raw == 'click_search_home_button_search_oneway' and search_has_arrive: continue

    actual_key = evt_raw
    display_file = f_name
    sub_tag = None

    if evt_raw == 'load_refund_finish_ok_BACK': sub_tag = 'BACK (1ro)'
    if evt_raw == 'load_refund_finish_ok' and is_roundtrip: sub_tag = 'GO (2do)'
    if evt_raw in ['click_search_home_button_search_roundtrip', 'click_search_home_button_search_oneway']:
        actual_key = 'click_search_home_button_search'
        display_file = 'click_search_home_button_search.json'
        sub_tag = 'roundtrip' if evt_raw == 'click_search_home_button_search_roundtrip' else 'oneway'

    actual_sum = ct_events.get(actual_key)
    rows = build_tree(ref_contract, actual_sum)
    has_err = False
    left_h, right_h = "", ""

    for r_idx, r in enumerate(rows):
        fmt_err = False
        if r['inC'] and not r['inA'] and r['type'] == 'primitive': has_err = True
        if r['inA'] and r['type'] == 'primitive' and r['path']:
            fk = re.sub(r'\[\d+\]', '', r['path'].split('.')[-1])
            if 'date' in fk.lower():
                vc_str = str(r['valC']) if isinstance(r['valC'], str) else ''
                if vc_str.startswith('$D_') and r['valA'] not in ['', None]:
                    if not isinstance(r['valA'], str) or not r['valA'].startswith('$D_'): fmt_err, has_err = True, True

        indent = '&nbsp;' * (r['depth'] * 4)
        fk_str = f'"{r["key"]}": ' if (r['key'] is not None and not r['parentIsArray']) else ''

        def rv(v):
            if v is None: return 'null'
            if isinstance(v, str): return f'"{v}"'
            if isinstance(v, bool): return 'true' if v else 'false'
            return str(v)

        cc = f'{indent}{fk_str}{{' if r['type']=='object_start' and r['inC'] else (f'{indent}{fk_str}[' if r['type']=='array_start' and r['inC'] else (f'{indent}}}' if r['type']=='object_end' and r['inC'] else (f'{indent}]' if r['type']=='array_end' and r['inC'] else (f'{indent}{fk_str}{rv(r["valC"])}' if r['type']=='primitive' and r['inC'] else ''))))
        ca = f'{indent}{fk_str}{{' if r['type']=='object_start' and r['inA'] else (f'{indent}{fk_str}[' if r['type']=='array_start' and r['inA'] else (f'{indent}}}' if r['type']=='object_end' and r['inA'] else (f'{indent}]' if r['type']=='array_end' and r['inA'] else (f'{indent}{fk_str}{rv(r["valA"])}' if r['type']=='primitive' and r['inA'] else ''))))

        l_bg = '#ffeef0' if (r['inC'] and not r['inA']) else ('#f1f5f9' if (fmt_err or (r['type']=='primitive' and r['valC']!=r['valA'] and r['inC'])) else 'transparent')
        r_bg = '#ffeef0' if fmt_err else ('#e6ffec' if (not r['inC'] and r['inA']) else ('#e0f2fe' if (r['type']=='primitive' and r['valC']!=r['valA']) else 'transparent'))

        left_h += f'<div style="display: flex; background: {l_bg}; min-height: 22px; align-items: center; padding: 2px 0;"><span style="width: 35px; min-width: 35px; color: #8c959f; text-align: right; padding-right: 10px; font-size: 11px; user-select: none;">{r_idx + 1 if r["inC"] else ""}</span><span style="font-family: ui-monospace, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word;">{cc}</span></div>'
        if actual_sum:
            right_h += f'<div style="display: flex; background: {r_bg}; min-height: 22px; align-items: center; padding: 2px 0;"><span style="width: 35px; min-width: 35px; color: #8c959f; text-align: right; padding-right: 10px; font-size: 11px; user-select: none;">{r_idx + 1 if r["inA"] else ""}</span><span style="font-family: ui-monospace, monospace; font-size: 12px; white-space: pre-wrap; word-break: break-word;">{ca}</span></div>'

    badge = '❌' if (has_err or not actual_sum) else '✅'
    label = f'{display_file} [{sub_tag}]' if sub_tag else display_file
    rt_title = f'CLEVERTAP ({target_id} - Version: {actual_sum.get("Version", actual_sum.get("version", "2.0.0"))})' if actual_sum else f'CLEVERTAP ({target_id} - No registrado)'

    diff_cards_html += f'<details {"open=""" if i==0 else ""} class="diff-container"><summary class="diff-header"><div class="diff-panel">{badge} CONTRATO ({label})</div><div class="diff-panel">{rt_title}</div></summary><div class="diff-body"><div class="diff-code">{left_h}</div><div class="diff-code">{right_h}</div></div></details>'

master_html = f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Reporte Contratos por Usuario: {target_id}</title><style>body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; margin: 20px; background: #fff; color: #24292e; }}.header-container {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #e2e8f0; padding-bottom: 15px; }}.diff-container {{ border: 1px solid #d0d7de; border-radius: 6px; overflow: hidden; font-size: 12px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}details.diff-container summary {{ list-style: none; }}details.diff-container summary::-webkit-details-marker {{ display: none; }}.diff-header {{ display: flex; background: #f6f8fa; font-weight: 700; color: #24292e; cursor: pointer; user-select: none; transition: background 0.2s; }}.diff-header:hover {{ background: #eaeef2; }}.diff-panel {{ flex: 1; padding: 12px 15px; border-right: 1px solid #d0d7de; }}.diff-panel:last-child {{ border-right: none; }}.diff-body {{ display: flex; font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, monospace; border-top: 1px solid #d0d7de; }}.diff-code {{ flex: 1; overflow-x: auto; padding: 10px 0; border-right: 1px solid #d0d7de; }}.diff-code:last-child {{ border-right: none; }}</style></head><body><div class="header-container"><h2 style="color: #0f172a; margin: 0;">📊 Reporte de Contratos para Usuario: <span style="color: #2563eb;">{target_id}</span></h2></div>{diff_cards_html}</body></html>'

# 5. Generar nombre con timestamp y guardar en 'generated-diff/'
now_str = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
output_filename = f"Reporte_Contratos_{now_str}.html"
output_path = os.path.join(output_dir, output_filename)

with open(output_path, 'w', encoding='utf-8') as out_f:
    out_f.write(master_html)

print(f"🎉 ¡Listo! El reporte se guardó en: {output_path}")