"""Import Sophia Script functions into perch-gallery YAML format.

Parses Sophia.psm1 to extract registry-based tweaks with Enable/Disable
or Show/Hide parameter pairs.
"""
import re, os, json

path = os.path.join(os.environ['TEMP'], 'sophia.psm1')
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s]+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s.strip('-')


# Map existing gallery tweaks by rough topic to skip duplicates
existing_topics = {
    'advertising-id', 'aero-shake', 'dark-mode', 'web-search',
    'bsod', 'detailed-bsod', 'compact-mode', 'file-extensions',
    'show-file-extensions', 'hidden-files', 'show-hidden-files',
    'explorer-open-this-pc', 'storage-sense', 'disable-storage-sense',
    'task-view', 'task-view-button', 'taskbar-alignment',
    'taskbar-alignment-left', 'end-task', 'enable-end-task',
    'search-button', 'search-button-in-taskbar', 'widgets',
    'disable-widgets', 'long-paths', 'long-paths-enabled',
    'recommendations-in-start-menu', 'sticky-keys', 'disable-sticky-keys',
    'mouse-acceleration', 'disable-mouse-acceleration', 'numlock',
    'numlock-on-startup', 'copilot', 'disable-copilot-button',
    'chat-icon', 'disable-chat-icon', 'disable-hibernation',
    's3-sleep', 'disable-telemetry', 'disable-activity-history',
    'disable-consumerfeatures', 'disable-location-tracking',
    'cross-device-resume', 'disable-background-apps',
    'disable-fullscreen-optimizations', 'set-display-for-performance',
    'prefer-ipv4', 'disable-ipv6', 'disable-teredo',
    'edge-debloat', 'brave-debloat', 'block-razer',
    'create-restore-point', 'disable-multiplane-overlay',
    'new-outlook', 'remove-settings-home-page',
    'set-time-to-utc', 'verbose-messages', 'disable-notification',
    'disable-wpbt', 'pin-to-start', 'classic-context-menu',
    'hide-this-pc-folders', 'show-full-path', 'show-protected-os-files',
    'hide-onedrive-navigation', 'hide-network-navigation',
}

# Sophia function -> existing gallery mapping (skip these)
skip_functions = {
    'AdvertisingID',      # disable-advertising-id
    'AeroShaking',        # disable-aero-shake
    'AppColorMode',       # dark-mode (partial)
    'WindowsColorMode',   # dark-mode (partial)
    'BingSearch',         # disable-web-search
    'BSoDStopError',      # detailed-bsod
    'FileExplorerCompactMode',  # compact-mode
    'FileExtensions',     # show-file-extensions
    'HiddenItems',        # show-hidden-files
    'OpenFileExplorerTo', # explorer-open-this-pc
    'StorageSense',       # disable-storage-sense
    'TaskViewButton',     # task-view-button-in-taskbar
    'TaskbarAlignment',   # taskbar-alignment-left
    'TaskbarEndTask',     # enable-end-task-with-right-click
    'TaskbarSearch',      # search-button-in-taskbar
    'TaskbarWidgets',     # disable-widgets
    'Win32LongPathsSupport',  # long-paths-enabled
    'StartRecommendationsTips',  # recommendations-in-start-menu (overlap)
    'Hibernation',        # disable-hibernation (script-only in Sophia)
    # Complex functions not suitable for simple registry YAML
    'FolderGroupBy',      # complex explorer view settings
    'Install-Cursors',    # cursor installation
    'OneDrive',           # complex uninstall/reinstall
    'DefaultTerminalApp', # complex app registration
    'DNSoverHTTPS',       # complex DNS configuration
    'CleanupTask',        # scheduled task, not registry
    'SoftwareDistributionTask',  # scheduled task
    'TempTask',           # scheduled task
}

