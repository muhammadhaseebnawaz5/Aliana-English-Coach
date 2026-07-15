$targetDir = "$env:LOCALAPPDATA\AlinaCoach"
if (-not (Test-Path -Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir | Out-Null
}

$exeSource = "dist\Alina English Coach.exe"
$iconSource = "app_icon.ico"
$uninstallerSource = "uninstall_alina.ps1"
$exeDest = "$targetDir\Alina English Coach.exe"
$iconDest = "$targetDir\app_icon.ico"
$uninstallerDest = "$targetDir\uninstall_alina.ps1"

# Copy files
Copy-Item -Path $exeSource -Destination $exeDest -Force
Copy-Item -Path $iconSource -Destination $iconDest -Force
Copy-Item -Path $uninstallerSource -Destination $uninstallerDest -Force

$wshShell = New-Object -ComObject WScript.Shell

# Desktop Shortcut
$desktop = [System.Environment]::GetFolderPath('Desktop')
$shortcut = $wshShell.CreateShortcut("$desktop\Alina English Coach.lnk")
$shortcut.TargetPath = $exeDest
$shortcut.IconLocation = $iconDest
$shortcut.WorkingDirectory = $targetDir
$shortcut.Save()

# Start Menu Shortcut
$startMenu = [System.Environment]::GetFolderPath('Programs')
$startMenuShortcut = $wshShell.CreateShortcut("$startMenu\Alina English Coach.lnk")
$startMenuShortcut.TargetPath = $exeDest
$startMenuShortcut.IconLocation = $iconDest
$startMenuShortcut.WorkingDirectory = $targetDir
$startMenuShortcut.Save()

# --- Registry for Add/Remove Programs ---
$registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AlinaEnglishCoach"
if (-not (Test-Path $registryPath)) {
    New-Item -Path $registryPath | Out-Null
}

$uninstallerPath = "$targetDir\uninstall.bat"
@"
@echo off
powershell -ExecutionPolicy Bypass -File "$targetDir\uninstall_alina.ps1"
"@ | Out-File -FilePath $uninstallerPath -Encoding ascii

New-ItemProperty -Path $registryPath -Name "DisplayName" -Value "Alina English Coach" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $registryPath -Name "DisplayIcon" -Value $iconDest -PropertyType String -Force | Out-Null
New-ItemProperty -Path $registryPath -Name "UninstallString" -Value "$uninstallerPath" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $registryPath -Name "Publisher" -Value "Antigravity AI" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $registryPath -Name "DisplayVersion" -Value "1.0.0" -PropertyType String -Force | Out-Null

Write-Host "✅ Installation Complete! Shortcuts created and registered in Windows Apps."
