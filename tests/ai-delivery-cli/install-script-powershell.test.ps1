[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$InstallScript = Join-Path $Root "scripts/install-ai-delivery.ps1"

function Fail {
  param([string]$Message)
  throw "[install-script-powershell-test] $Message"
}

function Assert-True {
  param(
    [bool]$Condition,
    [string]$Message
  )

  if (-not $Condition) {
    Fail $Message
  }
}

function Assert-Contains {
  param(
    [string]$Text,
    [string]$Needle
  )

  if (-not $Text.Contains($Needle)) {
    Fail "expected '$Needle'"
  }
}

function Assert-NotContains {
  param(
    [string]$Text,
    [string]$Needle
  )

  if ($Text.Contains($Needle)) {
    Fail "did not expect '$Needle'"
  }
}

function New-StubExecutable {
  param([string]$Path)

  $source = @"
using System;
using System.IO;
public static class Program {
  public static int Main(string[] args) {
    var output = Environment.GetEnvironmentVariable("AI_DELIVERY_TEST_OUTPUT");
    if (!string.IsNullOrEmpty(output)) {
      File.WriteAllText(output, string.Join(" ", args));
    }
    return 0;
  }
}
"@

  Add-Type -TypeDefinition $source -OutputAssembly $Path -OutputType ConsoleApplication | Out-Null
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
$InstallDir = Join-Path $TempDir "bin"
$StubExe = Join-Path $TempDir "ai-delivery.exe"
$RunOutput = Join-Path $TempDir "ai-delivery-run.txt"
$WebRequestLog = New-Object System.Collections.Generic.List[object]
$ArchiveName = "ai-delivery_windows_amd64.zip"
$ArchivePath = Join-Path $TempDir $ArchiveName
$ChecksumsPath = Join-Path $TempDir "checksums.txt"

try {
  New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
  New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

  New-StubExecutable -Path $StubExe
  Compress-Archive -LiteralPath $StubExe -DestinationPath $ArchivePath
  $Checksum = (Get-FileHash -LiteralPath $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
  Set-Content -LiteralPath $ChecksumsPath -Value @(
    "$Checksum  $ArchiveName"
    "deadbeef  ai-delivery_windows_arm64.zip"
  )

  function Invoke-WebRequest {
    param(
      [Parameter(Mandatory = $true)]
      [string]$Uri,
      [Parameter(Mandatory = $true)]
      [string]$OutFile,
      [hashtable]$Headers
    )

    $authorization = ""
    $accept = ""
    if ($null -ne $Headers) {
      if ($Headers.ContainsKey("Authorization")) {
        $authorization = [string]$Headers["Authorization"]
      }
      if ($Headers.ContainsKey("Accept")) {
        $accept = [string]$Headers["Accept"]
      }
    }

    $script:WebRequestLog.Add([pscustomobject]@{
        Uri           = $Uri
        Authorization = $authorization
        Accept        = $accept
      })

    switch ($Uri) {
      { $_ -eq "file://$TempDir/$ArchiveName" } {
        Copy-Item -LiteralPath $ArchivePath -Destination $OutFile -Force
        break
      }
      { $_ -eq "file://$TempDir/checksums.txt" } {
        Copy-Item -LiteralPath $ChecksumsPath -Destination $OutFile -Force
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/latest" {
        Set-Content -LiteralPath $OutFile -NoNewline -Value @"
{"assets":[{"id":101,"name":"$ArchiveName"},{"id":102,"name":"checksums.txt"}]}
"@
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/assets/101" {
        Copy-Item -LiteralPath $ArchivePath -Destination $OutFile -Force
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/assets/102" {
        Copy-Item -LiteralPath $ChecksumsPath -Destination $OutFile -Force
        break
      }
      default {
        Fail "unexpected web request uri: $Uri"
      }
    }
  }

  Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
  $env:AI_DELIVERY_TEST_OUTPUT = $RunOutput
  & $InstallScript -InstallDir $InstallDir -DownloadBaseUrl "file://$TempDir" -Version "v9.9.9"

  $InstalledExe = Join-Path $InstallDir "ai-delivery.exe"
  Assert-True (Test-Path -LiteralPath $InstalledExe -PathType Leaf) "expected installed ai-delivery.exe"

  $env:GITHUB_TOKEN = "test-token"
  & $InstallScript -InstallDir $InstallDir -Repo "example/private-repo" -Version "latest"

  $requestText = ($WebRequestLog | ForEach-Object {
      "$($_.Uri) $($_.Authorization) $($_.Accept)"
    }) -join "`n"
  Assert-Contains $requestText "Authorization: Bearer test-token"
  Assert-Contains $requestText "Accept: application/octet-stream"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/latest"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/assets/101"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/assets/102"
  Assert-NotContains $requestText "https://github.com/example/private-repo/releases/latest/download/$ArchiveName"

  & $InstallScript -InstallDir $InstallDir -DownloadBaseUrl "file://$TempDir" -Version "v9.9.9" -UpgradeInitTargetRepo "C:\repo"
  $runText = Get-Content -LiteralPath $RunOutput -Raw
  Assert-Contains $runText "init --upgrade C:\repo"
} finally {
  Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
  Remove-Item Env:AI_DELIVERY_TEST_OUTPUT -ErrorAction SilentlyContinue
  if (Test-Path -LiteralPath $TempDir) {
    Remove-Item -LiteralPath $TempDir -Recurse -Force
  }
}