# (category, tags, profiles, windows-versions, name, description)
sophia_meta = {
    'ActiveHours': ('System/Updates', ['updates', 'active-hours', 'restart'], ['power-user'], [10, 11],
                    'Set Active Hours Automatically', 'Automatically adjust active hours based on device activity to avoid restart during use'),
    'AdminApprovalMode': ('Security/UAC', ['security', 'uac', 'admin'], ['power-user'], [10, 11],
                          'Disable UAC Admin Approval Mode', 'Disable the User Account Control admin approval mode for the built-in Administrator account'),
    'AppsSilentInstalling': ('Privacy/Advertising', ['privacy', 'auto-install', 'suggestions'], ['power-user'], [10, 11],
                             'Disable Silent App Installing', 'Disable automatic installing of suggested apps'),
    'AppsSmartScreen': ('Security/Defender', ['security', 'smartscreen', 'defender'], ['power-user'], [10, 11],
                        'Disable App SmartScreen', 'Disable Microsoft Defender SmartScreen for apps'),
    'Autoplay': ('System/Devices', ['autoplay', 'media', 'devices'], ['power-user'], [10, 11],
                 'Disable AutoPlay', 'Disable AutoPlay for all media and devices'),
    'CABInstallContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'cab', 'install'], ['developer'], [10, 11],
                          'Add CAB Install Context Menu', 'Add Install item to .cab file context menu'),
    'CheckBoxes': ('Explorer/Appearance', ['explorer', 'checkboxes', 'selection'], ['power-user'], [10, 11],
                   'Disable Item Check Boxes', 'Disable item check boxes in File Explorer'),
    'ClockInNotificationCenter': ('Taskbar/Clock', ['taskbar', 'clock', 'notification-center'], ['power-user'], [11],
                                  'Show Clock in Notification Center', 'Show clock in the notification center area'),
    'CompressedFolderNewContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'zip', 'new'], ['power-user'], [10, 11],
                                  'Add Compressed Folder to New Menu', 'Add Compressed (zipped) Folder to the New context menu'),
    'ControlPanelView': ('System/Settings', ['control-panel', 'icons', 'view'], ['power-user'], [10, 11],
                         'Control Panel Icon View', 'Set Control Panel to large/small icons or category view'),
    'DeliveryOptimization': ('System/Updates', ['updates', 'delivery-optimization', 'bandwidth'], ['power-user'], [10, 11],
                             'Disable Delivery Optimization', 'Disable Windows Update Delivery Optimization for peer-to-peer updates'),
    'DiagnosticDataLevel': ('Privacy/Telemetry', ['privacy', 'diagnostics', 'telemetry'], ['power-user'], [10, 11],
                            'Set Diagnostic Data to Minimum', 'Set diagnostic data collection to required (minimum) level'),
    'EventViewerCustomView': ('System/Diagnostics', ['event-viewer', 'diagnostics', 'process-creation'], ['developer'], [10, 11],
                              'Enable Process Creation Event View', 'Create a custom Event Viewer view for process creation events'),
    'FeedbackFrequency': ('Privacy/Telemetry', ['privacy', 'feedback', 'telemetry'], ['power-user'], [10, 11],
                          'Disable Feedback Requests', 'Set Windows feedback frequency to never'),
    'FileTransferDialog': ('Explorer/Appearance', ['explorer', 'file-transfer', 'dialog'], ['power-user'], [10, 11],
                           'Detailed File Transfer Dialog', 'Show detailed file transfer dialog box'),
    'FirstLogonAnimation': ('Appearance/Logon', ['appearance', 'logon', 'animation'], ['power-user'], [10, 11],
                            'Disable First Logon Animation', 'Disable the first sign-in animation'),
    'GPUScheduling': ('Performance/GPU', ['performance', 'gpu', 'scheduling'], ['power-user'], [10, 11],
                      'Enable GPU Scheduling', 'Enable hardware-accelerated GPU scheduling'),
    'JPEGWallpapersQuality': ('Appearance/Wallpaper', ['appearance', 'wallpaper', 'jpeg', 'quality'], ['power-user'], [10, 11],
                              'Max JPEG Wallpaper Quality', 'Set JPEG desktop wallpaper import quality to maximum'),
    'LocalSecurityAuthority': ('Security/System', ['security', 'lsa', 'credential-guard'], ['power-user'], [10, 11],
                               'Enable LSA Protection', 'Enable Local Security Authority protection'),
    'MergeConflicts': ('Explorer/Behavior', ['explorer', 'merge', 'conflicts'], ['power-user'], [10, 11],
                       'Show Folder Merge Conflicts', 'Show folder merge conflicts in File Explorer'),
    'MostUsedStartApps': ('Search/Start Menu', ['start-menu', 'most-used', 'apps'], ['power-user'], [10, 11],
                          'Hide Most Used Start Apps', 'Hide most used apps from Start menu'),
    'MSIExtractContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'msi', 'extract'], ['developer'], [10, 11],
                          'Add MSI Extract Context Menu', 'Add Extract All item to .msi file context menu'),
    'MultipleInvokeContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'bulk-selection'], ['power-user'], [10, 11],
                              'Enable Bulk File Actions', 'Allow Open/Print/Edit for more than 15 selected files'),
    'NavigationPaneExpand': ('Explorer/Navigation', ['explorer', 'navigation', 'expand'], ['power-user'], [10, 11],
                             'Expand to Current Folder', 'Expand navigation pane to current folder'),
    'NetworkAdaptersSavePower': ('Power/Devices', ['power', 'network', 'wake', 'sleep'], ['power-user'], [10, 11],
                                 'Disable Network Adapter Power Saving', 'Prevent network adapters from waking the computer and disable power saving'),
    'OneDriveFileExplorerAd': ('Explorer/Declutter', ['explorer', 'onedrive', 'ads', 'notifications'], ['power-user'], [10, 11],
                               'Disable OneDrive File Explorer Ads', 'Disable OneDrive sync provider notifications in File Explorer'),
    'PowerShellModulesLogging': ('Security/Logging', ['security', 'powershell', 'logging'], ['developer'], [10, 11],
                                 'Enable PowerShell Module Logging', 'Enable logging for all PowerShell modules'),
    'PowerShellScriptsLogging': ('Security/Logging', ['security', 'powershell', 'script-logging'], ['developer'], [10, 11],
                                 'Enable PowerShell Script Logging', 'Enable logging for all PowerShell scripts'),
    'PreventEdgeShortcutCreation': ('Browsers/Debloat', ['edge', 'shortcuts', 'desktop'], ['power-user'], [10, 11],
                                    'Prevent Edge Desktop Shortcuts', 'Prevent Microsoft Edge from creating desktop shortcuts on update'),
    'PrintCMDContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'batch', 'print'], ['developer'], [10, 11],
                        'Add Print to BAT/CMD Context Menu', 'Add Print item to .bat and .cmd file context menu'),
    'QuickAccessFrequentFolders': ('Explorer/Navigation', ['explorer', 'quick-access', 'folders'], ['power-user'], [10, 11],
                                   'Hide Frequent Folders in Quick Access', 'Hide frequently used folders from Quick Access'),
    'QuickAccessRecentFiles': ('Explorer/Navigation', ['explorer', 'quick-access', 'recent-files'], ['power-user'], [10, 11],
                                'Hide Recent Files in Quick Access', 'Hide recently used files from Quick Access'),
    'RecentlyAddedStartApps': ('Search/Start Menu', ['start-menu', 'recently-added', 'apps'], ['power-user'], [10, 11],
                                'Hide Recently Added Start Apps', 'Hide recently added apps from Start menu'),
    'RecommendedTroubleshooting': ('System/Troubleshooting', ['troubleshooting', 'automatic', 'diagnostics'], ['power-user'], [10, 11],
                                   'Disable Auto Troubleshooting', 'Set recommended troubleshooter preferences to default'),
    'RecycleBinDeleteConfirmation': ('Explorer/Behavior', ['explorer', 'recycle-bin', 'confirmation'], ['power-user'], [10, 11],
                                     'Enable Delete Confirmation', 'Show delete confirmation dialog for Recycle Bin'),
    'RestartDeviceAfterUpdate': ('System/Updates', ['updates', 'restart', 'automatic'], ['power-user'], [10, 11],
                                 'Disable Auto Restart After Update', 'Prevent automatic restart after Windows Update'),
    'RestartNotification': ('System/Updates', ['updates', 'restart', 'notification'], ['power-user'], [10, 11],
                            'Show Restart Notification', 'Show notification when PC requires restart for updates'),
    'RestorePreviousFolders': ('Explorer/Behavior', ['explorer', 'restore', 'folders', 'logon'], ['power-user'], [10, 11],
                                'Restore Folders at Logon', 'Restore previous folder windows at logon'),
    'SaveZoneInformation': ('Security/Downloads', ['security', 'zone', 'downloads', 'block'], ['power-user'], [10, 11],
                            'Disable Zone Information Saving', 'Do not save zone information (Mark of the Web) in downloaded files'),
    'SearchHighlights': ('Search/Start Menu', ['search', 'highlights', 'bing'], ['power-user'], [10, 11],
                          'Disable Search Highlights', 'Disable search highlights (trending images/news) in search'),
    'SecondsInSystemClock': ('Taskbar/Clock', ['taskbar', 'clock', 'seconds'], ['power-user'], [11],
                              'Show Seconds in Clock', 'Show seconds on the taskbar clock'),
    'SettingsSuggestedContent': ('Privacy/Advertising', ['privacy', 'settings', 'suggestions'], ['power-user'], [10, 11],
                                 'Disable Settings Suggestions', 'Disable suggested content in the Settings app'),
    'ShortcutsSuffix': ('Explorer/Behavior', ['explorer', 'shortcuts', 'suffix'], ['power-user'], [10, 11],
                         'Remove Shortcut Suffix', 'Remove the - Shortcut suffix from new shortcuts'),
    'SnapAssist': ('Appearance/Window Management', ['window-management', 'snap', 'assist'], ['power-user'], [10, 11],
                   'Disable Snap Assist', 'Disable Snap Assist window arrangement suggestions'),
    'StartAccountNotifications': ('Search/Start Menu', ['start-menu', 'account', 'notifications'], ['power-user'], [11],
                                  'Disable Start Account Notifications', 'Disable Microsoft account notifications in Start'),
    'StartLayout': ('Search/Start Menu', ['start-menu', 'layout', 'pins'], ['power-user'], [11],
                    'Configure Start Layout', 'Set Start layout to show more pins or more recommendations'),
    'StartRecommendedSection': ('Search/Start Menu', ['start-menu', 'recommended', 'declutter'], ['power-user'], [11],
                                 'Hide Recommended Section', 'Hide the entire Recommended section in Start'),
    'TailoredExperiences': ('Privacy/Telemetry', ['privacy', 'tailored-experiences', 'telemetry'], ['power-user'], [10, 11],
                            'Disable Tailored Experiences', 'Disable tailored experiences based on diagnostic data'),
    'TaskbarCombine': ('Taskbar/Layout', ['taskbar', 'combine', 'labels'], ['power-user'], [11],
                       'Never Combine Taskbar Buttons', 'Show labels and never combine taskbar buttons'),
    'ThisPC': ('Explorer/Desktop', ['explorer', 'desktop', 'this-pc', 'icon'], ['power-user'], [10, 11],
               'Show This PC on Desktop', 'Show This PC icon on the desktop'),
    'UpdateMicrosoftProducts': ('System/Updates', ['updates', 'microsoft', 'office'], ['power-user'], [10, 11],
                                'Update Other Microsoft Products', 'Receive updates for other Microsoft products via Windows Update'),
    'UseStoreOpenWith': ('System/Settings', ['store', 'open-with', 'app-suggestions'], ['power-user'], [10, 11],
                         'Hide Store in Open With', 'Hide Look for an app in the Microsoft Store from Open With dialog'),
    'WhatsNewInWindows': ('Privacy/Advertising', ['privacy', 'tips', 'whats-new'], ['power-user'], [10, 11],
                          'Disable What\'s New in Windows', 'Disable the Ways to get the most out of Windows notifications'),
    'WindowsLatestUpdate': ('System/Updates', ['updates', 'latest', 'preview'], ['power-user'], [10, 11],
                            'Get Latest Windows Updates', 'Opt in to receive latest updates as soon as available'),
    'WindowsTips': ('Privacy/Advertising', ['privacy', 'tips', 'suggestions'], ['power-user'], [10, 11],
                    'Disable Windows Tips', 'Disable getting tips and suggestions when using Windows'),
    'WindowsWelcomeExperience': ('Privacy/Advertising', ['privacy', 'welcome', 'post-update'], ['power-user'], [10, 11],
                                 'Disable Welcome Experience', 'Disable Windows welcome experiences after updates'),
    'XboxGameBar': ('Gaming/Xbox', ['gaming', 'xbox', 'game-bar'], ['power-user'], [10, 11],
                    'Disable Xbox Game Bar', 'Disable Xbox Game Bar and related features'),
    'XboxGameTips': ('Gaming/Xbox', ['gaming', 'xbox', 'game-tips'], ['power-user'], [10, 11],
                     'Disable Xbox Game Tips', 'Disable Xbox Game Bar tips and notifications'),
    # Additional functions from the skipped list
    'PrtScnSnippingTool': ('Input/Keyboard', ['keyboard', 'print-screen', 'snipping-tool', 'screenshot'], ['power-user'], [10, 11],
                           'PrintScreen Opens Snipping Tool', 'Map the Print Screen key to open Snipping Tool'),
    'F1HelpPage': ('Input/Keyboard', ['keyboard', 'f1', 'help', 'disable'], ['power-user'], [10, 11],
                   'Disable F1 Help Key', 'Disable the F1 help key from opening Bing search'),
    'ErrorReporting': ('Privacy/Telemetry', ['privacy', 'error-reporting', 'telemetry'], ['power-user'], [10, 11],
                       'Disable Error Reporting', 'Disable Windows Error Reporting'),
    'WindowsAI': ('Privacy/AI', ['privacy', 'ai', 'recall', 'copilot'], ['power-user'], [11],
                  'Disable Windows AI', 'Disable Windows AI features including Recall'),
    'CapsLock': ('Input/Keyboard', ['keyboard', 'capslock', 'remap'], ['power-user'], [10, 11],
                 'Disable Caps Lock', 'Disable the Caps Lock key'),
    'EditWithClipchampContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'clipchamp'], ['power-user'], [11],
                                 'Remove Clipchamp Context Menu', 'Remove Edit with Clipchamp from context menu'),
    'EditWithPaintContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'paint'], ['power-user'], [11],
                              'Remove Paint Context Menu', 'Remove Edit with Paint from image context menu'),
    'EditWithPhotosContext': ('Explorer/Context Menu', ['explorer', 'context-menu', 'photos'], ['power-user'], [11],
                               'Remove Photos Context Menu', 'Remove Edit with Photos from image context menu'),
    'StickyShift': ('Accessibility/Keyboard', ['accessibility', 'keyboard', 'sticky-shift'], ['power-user'], [10, 11],
                    'Disable Sticky Shift Shortcut', 'Disable the Sticky Keys prompt from pressing Shift 5 times'),
    'NetworkDiscovery': ('Networking/Discovery', ['networking', 'discovery', 'sharing'], ['power-user'], [10, 11],
                          'Enable Network Discovery', 'Enable Network Discovery and File Sharing'),
    'SigninInfo': ('Privacy/Logon', ['privacy', 'sign-in', 'auto-finish'], ['power-user'], [10, 11],
                   'Disable Sign-in Auto Setup', 'Disable using sign-in info to auto-finish setup after an update'),
    'RecycleBinDeleteConfirmation': ('Explorer/Behavior', ['explorer', 'recycle-bin', 'confirmation'], ['power-user'], [10, 11],
                                     'Enable Delete Confirmation', 'Show delete confirmation dialog for Recycle Bin'),
}


