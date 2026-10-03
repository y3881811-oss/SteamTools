import os
import re

# 0. nuget.config
with open('nuget.config', 'w', encoding='utf-8') as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <config>
    <add key="signatureValidationMode" value="accept" />
  </config>
</configuration>
''')

# 1. TFM props
path = 'src/TFM_NETX_WITH_ALL.props'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace(
        "<TargetFrameworks Condition=\"$([MSBuild]::IsOSPlatform('linux'))\">$(TargetFrameworks)</TargetFrameworks>",
        "<TargetFrameworks Condition=\"$([MSBuild]::IsOSPlatform('linux'))\">$(TargetFrameworks);net$(DotNet_Version)-android</TargetFrameworks>"
    )
    c = c.replace(
        "net$(DotNet_Version)-windows10.0.19041.0</TargetFrameworks>",
        "net$(DotNet_Version)-windows10.0.19041.0;net$(DotNet_Version)-android</TargetFrameworks>"
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Patched TFM props")

# 2. 共享库 csproj
path = 'src/BD.WTTS.Client/BD.WTTS.Client.csproj'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace(
        '<PackageReference Include="System.Drawing.Common" />',
        '<PackageReference Include="System.Drawing.Common" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) == \'windows\'" />'
    )
    c = c.replace(
        '<ProjectReference Include="..\\..\\ref\\WinAuth\\src\\WinAuth\\WinAuth.csproj" />',
        '<ProjectReference Include="..\\..\\ref\\WinAuth\\src\\WinAuth\\WinAuth.csproj" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) != \'android\'" />'
    )
    c = c.replace(
        '<ProjectReference Include="..\\..\\ref\\Facepunch.Steamworks\\Facepunch.Steamworks\\Facepunch.Steamworks.Win64.csproj" />',
        '<ProjectReference Include="..\\..\\ref\\Facepunch.Steamworks\\Facepunch.Steamworks\\Facepunch.Steamworks.Win64.csproj" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) == \'windows\'" />'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Patched BD.WTTS.Client.csproj")

# 3. Splat 版本强制改写
SPLAT_PKGS = ['Splat', 'Splat.Core', 'Splat.Builder', 'Splat.Logging', 'Splat.Drawing']
SPLAT_TARGET = '19.4.1'

def force_rewrite_splat(root_dirs):
    changed = 0
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fn in filenames:
                if fn.endswith('.csproj') or fn == 'Directory.Packages.props':
                    fp = os.path.join(dirpath, fn)
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            content = f.read()
                    except Exception:
                        continue
                    original = content
                    for pkg in SPLAT_PKGS:
                        content = re.sub(
                            rf'(<(?:PackageReference|PackageVersion)\s+Include="{re.escape(pkg)}"[^>]*?Version=")[^"]+(")',
                            rf'\g<1>{SPLAT_TARGET}\g<2>', content)
                        content = re.sub(
                            rf'(<(?:PackageReference|PackageVersion)\s+Version=")[^"]+("[^>]*?Include="{re.escape(pkg)}")',
                            rf'\g<1>{SPLAT_TARGET}\g<2>', content)
                    if content != original:
                        with open(fp, 'w', encoding='utf-8') as f:
                            f.write(content)
                        changed += 1
    return changed

force_rewrite_splat(['ref', 'src'])
print("Splat versions forced to 19.4.1")

# 4. 扫描版本号并补 Directory.Packages.props
def scan_versions(root_dirs):
    versions = {}
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fn in filenames:
                if fn.endswith('.csproj') or fn == 'Directory.Packages.props':
                    fp = os.path.join(dirpath, fn)
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            c = f.read()
                    except Exception:
                        continue
                    for m in re.finditer(
                        r'<(?:PackageReference|PackageVersion)\s+Include="([^"]+)"\s+Version="([^"]+)"',
                        c
                    ):
                        versions[m.group(1)] = m.group(2)
    return versions

scanned = scan_versions(['ref', 'src'])
scanned.update({
    "HarfBuzzSharp": "7.3.0.2",
    "fusillade": "5.0.0",
    "Avalonia": "11.3.20",
    "SteamKit2": "3.4.0",
    "Microsoft.Extensions.Logging.Debug": "11.0.0",
    "Microsoft.SourceLink.GitHub": "8.0.0",
})

required_packages = [
    "AutoMapper", "SharpZipLib", "NLog", "NLog.Extensions.Logging",
    "Net.Codecrete.QrCodeGenerator", "Fleck", "Stun.Net", "System.Linq.Async",
    "ReactiveUI.Fody", "fusillade", "Splat.Drawing",
    "Microsoft.Extensions.FileProviders.Physical", "Microsoft.Bcl.AsyncInterfaces",
    "SkiaSharp", "SkiaSharp.HarfBuzz", "HarfBuzzSharp", "Utf8StringInterpolation",
    "System.Composition", "System.CommandLine", "SteamKit2",
    "Microsoft.Extensions.Logging.Console", "Avalonia",
    "HarfBuzzSharp.NativeAssets.Linux", "SkiaSharp.NativeAssets.Linux",
    "Microsoft.Extensions.Logging.Debug", "Microsoft.SourceLink.GitHub",
    "Splat", "Splat.Core", "Splat.Builder", "Splat.Logging",
]

path = 'src/Directory.Packages.props'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    missing = ""
    for pkg in required_packages:
        ver = scanned.get(pkg)
        if ver and f'Include="{pkg}"' not in c:
            missing += f'    <PackageVersion Include="{pkg}" Version="{ver}" />\n'
    if missing:
        pos = c.rfind('</Project>')
        if pos != -1:
            c = c[:pos] + "\n  <ItemGroup>\n" + missing + "  </ItemGroup>\n" + c[pos:]
            with open(path, 'w', encoding='utf-8') as f:
                f.write(c)
            print("Patched Directory.Packages.props")

# 5. ★ 新增：修复 SKColorType.Argb4444 在 Android 上不存在的问题
target_file = 'src/BD.WTTS.Client/Helpers/UI/QRCodeHelper.Net.Codecrete.QrCodeGenerator.SkiaSharp.cs'
if os.path.exists(target_file):
    with open(target_file, 'r', encoding='utf-8') as f:
        c = f.read()
    original = c
    # Argb4444 在 Android 的 SkiaSharp 里没有，换成跨平台都有的 Rgba8888
    c = c.replace('SKColorType.Argb4444', 'SKColorType.Rgba8888')
    if c != original:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(c)
        print("Fixed SKColorType.Argb4444 -> Rgba8888")
    else:
        print("WARN: Argb4444 not found in QRCodeHelper, trying global scan...")
        # 兜底：整个 src/ 目录全局替换
        for dirpath, dirnames, filenames in os.walk('src'):
            for fn in filenames:
                if fn.endswith('.cs'):
                    fp = os.path.join(dirpath, fn)
                    try:
                        with open(fp, 'r', encoding='utf-8') as f:
                            cc = f.read()
                    except Exception:
                        continue
                    if 'SKColorType.Argb4444' in cc:
                        cc = cc.replace('SKColorType.Argb4444', 'SKColorType.Rgba8888')
                        with open(fp, 'w', encoding='utf-8') as f:
                            f.write(cc)
                        print(f"  Fixed in {fp}")
else:
    print(f"WARN: {target_file} not found, doing global scan...")
    for dirpath, dirnames, filenames in os.walk('src'):
        for fn in filenames:
            if fn.endswith('.cs'):
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        cc = f.read()
                except Exception:
                    continue
                if 'SKColorType.Argb4444' in cc:
                    cc = cc.replace('SKColorType.Argb4444', 'SKColorType.Rgba8888')
                    with open(fp, 'w', encoding='utf-8') as f:
                        f.write(cc)
                    print(f"  Fixed in {fp}")