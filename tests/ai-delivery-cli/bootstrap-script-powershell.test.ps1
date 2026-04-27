[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$BootstrapScript = Join-Path $Root "scripts/bootstrap-ai-delivery.ps1"

function Fail {
  param([string]$Message)
  throw "[bootstrap-script-powershell-test] $Message"
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

  $sourcePath = [System.IO.Path]::ChangeExtension($Path, ".go")
  $source = @'
package main

import (
  "os"
  "strings"
)

func main() {
  output := os.Getenv("AI_DELIVERY_TEST_OUTPUT")
  if output != "" {
    _ = os.WriteFile(output, []byte(strings.Join(os.Args[1:], " ")), 0644)
  }
}
'@

  Set-Content -LiteralPath $sourcePath -Value $source -NoNewline
  & go build -o $Path $sourcePath
  if ($LASTEXITCODE -ne 0) {
    Fail "failed to build stub executable with go"
  }
  Remove-Item -LiteralPath $sourcePath -Force
}

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ([System.IO.Path]::GetRandomFileName())
$TargetRepo = Join-Path $TempDir "target-repo"
$LocalLog = Join-Path $TempDir "local-command.log"
$DownloadLog = Join-Path $TempDir "download-command.log"
$LocalExe = Join-Path $TempDir "local-ai-delivery.exe"
$DownloadExe = Join-Path $TempDir "ai-delivery.exe"
$WebRequestLog = New-Object System.Collections.Generic.List[object]
$ArchiveName = "ai-delivery_windows_amd64.zip"
$ArchivePath = Join-Path $TempDir $ArchiveName
$ChecksumsPath = Join-Path $TempDir "checksums.txt"
$global:AiDeliveryTestWebRequestLog = $WebRequestLog
$global:AiDeliveryTestTempDir = $TempDir
$global:AiDeliveryTestArchiveName = $ArchiveName
$global:AiDeliveryTestArchivePath = $ArchivePath
$global:AiDeliveryTestChecksumsPath = $ChecksumsPath

try {
  New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
  New-Item -ItemType Directory -Force -Path $TargetRepo | Out-Null

  New-StubExecutable -Path $LocalExe
  New-StubExecutable -Path $DownloadExe
  Compress-Archive -LiteralPath $DownloadExe -DestinationPath $ArchivePath
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

    $global:AiDeliveryTestWebRequestLog.Add([pscustomobject]@{
        Uri           = $Uri
        Authorization = $authorization
        Accept        = $accept
      })

    switch ($Uri) {
      { $_ -eq "file://$global:AiDeliveryTestTempDir/$global:AiDeliveryTestArchiveName" } {
        Copy-Item -LiteralPath $global:AiDeliveryTestArchivePath -Destination $OutFile -Force
        break
      }
      { $_ -eq "file://$global:AiDeliveryTestTempDir/checksums.txt" } {
        Copy-Item -LiteralPath $global:AiDeliveryTestChecksumsPath -Destination $OutFile -Force
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/tags/v0.0.1" {
        Set-Content -LiteralPath $OutFile -NoNewline -Value @"
{"assets":[{"id":201,"name":"$global:AiDeliveryTestArchiveName"},{"id":202,"name":"checksums.txt"}]}
"@
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/assets/201" {
        Copy-Item -LiteralPath $global:AiDeliveryTestArchivePath -Destination $OutFile -Force
        break
      }
      "https://api.github.com/repos/example/private-repo/releases/assets/202" {
        Copy-Item -LiteralPath $global:AiDeliveryTestChecksumsPath -Destination $OutFile -Force
        break
      }
      default {
        Fail "unexpected web request uri: $Uri"
      }
    }
  }

  $env:AI_DELIVERY_TEST_OUTPUT = $LocalLog
  Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
  & $BootstrapScript -TargetRepo $TargetRepo -CommandOverride $LocalExe
  $localText = Get-Content -LiteralPath $LocalLog -Raw
  Assert-Contains $localText "init"
  Assert-Contains $localText $TargetRepo

  $env:AI_DELIVERY_TEST_OUTPUT = $DownloadLog
  & $BootstrapScript -TargetRepo $TargetRepo -DownloadBaseUrl "file://$TempDir" -Version "v9.9.9"
  $downloadText = Get-Content -LiteralPath $DownloadLog -Raw
  Assert-Contains $downloadText "init"
  Assert-Contains $downloadText $TargetRepo

  Remove-Item -LiteralPath $DownloadLog -Force
  $env:AI_DELIVERY_TEST_OUTPUT = $DownloadLog
  $env:GITHUB_TOKEN = "test-token"
  & $BootstrapScript -TargetRepo $TargetRepo -Repo "example/private-repo" -Version "v0.0.1"

  $requestText = ($WebRequestLog | ForEach-Object {
      "$($_.Uri) $($_.Authorization) $($_.Accept)"
    }) -join "`n"
  Assert-Contains $requestText "Authorization: Bearer test-token"
  Assert-Contains $requestText "Accept: application/octet-stream"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/tags/v0.0.1"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/assets/201"
  Assert-Contains $requestText "https://api.github.com/repos/example/private-repo/releases/assets/202"
  Assert-NotContains $requestText "https://github.com/example/private-repo/releases/download/v0.0.1/$ArchiveName"

  $downloadText = Get-Content -LiteralPath $DownloadLog -Raw
  Assert-Contains $downloadText "init"
  Assert-Contains $downloadText $TargetRepo
} finally {
  Remove-Item Env:AI_DELIVERY_TEST_OUTPUT -ErrorAction SilentlyContinue
  Remove-Item Env:GITHUB_TOKEN -ErrorAction SilentlyContinue
  Remove-Variable -Name AiDeliveryTestWebRequestLog -Scope Global -ErrorAction SilentlyContinue
  Remove-Variable -Name AiDeliveryTestTempDir -Scope Global -ErrorAction SilentlyContinue
  Remove-Variable -Name AiDeliveryTestArchiveName -Scope Global -ErrorAction SilentlyContinue
  Remove-Variable -Name AiDeliveryTestArchivePath -Scope Global -ErrorAction SilentlyContinue
  Remove-Variable -Name AiDeliveryTestChecksumsPath -Scope Global -ErrorAction SilentlyContinue
  if (Test-Path -LiteralPath $TempDir) {
    Remove-Item -LiteralPath $TempDir -Recurse -Force
  }
}
