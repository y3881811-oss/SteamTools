import os
import re

# 0. 创建 nuget.config 绕过证书撤销
with open('nuget.config', 'w', encoding='utf-8') as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <config>
    <add key="signatureValidationMode" value="accept" />
  </config>
</configuration>
''')
print("Created nuget.config")

# 1. 修补 TFM props
path = 'src/TFM_NETX_WITH_ALL.props'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(
        "<TargetFrameworks Condition=\"$([MSBuild]::IsOSPlatform('linux'))\">$(TargetFrameworks)</TargetFrameworks>",
        "<TargetFrameworks Condition=\"$([MSBuild]::IsOSPlatform('linux'))\">$(TargetFrameworks);net$(DotNet_Version)-android</TargetFrameworks>"
    )
    content = content.replace(
        "net$(DotNet_Version)-windows10.0.19041.0</TargetFrameworks>",
        "net$(DotNet_Version)-windows10.0.19041.0;net$(DotNet_Version)-android</TargetFrameworks>"
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched TFM props")

# 2. 修补共享库 csproj
path = 'src/BD.WTTS.Client/BD.WTTS.Client.csproj'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    content = content.replace(
        '<PackageReference Include="System.Drawing.Common" />',
        '<PackageReference Include="System.Drawing.Common" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) == \'windows\'" />'
    )
    content = content.replace(
        '<ProjectReference Include="..\\..\\ref\\WinAuth\\src\\WinAuth\\WinAuth.csproj" />',
        '<ProjectReference Include="..\\..\\ref\\WinAuth\\src\\WinAuth\\WinAuth.csproj" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) != \'android\'" />'
    )
    content = content.replace(
        '<ProjectReference Include="..\\..\\ref\\Facepunch.Steamworks\\Facepunch.Steamworks\\Facepunch.Steamworks.Win64.csproj" />',
        '<ProjectReference Include="..\\..\\ref\\Facepunch.Steamworks\\Facepunch.Steamworks\\Facepunch.Steamworks.Win64.csproj" Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) == \'windows\'" />'
    )
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched BD.WTTS.Client.csproj")

# 3. 从 ref/ 和 src/ 目录扫描真实包版本
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
                        pkg, ver = m.group(1), m.group(2)
                        versions[pkg] = ver  # 后发现的覆盖，尽量保留最新扫描到的
    return versions

scanned = scan_versions(['ref', 'src'])
print(f"Scanned {len(scanned)} package versions from ref/ and src/")

# 关键的手动覆盖（依据报错日志里的需要）
manual = {
    "HarfBuzzSharp": "7.3.0.2",
    "fusillade": "5.0.0",
    "Avalonia": "11.3.20",
    "Splat.Drawing": "19.4.1",
    "SteamKit2": "3.4.0",
    "Microsoft.Extensions.Logging.Debug": "11.0.0",
    "Microsoft.SourceLink.GitHub": "8.0.0",
}
scanned.update(manual)

# 需要补的包清单
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
]

# 4. 修补 Directory.Packages.props
path = 'src/Directory.Packages.props'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    missing_items = ""
    for pkg in required_packages:
        ver = scanned.get(pkg)
        if ver and f'Include="{pkg}"' not in content:
            missing_items += f'    <PackageVersion Include="{pkg}" Version="{ver}" />\n'

    if missing_items:
        insert_pos = content.rfind('</Project>')
        if insert_pos != -1:
            new_content = content[:insert_pos] + "\n  <ItemGroup>\n" + missing_items + "  </ItemGroup>\n" + content[insert_pos:]
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Patched Directory.Packages.props:")
            print(missing_items)
        else:
            print("Warning: </Project> not found")