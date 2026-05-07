param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = $Utf8NoBom
[Console]::InputEncoding = $Utf8NoBom
$OutputEncoding = $Utf8NoBom

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
$LogPath = Join-Path $StateDir "install-ai-team-bootstrap.log"
$HumanOutputDone = $false
$ProgressPreference = "SilentlyContinue"

function Write-HumanFailure {
    param(
        [string]$Category,
        [string]$Reason,
        [string]$NextStep
    )
    $script:HumanOutputDone = $true
    Write-Host "安装未完成：$Category"
    Write-Host "原因：$Reason"
    Write-Host "下一步：$NextStep"
    Write-Host "日志：$LogPath"
}

function Write-HumanSuccess {
    $script:HumanOutputDone = $true
    Write-Host "安装完成：ai-team $ResolvedVersion 已接入当前项目。"
    Write-Host "下一步：在项目根目录打开 Codex，输入："
    Write-Host "/总控 请接管当前项目，并授权派发子agent"
    Write-Host "日志：$LogPath"
}

try {

if ($env:AI_TEAM_RELEASE_METADATA_URL) {
    $ReleaseMetadataUrl = $env:AI_TEAM_RELEASE_METADATA_URL
} elseif (-not [string]::IsNullOrWhiteSpace($Version)) {
    $Tag = "ai-team-bundle-$Version"
    $ReleaseMetadataUrl = "$RepoWebBaseUrl/raw/branch/$RepoBranch/releases/$Version/$Tag.release.json"
} else {
    $ReleaseMetadataUrl = if ($env:AI_TEAM_STABLE_RELEASE_URL) { $env:AI_TEAM_STABLE_RELEASE_URL } else { $DefaultStableReleaseUrl }
}

New-Item -ItemType Directory -Force -Path $BinDir, $ReleasesDir, $StateDir | Out-Null
"" | Set-Content -Path $LogPath -Encoding utf8
$TempReleaseMetadataPath = Join-Path $InstallBase ([System.IO.Path]::GetRandomFileName() + ".json")

Invoke-WebRequest -Uri $ReleaseMetadataUrl -OutFile $TempReleaseMetadataPath
$ReleaseMetadata = Get-Content -Raw $TempReleaseMetadataPath | ConvertFrom-Json
$Tag = $ReleaseMetadata.tag
$ResolvedVersion = $ReleaseMetadata.bundle_version
$ReleaseStatusUrl = "$RepoWebBaseUrl/raw/branch/$RepoBranch/releases/$ResolvedVersion/release-status.json"
$TempReleaseStatusPath = Join-Path $InstallBase ([System.IO.Path]::GetRandomFileName() + ".release-status.json")
try {
    Invoke-WebRequest -Uri $ReleaseStatusUrl -OutFile $TempReleaseStatusPath
    $ReleaseStatus = Get-Content -Raw $TempReleaseStatusPath | ConvertFrom-Json
    if (($ReleaseStatus.default_install_allowed -eq $false) -or ($ReleaseStatus.release_status -eq "postrelease_failed")) {
        Write-HumanFailure `
            -Category "release_quarantined" `
            -Reason "该版本发布后现场失败，不能作为默认安装版本。" `
            -NextStep "使用默认 stable 入口安装回退版本，或等待下一热修版本。"
        exit 1
    }
} catch {
} finally {
    if (Test-Path $TempReleaseStatusPath) { Remove-Item $TempReleaseStatusPath -Force }
}
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

Write-HumanSuccess
} catch {
    if (-not $HumanOutputDone) {
        $Message = $_.Exception.Message
        Add-Content -Path $LogPath -Value $Message -Encoding utf8
        Write-HumanFailure `
            -Category "bootstrap_failed" `
            -Reason "安装入口执行失败，详细错误已写入日志。" `
            -NextStep "检查网络、权限和发布入口后重试。"
    }
    exit 1
}
