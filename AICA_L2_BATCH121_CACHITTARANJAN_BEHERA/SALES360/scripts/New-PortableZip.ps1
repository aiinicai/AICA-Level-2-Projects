# Writes a release ZIP the way Windows and other unzip tools expect it:
# forward-slash entry names, folder entries, and no Python bytecode caches.
# [IO.Compression.ZipFile]::CreateFromDirectory writes backslash names with no folder entries,
# which breaks extraction. The bundle inventory excludes .pyc/.pyo and __pycache__, so the ZIP does too.
function New-PortableZip {
    param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Destination)
    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $Destination) { throw "ZIP already exists: $Destination" }
    $root = (Resolve-Path -LiteralPath $Source).ProviderPath.TrimEnd('\')
    $excluded = {
        param($relative)
        if ([IO.Path]::GetExtension($relative) -in '.pyc', '.pyo') { return $true }
        return (($relative -split '\\') -contains '__pycache__')
    }
    $archive = [IO.Compression.ZipFile]::Open($Destination, [IO.Compression.ZipArchiveMode]::Create)
    try {
        foreach ($dir in Get-ChildItem -LiteralPath $root -Recurse -Directory) {
            $relative = $dir.FullName.Substring($root.Length + 1)
            if (-not (& $excluded $relative)) { $archive.CreateEntry(($relative -replace '\\', '/') + '/') | Out-Null }
        }
        foreach ($file in Get-ChildItem -LiteralPath $root -Recurse -File) {
            $relative = $file.FullName.Substring($root.Length + 1)
            if (& $excluded $relative) { continue }
            $entry = $archive.CreateEntry(($relative -replace '\\', '/'), [IO.Compression.CompressionLevel]::Optimal)
            $in = [IO.File]::OpenRead($file.FullName)
            try {
                $out = $entry.Open()
                try { $in.CopyTo($out) } finally { $out.Dispose() }
            } finally { $in.Dispose() }
        }
    } finally { $archive.Dispose() }
}
