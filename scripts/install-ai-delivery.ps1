[CmdletBinding()]
param(
  [string]$Version = $env:AI_DELIVERY_VERSION,
  [string]$Repo = $env:AI_DELIVERY_REPO,
  [string]$InstallDir = $env:AI_DELIVERY_INSTALL_DIR,
  [string]$DownloadBaseUrl = $env:AI_DELIVERY_DOWNLOAD_BASE_URL,
  [string]$InitTargetRepo = $env:AI_DELIVERY_INIT_TARGET_REPO,
  [string]$UpgradeInitTargetRepo = $env:AI_DELIVERY_UPGRADE_INIT_TARGET_REPO
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
  $Version = "latest"
}

if ([string]::IsNullOrWhiteSpace($Repo)) {
  $Repo = "s-charvin/ai-delivery-kit"
}

if ([string]::IsNullOrWhiteSpace($InstallDir)) {
  $InstallDir = Join-Path $HOME ".local/bin"
}

$script:ReleaseMetadata = $null

function Write-Log {
  param([string]$Message)
  Write-Host "[install-ai-delivery] $Message"
}

function Get-ReleaseBaseUrl {
  if (-not [string]::IsNullOrWhiteSpace($DownloadBaseUrl)) {
    return $DownloadBaseUrl.TrimEnd('/')
  }

  if ($Version -eq "latest") {
    return "https://github.com/$Repo/releases/latest/download"
  }

  return "https://github.com/$Repo/releases/download/$Version"
}

function Get-GitHubApiBaseUrl {
  return "https://api.github.com/repos/$Repo"
}

function Get-GitHubReleaseApiUrl {
  $apiBaseUrl = Get-GitHubApiBaseUrl
  if ($Version -eq "latest") {
    return "$apiBaseUrl/releases/latest"
  }

  return "$apiBaseUrl/releases/tags/$Version"
}

function Get-ReleaseSourceDescription {
  if (-not [string]::IsNullOrWhiteSpace($DownloadBaseUrl)) {
    return $DownloadBaseUrl.TrimEnd('/')
  }

  if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
    return "GitHub Releases API for $Repo ($Version)"
  }

  return Get-ReleaseBaseUrl
}

function Get-RequestHeaders {
  param([string]$Accept)

  $headers = @{}
  if (-not [string]::IsNullOrWhiteSpace($Accept)) {
    $headers["Accept"] = $Accept
  }
  if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
    $headers["Authorization"] = "Bearer $($env:GITHUB_TOKEN)"
  }
  return $headers
}

function Invoke-Download {
  param(
    [string]$Uri,
    [string]$OutFile,
    [string]$Accept
  )

  $headers = Get-RequestHeaders -Accept $Accept
  if ($headers.Count -gt 0) {
    Invoke-WebRequest -Uri $Uri -OutFile $OutFile -Headers $headers
    return
  }

  Invoke-WebRequest -Uri $Uri -OutFile $OutFile
}

function Get-GitHubReleaseMetadata {
  param([string]$TempDir)

  if ($null -ne $script:ReleaseMetadata) {
    return $script:ReleaseMetadata
  }

  $metadataPath = Join-Path $TempDir "release.json"
  Invoke-Download -Uri (Get-GitHubReleaseApiUrl) -OutFile $metadataPath -Accept "application/vnd.github+json"
  $script:ReleaseMetadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
  return $script:ReleaseMetadata
}

function Get-GitHubReleaseAsset {
  param(
    [string]$TempDir,
    [string]$AssetName
  )

  $releaseMetadata = Get-GitHubReleaseMetadata -TempDir $TempDir
  $asset = @($releaseMetadata.assets | Where-Object { $_.name -eq $AssetName }) | Select-Object -First 1
  if ($null -eq $asset) {
    throw "Could not find release asset $AssetName for $Repo@$Version"
  }

  return $asset
}

function Download-GitHubReleaseAsset {
  param(
    [string]$TempDir,
    [string]$AssetName,
    [string]$OutFile
  )

  $asset = Get-GitHubReleaseAsset -TempDir $TempDir -AssetName $AssetName
  Invoke-Download -Uri "$(Get-GitHubApiBaseUrl)/releases/assets/$($asset.id)" -OutFile $OutFile -Accept "application/octet-stream"
}