def convert_path(p):
    p = p.replace(':\\', '\\').strip('"')
    # Convert PowerShell registry provider paths
    p = p.replace('Registry\\HKEY_CLASSES_ROOT', 'HKCR')
    p = p.replace('Registry::HKEY_CLASSES_ROOT', 'HKCR')
    return p


def parse_function_registry(func_body, func_name):
    """Extract registry entries from the 'desired' parameter branch."""
    # Find parameter blocks - look for the first switch block (Enable/Disable/Show/Hide)
    # The "desired" state varies by function - for "Disable*" functions it's the Disable block
    # For most Sophia functions, the first parameter is the "tweaked" state

    # Split by parameter switch blocks
    param_blocks = re.split(r'\$(\w+)\s*\{', func_body)

    entries = []
    seen = set()

    # Collect all New-ItemProperty calls with their context
    for reg_match in re.finditer(
        r'New-ItemProperty\s+-Path\s+"?([^"\n]+?)"?\s+-Name\s+"?([^"\n]+?)"?\s+'
        r'-(?:PropertyType|Type)\s+(\w+)\s+-Value\s+"?([^"\s]+?)"?\s+-Force',
        func_body
    ):
        rpath = convert_path(reg_match.group(1).strip())
        rname = reg_match.group(2).strip().strip('"')
        rtype = reg_match.group(3).lower()
        rval = reg_match.group(4).strip().strip('"')

        # Skip variable values and PowerShell expressions
        if rval.startswith('$') and rval not in ('$true', '$false'):
            continue
        if rval.startswith('(') or rval.startswith('@'):
            continue

        key = (rpath, rname)
        if key not in seen:
            seen.add(key)
            try:
                val = int(rval)
            except (ValueError, TypeError):
                val = rval
            entries.append({
                'path': rpath,
                'name': rname,
                'type': rtype,
                'value': val,
            })

    return entries


