import os

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

# 2. 修补共享库 csproj，排除 Android 不支持的引用
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

# 3. 修补 Directory.Packages.props，补全缺失包的版本号
path = 'src/Directory.Packages.props'
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    packages = {
        "AutoMapper": "13.0.1",
        "SharpZipLib": "1.4.2",
        "NLog": "5.3.4",
        "NLog.Extensions.Logging": "5.3.4",
        "Net.Codecrete.QrCodeGenerator": "2.0.5",
        "Fleck": "1.2.0",
        "Stun.Net": "1.0.0",
        "System.Linq.Async": "6.0.1",
        "ReactiveUI.Fody": "19.5.41",
        "fusillade": "2.0.0",
        "Splat.Drawing": "14.4.1",
        "Microsoft.Extensions.FileProviders.Physical": "8.0.0",
        "Microsoft.Bcl.AsyncInterfaces": "8.0.0",
        "SkiaSharp": "2.88.8",
        "SkiaSharp.HarfBuzz": "2.88.8",
        "HarfBuzzSharp": "2.8.2.3",
        "Utf8StringInterpolation": "1.3.0",
        "System.Composition": "8.0.0",
        "System.CommandLine": "2.0.0-beta4.22272.1",
        "SteamKit2": "2.5.0",
        "Microsoft.Extensions.Logging.Console": "8.0.0",
        "Avalonia": "11.0.0",
        "HarfBuzzSharp.NativeAssets.Linux": "2.8.2.3",
        "SkiaSharp.NativeAssets.Linux": "2.88.8"
    }

    missing_items = ""
    for pkg, ver in packages.items():
        if f'Include="{pkg}"' not in content:
            missing_items += f'    <PackageVersion Include="{pkg}" Version="{ver}" />\n'

    if missing_items:
        insert_pos = content.rfind('</Project>')
        if insert_pos != -1:
            new_content = content[:insert_pos] + "\n  <ItemGroup>\n" + missing_items + "  </ItemGroup>\n" + content[insert_pos:]
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("Patched Directory.Packages.props with missing packages")
        else:
            print("Warning: </Project> not found in Directory.Packages.props")
else:
    print("Directory.Packages.props not found, skipping package injection.")