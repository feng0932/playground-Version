param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

$RepoName = if ($env:REPO_NAME) { $env:REPO_NAME } else { "playground-Version" }
$RepoBranch = if ($env:REPO_BRANCH) { $env:REPO_BRANCH } else { "main" }
$RepoWebBaseUrl = if ($env:REPO_WEB_BASE_URL) { $env:REPO_WEB_BASE_URL } else { "http://192.168.1.152/yuhua/playground-Version" }
$RepoWebBaseUrl = $RepoWebBaseUrl.TrimEnd("/")
$DefaultStableReleaseUrl = "$RepoWebBaseUrl/raw/branch/$RepoBranch/stable-release.json"

$InstallBase = Join-Path $HOME ".ai-team"
$BinDir = Join-Path $InstallBase "bin"
$ReleasesDir = Join-Path $InstallBase "releases"
$LauncherPath = Join-Path $BinDir "ai-team.cmd"
$StateDir = Join-Path $InstallBase "state"
$MachineStatePath = Join-Path $StateDir "machine-install.json"
$InstallHistoryPath = Join-Path $StateDir "install-history.jsonl"

if ($env:AI_TEAM_RELEASE_METADATA_URL) {
    $ReleaseMetadataUrl = $env:AI_TEAM_RELEASE_METADATA_URL
} elseif (-not [string]::IsNullOrWhiteSpace($Version)) {
    $Tag = "ai-team-bundle-$Version"
    $ReleaseMetadataUrl = "$RepoWebBaseUrl/raw/branch/$RepoBranch/releases/$Version/$Tag.release.json"
} else {
    $ReleaseMetadataUrl = if ($env:AI_TEAM_STABLE_RELEASE_URL) { $env:AI_TEAM_STABLE_RELEASE_URL } else { $DefaultStableReleaseUrl }
}

New-Item -ItemType Directory -Force -Path $BinDir, $ReleasesDir, $StateDir | Out-Null
$TempReleaseMetadataPath = Join-Path $InstallBase ([System.IO.Path]::GetRandomFileName() + ".json")

Invoke-WebRequest -Uri $ReleaseMetadataUrl -OutFile $TempReleaseMetadataPath
$ReleaseMetadata = Get-Content -Raw $TempReleaseMetadataPath | ConvertFrom-Json
$Tag = $ReleaseMetadata.tag
$ResolvedVersion = $ReleaseMetadata.bundle_version
$TargetDir = Join-Path $ReleasesDir $Tag
$ReleaseMetadataPath = Join-Path $TargetDir "$Tag.release.json"
$ArchivePath = Join-Path $TargetDir "$Tag.tar.gz"
$ExtractRoot = Join-Path $TargetDir "source"
$ArchiveDirName = "$RepoName-$Tag"
$EntrypointPath = Join-Path $ExtractRoot "$ArchiveDirName\ai_team_installer.py"

New-Item -ItemType Directory -Force -Path $TargetDir, $ExtractRoot | Out-Null
if (Test-Path $ArchivePath) { Remove-Item $ArchivePath -Force }
if (Test-Path $ReleaseMetadataPath) { Remove-Item $ReleaseMetadataPath -Force }
if (Test-Path $ExtractRoot) {
    Get-ChildItem -Force $ExtractRoot | Remove-Item -Recurse -Force
}
Move-Item -Path $TempReleaseMetadataPath -Destination $ReleaseMetadataPath -Force

$ArchiveUrl = $ReleaseMetadata.installer_archive_url
$ExpectedArchiveSha256 = $ReleaseMetadata.installer_archive_sha256
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ArchivePath
$ActualArchiveSha256 = (Get-FileHash -Algorithm SHA256 -Path $ArchivePath).Hash.ToLowerInvariant()
if ($ActualArchiveSha256 -ne $ExpectedArchiveSha256.ToLowerInvariant()) {
    throw "checksum mismatch: expected $ExpectedArchiveSha256, got $ActualArchiveSha256"
}
tar -xzf "$ArchivePath" -C "$ExtractRoot"

@"
@echo off
set "AI_TEAM_RELEASE_METADATA_PATH=$ReleaseMetadataPath"
python "$EntrypointPath" %*
"@ | Set-Content -Path $LauncherPath -Encoding ascii

$Snapshot = [ordered]@{
    schema_version = 1
    installed_at = [DateTimeOffset]::UtcNow.ToString("o")
    bundle_version = $ReleaseMetadata.bundle_version
    bundle_source = $ReleaseMetadata.bundle_source
    release_tag = $ReleaseMetadata.tag
    install_source = $ReleaseMetadataUrl
    release_metadata_url = $ReleaseMetadataUrl
    release_metadata_path = $ReleaseMetadataPath
    installer_archive_url = $ReleaseMetadata.installer_archive_url
    installer_archive_sha256 = $ReleaseMetadata.installer_archive_sha256
}
if (Test-Path $MachineStatePath) {
    $PreviousSnapshot = Get-Content -Raw $MachineStatePath | ConvertFrom-Json
    if ($PreviousSnapshot.bundle_version) {
        $Snapshot["previous_bundle_version"] = $PreviousSnapshot.bundle_version
    }
}
[System.IO.File]::WriteAllText(
    $MachineStatePath,
    (($Snapshot | ConvertTo-Json) + [Environment]::NewLine),
    $Utf8NoBom
)
[System.IO.File]::AppendAllText(
    $InstallHistoryPath,
    (($Snapshot | ConvertTo-Json -Compress) + [Environment]::NewLine),
    $Utf8NoBom
)

$CurrentUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ([string]::IsNullOrWhiteSpace($CurrentUserPath)) {
    [Environment]::SetEnvironmentVariable("Path", $BinDir, "User")
} elseif (-not ($CurrentUserPath -split ';' | Where-Object { $_ -eq $BinDir })) {
    [Environment]::SetEnvironmentVariable("Path", "$BinDir;$CurrentUserPath", "User")
}

Write-Host "installed ai-team launcher:"
Write-Host "- version: $ResolvedVersion"
Write-Host "- release metadata: $ReleaseMetadataUrl"
Write-Host "- archive: $ArchiveUrl"
Write-Host "- launcher: $LauncherPath"
Write-Host ""
Write-Host "user PATH updated with $HOME\.ai-team\bin"
Write-Host "restart PowerShell, then run:"
Write-Host "  ai-team install"