function Download-ReleaseAsset {
  param(
    [string]$TempDir,
    [string]$AssetName,
    [string]$OutFile
  )

  if (-not [string]::IsNullOrWhiteSpace($DownloadBaseUrl)) {
    Invoke-Download -Uri "$($DownloadBaseUrl.TrimEnd('/'))/$AssetName" -OutFile $OutFile -Accept ""
    return
  }

  if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_TOKEN)) {
    Download-GitHubReleaseAsset -TempDir $TempDir -AssetName $AssetName -OutFile $OutFile
    return
  }

  Invoke-Download -Uri "$((Get-ReleaseBaseUrl))/$AssetName" -OutFile $OutFile -Accept ""
}

function Get-ArchiveName {
  $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
  switch ($arch) {
    "X64" { return "ai-delivery_windows_amd64.zip" }
    "Arm64" { throw "Windows arm64 releases are not published in v1." }
    default { throw "Unsupported architecture: $arch" }
  }
}

function Get-FileHashValue {
  param([string]$Path)
  return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Verify-Checksum {
  param(
    [string]$ArchivePath,
    [string]$ChecksumsPath
  )

  $archiveName = Split-Path -Leaf $ArchivePath
  $line = Select-String -Path $ChecksumsPath -SimpleMatch "  $archiveName" | Select-Object -First 1
  if ($null -eq $line) {
    Write-Log "No checksum entry found for $archiveName; skipping verification."
    return
  }

  $expected = ($line.Line -split '\s+')[0].ToLowerInvariant()
  $actual = Get-FileHashValue -Path $ArchivePath
  if ($expected -ne $actual) {
    throw "Checksum verification failed for $archiveName"
  }
}

function Invoke-PostInstallInit {
  param([string]$TargetPath)

  if (-not [string]::IsNullOrWhiteSpace($InitTargetRepo) -and -not [string]::IsNullOrWhiteSpace($UpgradeInitTargetRepo)) {
    throw "Use only one of -InitTargetRepo or -UpgradeInitTargetRepo"
  }

  if (-not [string]::IsNullOrWhiteSpace($InitTargetRepo)) {
    Write-Log "Running: $TargetPath init $InitTargetRepo"
    & $TargetPath init $InitTargetRepo
    return
  }

  if (-not [string]::IsNullOrWhiteSpace($UpgradeInitTargetRepo)) {
    Write-Log "Running: $TargetPath init --upgrade $UpgradeInitTargetRepo"
    & $TargetPath init --upgrade $UpgradeInitTargetRepo
  }
}

$archiveName = Get-ArchiveName
$sourceDescription = Get-ReleaseSourceDescription
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
$archivePath = Join-Path $tempDir $archiveName
$checksumsPath = Join-Path $tempDir "checksums.txt"
$extractDir = Join-Path $tempDir "extracted"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

try {
  Write-Log "Downloading $archiveName from $sourceDescription"
  Download-ReleaseAsset -TempDir $tempDir -AssetName $archiveName -OutFile $archivePath

  try {
    Download-ReleaseAsset -TempDir $tempDir -AssetName "checksums.txt" -OutFile $checksumsPath
    Verify-Checksum -ArchivePath $archivePath -ChecksumsPath $checksumsPath
  } catch {
    Write-Log "Could not verify checksums: $($_.Exception.Message)"
  }

  Expand-Archive -LiteralPath $archivePath -DestinationPath $extractDir -Force
  $binaryPath = Get-ChildItem -Path $extractDir -Recurse -Filter "ai-delivery.exe" | Select-Object -First 1
  if ($null -eq $binaryPath) {
    throw "Extracted archive did not contain ai-delivery.exe"
  }

  $targetPath = Join-Path $InstallDir "ai-delivery.exe"
  if (Test-Path -LiteralPath $targetPath) {
    Write-Log "Replacing existing ai-delivery at $targetPath"
  }
  Copy-Item -LiteralPath $binaryPath.FullName -Destination $targetPath -Force

  Write-Log "Installed ai-delivery to $targetPath"
  Write-Log "Add $InstallDir to PATH if needed."
  Write-Log "Run: ai-delivery init C:\path\to\repo"
  Write-Log "Upgrade an existing initialized repo: ai-delivery init --upgrade C:\path\to\repo"
  Write-Log "Upgrade the installed CLI later by rerunning this installer."
  Invoke-PostInstallInit -TargetPath $targetPath
} finally {
  if (Test-Path -LiteralPath $tempDir) {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
  }
}
