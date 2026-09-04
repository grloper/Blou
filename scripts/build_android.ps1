# Blou — Android Build Helper Script (PowerShell)
param(
    [string]$Task = ":freeRDPCore:externalNativeBuildDebug",
    [switch]$Info
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Blou Android Build Orchestrator" -ForegroundColor Cyan
Write-Host "  Task: $Task" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Configure paths
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:PATH = "$env:LOCALAPPDATA\strawberry-perl\perl\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:JAVA_HOME\bin;$env:PATH"

$projectDir = Join-Path $PSScriptRoot "..\FreeRDP\client\Android\Studio"
Set-Location $projectDir

$extraArgs = if ($Info) { "--info" } else { "" }
cmd /c "gradlew.bat $Task $extraArgs"
