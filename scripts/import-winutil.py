"""Import WinUtil tweaks.json into perch-gallery YAML format."""
import json, os, re, sys

path = os.path.join(os.environ['TEMP'], 'winutil-tweaks.json')
with open(path, 'r', encoding='utf-8') as f:
    data = json.loads(f.read(), strict=False)

existing_keywords = [
    'Dark Theme', 'Bing Search', 'Mouse Acceleration', 'Sticky Keys',
    'Show Hidden Files', 'Show File Extensions', 'Center Taskbar',
    'Widgets', 'Copilot', 'Classic Right-Click'
]

already = set()
for key, tweak in data.items():
    name = tweak.get('Content', '')
    for kw in existing_keywords:
        if kw.lower() in name.lower():
            already.add(key)


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


def convert_path(p):
    return p.replace(':\\', '\\')


def convert_type(t):
    return t.lower()


def convert_value(v, typ):
    if v == '<RemoveEntry>':
        return None
    if typ.lower() == 'dword':
        try:
            return int(v)
        except (ValueError, TypeError):
            return v
    return v


def format_value(v):
    if v is None:
        return 'null'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        if v == '':
            return '""'
        if any(c in v for c in ':{}[],"\'&#*?|-><!%@`'):
            return '"%s"' % v.replace('"', '\\"')
        return v
    return str(v)


# (category, tags, profiles, windows-versions)
tweak_meta = {
    # WPFToggle* keys (preference toggles)
    'WPFToggleNumLock': ('Input/Keyboard', ['keyboard', 'numlock', 'startup'], ['power-user'], [10, 11]),
    'WPFToggleVerboseLogon': ('System/Diagnostics', ['diagnostics', 'logon', 'verbose'], ['developer'], [10, 11]),
    'WPFToggleStartMenuRecommendations': ('Search/Start Menu', ['start-menu', 'recommendations', 'declutter'], ['power-user'], [11]),
    'WPFToggleHideSettingsHome': ('System/Settings', ['settings', 'home-page', 'declutter'], ['power-user'], [11]),
    'WPFToggleMultiplaneOverlay': ('System/Graphics', ['graphics', 'multiplane-overlay', 'performance'], ['power-user'], [10, 11]),
    'WPFToggleNewOutlook': ('System/Settings', ['outlook', 'microsoft', 'mail'], ['power-user'], [11]),
    'WPFToggleS3Sleep': ('Power/Sleep', ['power', 'sleep', 's3', 'standby'], ['power-user'], [10, 11]),
    'WPFToggleTaskbarSearch': ('Taskbar/Declutter', ['taskbar', 'search', 'declutter'], ['power-user'], [10, 11]),
    'WPFToggleTaskView': ('Taskbar/Declutter', ['taskbar', 'task-view', 'declutter'], ['power-user'], [10, 11]),
    'WPFToggleDetailedBSoD': ('System/Diagnostics', ['bsod', 'diagnostics', 'crash'], ['developer'], [10, 11]),
    'WPFToggleDisableCrossDeviceResume': ('Privacy/Sync', ['privacy', 'cross-device', 'sync', 'resume'], ['power-user'], [11]),
    # WPFTweaks* keys (essential/advanced tweaks)
    'WPFTweaksActivity': ('Privacy/Tracking', ['privacy', 'activity-history', 'telemetry'], ['power-user'], [10, 11]),
    'WPFTweaksBraveDebloat': ('Browsers/Debloat', ['brave', 'browser', 'debloat'], ['power-user'], [10, 11]),
    'WPFTweaksConsumerFeatures': ('Privacy/Advertising', ['privacy', 'consumer-features', 'suggestions'], ['power-user'], [10, 11]),
    'WPFTweaksDisableBGapps': ('Performance/Background', ['performance', 'background-apps', 'resources'], ['power-user'], [10, 11]),
    'WPFTweaksDisableFSO': ('Performance/Gaming', ['gaming', 'fullscreen', 'performance'], ['power-user'], [10, 11]),
    'WPFTweaksDisableNotifications': ('Taskbar/Declutter', ['taskbar', 'notifications', 'calendar', 'declutter'], ['power-user'], [10, 11]),
    'WPFTweaksEdgeDebloat': ('Browsers/Debloat', ['edge', 'browser', 'debloat', 'microsoft'], ['power-user'], [10, 11]),
    'WPFTweaksEndTaskOnTaskbar': ('Taskbar/Productivity', ['taskbar', 'end-task', 'right-click'], ['developer', 'power-user'], [11]),
    'WPFTweaksIPv46': ('Networking/Protocol', ['networking', 'ipv4', 'ipv6'], ['power-user'], [10, 11]),
    'WPFTweaksLocation': ('Privacy/Tracking', ['privacy', 'location', 'tracking'], ['power-user'], [10, 11]),
    'WPFTweaksStorage': ('System/Storage', ['storage', 'storage-sense', 'cleanup'], ['power-user'], [10, 11]),
    'WPFTweaksUTC': ('System/Clock', ['clock', 'utc', 'dual-boot', 'linux'], ['developer'], [10, 11]),
    'WPFTweaksWPBT': ('Security/Firmware', ['security', 'firmware', 'wpbt'], ['power-user'], [10, 11]),
    'WPFTweaksHiber': ('Power/Hibernation', ['power', 'hibernation', 'disk-space'], ['power-user'], [10, 11]),
    'WPFTweaksTelemetry': ('Privacy/Telemetry', ['privacy', 'telemetry', 'microsoft'], ['power-user'], [10, 11]),
    'WPFTweaksRestorePoint': ('System/Backup', ['backup', 'restore-point', 'system-protection'], ['power-user'], [10, 11]),
    'WPFTweaksDisplay': ('Performance/Visual', ['performance', 'visual-effects', 'animations'], ['power-user'], [10, 11]),
    'WPFTweaksRazerBlock': ('System/Bloatware', ['razer', 'bloatware', 'driver'], ['power-user'], [10, 11]),
    'WPFTweaksDisableIPv6': ('Networking/Protocol', ['networking', 'ipv6', 'disable'], ['power-user'], [10, 11]),
    'WPFTweaksTeredo': ('Networking/Protocol', ['networking', 'teredo', 'ipv6', 'tunnel'], ['power-user'], [10, 11]),
}

outdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'catalog', 'tweaks')
generated = []

for key, tweak in data.items():
    if key in already:
        continue
    if 'registry' not in tweak:
        continue
    meta = tweak_meta.get(key)
    if not meta:
        continue

    category, tags, profiles, versions = meta
    name = tweak['Content'].strip()
    slug = slugify(name)
    desc = tweak.get('Description', name).replace('"', '\\"')
    has_script = 'InvokeScript' in tweak

    lines = []
    lines.append('type: tweak')
    lines.append('name: %s' % format_value(name))
    lines.append('category: %s' % category)
    lines.append('tags: [%s]' % ', '.join(tags))
    lines.append('description: "%s"' % desc)
    lines.append('reversible: true')
    lines.append('profiles: [%s]' % ', '.join(profiles))
    lines.append('windows-versions: [%s]' % ', '.join(str(v) for v in versions))
    lines.append('source: winutil')
    if has_script:
        lines.append('# NOTE: WinUtil also has InvokeScript/UndoScript for this tweak (not imported)')
    lines.append('registry:')

    for entry in tweak['registry']:
        rkey = convert_path(entry['Path'])
        rname = entry.get('Name', '')
        rtype = convert_type(entry.get('Type', 'dword'))
        rval = convert_value(entry.get('Value', ''), entry.get('Type', 'DWord'))
        rdefault = convert_value(entry.get('OriginalValue', ''), entry.get('Type', 'DWord'))

        lines.append('  - key: %s' % rkey)
        lines.append('    name: %s' % format_value(rname))
        lines.append('    value: %s' % format_value(rval))
        lines.append('    type: %s' % rtype)
        lines.append('    default-value: %s' % format_value(rdefault))

    lines.append('')

    filepath = os.path.join(outdir, slug + '.yaml')
    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    generated.append(slug)

print('Generated %d files:' % len(generated))
for s in sorted(generated):
    print('  catalog/tweaks/%s.yaml' % s)
