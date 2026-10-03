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

# ★ 自动收敛扫描：找出所有需要从 Android 编译中排除的 .cs 文件
CLIENT_ROOT = 'src/BD.WTTS.Client'

# SkiaSharp 3.x 移除/改动的 API 关键词
SKIA_KEYWORDS = [
    'SKFontManager', 'SKTypeface', 'SKEncodedImageFormat', 'SKBitmap',
    'SKCanvas', 'SKColorType', 'SKImage', 'SKPaint', 'SKPath', 'SKSurface',
    'SKData', 'SKCodec', 'SKStream',
]

# 直接被排除文件里定义的类型（初始种子）
EXCLUDED_TYPES = ['IFontManager', 'IcoEncoder', 'QRCodeHelper']

# 已经确认有问题的种子文件
SEED_FILES = [
    'Helpers/UI/QRCodeHelper.Net.Codecrete.QrCodeGenerator.SkiaSharp.cs',
    'Helpers/UI/QRCodeHelper.Net.Codecrete.QrCodeGenerator.cs',
    'Helpers/IcoEncoder.cs',
    'Services/Platform/IPlatformService.Font.cs',
    'Services/UI/IFontManager.cs',
    'Services.Implementation/UI/FontManagerImpl.cs',
]

def file_contains_any(filepath, keywords):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False
    for kw in keywords:
        if kw in content:
            return True
    return False

def extract_public_types(filepath):
    types = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return types
    for m in re.finditer(
        r'\b(?:public|internal)\s+(?:sealed\s+|abstract\s+|partial\s+|static\s+)?(?:class|interface|struct|enum|record)\s+(\w+)',
        content
    ):
        types.add(m.group(1))
    return types

# 迭代扫描
excluded_set = set(SEED_FILES)
excluded_types = set(EXCLUDED_TYPES)
max_iter = 15

for iteration in range(max_iter):
    new_additions = set()

    for dirpath, dirnames, filenames in os.walk(CLIENT_ROOT):
        for fn in filenames:
            if not fn.endswith('.cs'):
                continue
            fp = os.path.join(dirpath, fn)
            rel = os.path.relpath(fp, CLIENT_ROOT).replace('\\', '/')

            if rel in excluded_set:
                continue

            # 判断是否包含 SkiaSharp 相关关键词
            has_skia = file_contains_any(fp, SKIA_KEYWORDS)
            # 判断是否引用了被排除文件里的类型
            has_excluded_type = False
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    content = f.read()
                for t in excluded_types:
                    if re.search(rf'\b{re.escape(t)}\b', content):
                        has_excluded_type = True
                        break
            except Exception:
                pass

            if has_skia or has_excluded_type:
                new_additions.add(rel)

    if not new_additions:
        print(f"Converged after {iteration} iterations")
        break

    # 提取新加入文件的 public 类型，扩大下一轮扫描的种子
    for rel in new_additions:
        fp = os.path.join(CLIENT_ROOT, rel)
        excluded_types.update(extract_public_types(fp))

    excluded_set.update(new_additions)
    print(f"Iteration {iteration}: added {len(new_additions)} files")

print(f"\nTotal excluded files: {len(excluded_set)}")
for f in sorted(excluded_set):
    print(f"  - {f}")

# 2. 共享库 csproj
path = f'{CLIENT_ROOT}/BD.WTTS.Client.csproj'
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

    # 移除旧的排除块（如果存在），重新生成
    c = re.sub(
        r'\n  <ItemGroup Condition="\$\(\[MSBuild\]::GetTargetPlatformIdentifier\(\'\$\(TargetFramework\)\'\)\) == \'android\'">\n    <!-- EXCLUDE_ANDROID_SKIA -->.*?</ItemGroup>\n',
        '\n',
        c,
        flags=re.DOTALL
    )

    # 生成新的排除块
    exclude_lines = []
    for rel in sorted(excluded_set):
        exclude_lines.append(f'    <Compile Remove="{rel}" />')

    exclude_block = (
        '\n  <ItemGroup Condition="$([MSBuild]::GetTargetPlatformIdentifier(\'$(TargetFramework)\')) == \'android\'">\n'
        '    <!-- EXCLUDE_ANDROID_SKIA -->\n'
        + '\n'.join(exclude_lines) + '\n'
        '  </ItemGroup>\n'
    )

    c = c.replace('</Project>', exclude_block + '</Project>')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print("Patched BD.WTTS.Client.csproj with auto-exclusion")

# 3. Splat 版本强制改写
SPLAT_PKGS = ['Splat', 'Splat.Core', 'Splat.Builder', 'Splat.Logging', 'Splat.Drawing']
SPLAT_TARGET = '19.4.1'

def force_rewrite_splat(root_dirs):
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

force_rewrite_splat(['ref', 'src'])
print("Splat versions forced")

# 4. 扫描版本 + 补 Directory.Packages.props
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

# 5. SKColorType 修复
REPLACEMENTS = {
    'SKColorType.Argb4444': '(SKColorType)4',
    'SKColorType.Rgba8888': '(SKColorType)4',
    'SKColorType.Bgra8888': '(SKColorType)6',
}

def fix_skcolortype(root_dirs):
    for root_dir in root_dirs:
        if not os.path.exists(root_dir):
            continue
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for fn in filenames:
                if not fn.endswith('.cs'):
                    continue
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8') as f:
                        c = f.read()
                except Exception:
                    continue
                original = c
                for k, v in REPLACEMENTS.items():
                    c = c.replace(k, v)
                if c != original:
                    with open(fp, 'w', encoding='utf-8') as f:
                        f.write(c)

fix_skcolortype(['src', 'ref'])
print("Done")