"""Parse Sophia Script .psm1 to extract registry-based tweaks."""
import re, os, json

path = os.path.join(os.environ['TEMP'], 'sophia.psm1')
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

# Split into function blocks
func_pattern = re.compile(
    r'<#\s*\n(.*?)\n\s*#>\s*\n\s*function\s+(\w+)\s*\n(.*?)(?=\n<#\s*\n|\n#region\s|\Z)',
    re.DOTALL
)

functions = []
for match in func_pattern.finditer(content):
    help_block = match.group(1)
    func_name = match.group(2)
    func_body = match.group(3)

    # Extract synopsis
    synopsis_m = re.search(r'\.SYNOPSIS\s*\n\s*(.+?)(?=\n\s*\.|\n\s*#)', help_block, re.DOTALL)
    synopsis = synopsis_m.group(1).strip() if synopsis_m else ''

    # Extract parameters (Enable/Disable, Show/Hide, etc.)
    params = re.findall(r'\$(\w+)', re.findall(r'param\s*\((.*?)\)', func_body, re.DOTALL)[0]) if 'param' in func_body else []
    params = [p for p in params if p not in ('PSCmdlet',)]

    # Extract registry operations
    reg_ops = []
    for reg_match in re.finditer(
        r'New-ItemProperty\s+-Path\s+"?([^"\s]+)"?\s+-Name\s+"?([^"\s]+(?:\s+[^-][^"\s]*)*)"?\s+'
        r'-(?:PropertyType|Type)\s+(\w+)\s+-Value\s+"?([^"\s]+)"?',
        func_body
    ):
        reg_ops.append({
            'path': reg_match.group(1).replace(':\\', '\\'),
            'name': reg_match.group(2),
            'type': reg_match.group(3).lower(),
            'value': reg_match.group(4),
        })

    # Also catch simpler patterns
    for reg_match in re.finditer(
        r'New-ItemProperty\s+-Path\s+([^\s]+)\s+-Name\s+(\w+)\s+-PropertyType\s+(\w+)\s+-Value\s+(\S+)',
        func_body
    ):
        path_val = reg_match.group(1).replace(':\\', '\\').strip('"')
        entry = {
            'path': path_val,
            'name': reg_match.group(2),
            'type': reg_match.group(3).lower(),
            'value': reg_match.group(4),
        }
        if entry not in reg_ops:
            reg_ops.append(entry)

    if not reg_ops:
        continue

    # Skip cursor-related, complex multi-step functions
    if func_name in ('Install', 'Uninstall', 'Export', 'Import', 'Set', 'Logging',
                      'Install-Cursors', 'ScanRegistryPolicies'):
        continue

    functions.append({
        'name': func_name,
        'synopsis': synopsis,
        'params': params,
        'registry': reg_ops,
        'reg_count': len(reg_ops),
    })

# Print summary
for fn in sorted(functions, key=lambda x: x['name']):
    params_str = '/'.join(fn['params']) if fn['params'] else 'none'
    print('%s (%s) [%d reg keys]' % (fn['name'], params_str, fn['reg_count']))
    print('  %s' % fn['synopsis'][:100])
    print()

print('Total: %d registry-touching functions' % len(functions))