def format_value(v):
    if v is None:
        return 'null'
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        if v == '':
            return '""'
        # Use single quotes for values with backslashes to avoid YAML escape issues
        if '\\' in v:
            return "'%s'" % v.replace("'", "''")
        if any(c in v for c in ':{}[],"\'&#*?|-><!%@`'):
            return '"%s"' % v.replace('"', '\\"')
        return v
    return str(v)


# Parse functions
func_pattern = re.compile(
    r'<#\s*\n(.*?)\n\s*#>\s*\n\s*function\s+(\w+)\s*\n(.*?)(?=\n<#\s*\n|\n#region\s|\Z)',
    re.DOTALL
)

outdir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'catalog', 'tweaks')
generated = []
skipped_existing = []
skipped_no_meta = []

for match in func_pattern.finditer(content):
    func_name = match.group(2)
    func_body = match.group(3)

    if func_name in skip_functions:
        skipped_existing.append(func_name)
        continue

    meta = sophia_meta.get(func_name)
    if not meta:
        skipped_no_meta.append(func_name)
        continue

    category, tags, profiles, versions, name, description = meta

    # Parse registry entries (take first occurrence of each path+name pair)
    reg_entries = parse_function_registry(func_body, func_name)
    if not reg_entries:
        continue

    slug = slugify(name)
    top_cat = category.split('/')[0].lower().replace(' ', '-')
    cat_dir = os.path.join(outdir, top_cat)
    os.makedirs(cat_dir, exist_ok=True)

    filepath = os.path.join(cat_dir, slug + '.yaml')

    lines = []
    lines.append('type: tweak')
    lines.append('name: %s' % format_value(name))
    lines.append('category: %s' % category)
    lines.append('tags: [%s]' % ', '.join(tags))
    lines.append('description: "%s"' % description.replace('"', '\\"'))
    lines.append('reversible: true')
    lines.append('profiles: [%s]' % ', '.join(profiles))
    lines.append('windows-versions: [%s]' % ', '.join(str(v) for v in versions))
    lines.append('source: sophia-script')
    lines.append('registry:')

    for entry in reg_entries:
        lines.append('  - key: %s' % entry['path'])
        lines.append('    name: %s' % format_value(entry['name']))
        lines.append('    value: %s' % format_value(entry['value']))
        lines.append('    type: %s' % entry['type'])
        lines.append('    default-value: null')

    lines.append('')

    with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines))
    generated.append(slug)

print('Generated %d files:' % len(generated))
for s in sorted(generated):
    print('  %s' % s)

if skipped_existing:
    print('\nSkipped (existing/overlap): %d' % len(skipped_existing))
if skipped_no_meta:
    print('Skipped (no metadata defined): %s' % ', '.join(sorted(skipped_no_meta)))
