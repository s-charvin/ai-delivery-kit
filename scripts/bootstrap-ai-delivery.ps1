[CmdletBinding()]
param(
  [Parameter(Mandatory = $true, Position = 0)]
  [string]$TargetRepo,
  [string]$ProjectId = "",
  [string]$MainBranch = "main",
  [string]$Version = $env:AI_DELIVERY_VERSION,
  [string]$Repo = $env:AI_DELIVERY_REPO,
  [string]$DownloadBaseUrl = $env:AI_DELIVERY_DOWNLOAD_BASE_URL,
  [string]$CommandOverride = $env:AI_DELIVERY_CMD
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($Version)) {
  $Version = "latest"
}

if ([string]::IsNullOrWhiteSpace($Repo)) {
  $Repo = "s-charvin/ai-delivery-kit"
}

function Write-Log {
  param([string]$Message)
  Write-Host "[bootstrap-ai-delivery] $Message"
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

function Invoke-AiDelivery {
  param([string]$Executable)
  & $Executable init $TargetRepo --project-id $ProjectId --main-branch $MainBranch
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

if (-not (Test-Path -LiteralPath $TargetRepo -PathType Container)) {
  throw "Target repository directory does not exist: $TargetRepo"
}

if (-not [string]::IsNullOrWhiteSpace($CommandOverride)) {
  Write-Log "Using local ai-delivery command override"
  Invoke-AiDelivery -Executable $CommandOverride
  exit $LASTEXITCODE
}

$archiveName = Get-ArchiveName
$baseUrl = Get-ReleaseBaseUrl
$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
$archivePath = Join-Path $tempDir $archiveName
$checksumsPath = Join-Path $tempDir "checksums.txt"
$extractDir = Join-Path $tempDir "extracted"

New-Item -ItemType Directory -Force -Path $tempDir | Out-Null
New-Item -ItemType Directory -Force -Path $extractDir | Out-Null

try {
  Write-Log "Downloading temporary ai-delivery binary from $baseUrl"
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

  Invoke-AiDelivery -Executable $binaryPath.FullName
  exit $LASTEXITCODE
} finally {
  if (Test-Path -LiteralPath $tempDir) {
    Remove-Item -LiteralPath $tempDir -Recurse -Force
  }
}
