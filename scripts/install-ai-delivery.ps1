[CmdletBinding()]
param(
  [string]$Version = $env:AI_DELIVERY_VERSION,
  [string]$Repo = $env:AI_DELIVERY_REPO,
  [string]$InstallDir = $env:AI_DELIVERY_INSTALL_DIR,
  [string]$DownloadBaseUrl = $env:AI_DELIVERY_DOWNLOAD_BASE_URL
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

$archiveName = Get-ArchiveName
$baseUrl = Get-ReleaseBaseUrl
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
$archivePath = Join-Path $tempDir $archiveName
$checksumsPath = Join-Path $tempDir "checksums.txt"
$extractDir = Join-Path $tempDir "extracted"

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

try {
  Write-Log "Downloading $archiveName from $baseUrl"
  Invoke-WebRequest -Uri "$baseUrl/$archiveName" -OutFile $archivePath

  try {
    Invoke-WebRequest -Uri "$baseUrl/checksums.txt" -OutFile $checksumsPath
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
  Copy-Item -LiteralPath $binaryPath.FullName -Destination $targetPath -Force

  Write-Log "Installed ai-delivery to $targetPath"
  Write-Log "Add $InstallDir to PATH if needed."
  Write-Log "Run: ai-delivery init C:\path\to\repo"
} finally {
  if (Test-Path -LiteralPath $tempDir) {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
  }
}
