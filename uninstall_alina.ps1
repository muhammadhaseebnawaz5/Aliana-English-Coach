# uninstall_alina.ps1 - Uninstaller for Alina English Coach

$targetDir = "$env:LOCALAPPDATA\AlinaCoach"
$registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\AlinaEnglishCoach"

Write-Host "⚠️ Uninstalling Alina English Coach..."

# 1. Remove Shortcuts
$desktop = [System.Environment]::GetFolderPath('Desktop')
$startMenu = [System.Environment]::GetFolderPath('Programs')

if (Test-Path "$desktop\Alina English Coach.lnk") {
    Remove-Item "$desktop\Alina English Coach.lnk" -Force
}
if (Test-Path "$startMenu\Alina English Coach.lnk") {
    Remove-Item "$startMenu\Alina English Coach.lnk" -Force
}

# 2. Remove Registry Entry
if (Test-Path $registryPath) {
    Remove-Item -Path $registryPath -Recurse -Force
}

# 3. Remove App Directory
if (Test-Path $targetDir) {
    # We can't delete the folder if the uninstaller script itself is in it 
    # and being executed, but we can delete everything ELSE first.
    Get-ChildItem -Path $targetDir -Exclude "uninstall_alina.ps1", "uninstall.bat" | Remove-Item -Recurse -Force
    Write-Host "Note: You can now manually delete the folder $targetDir"
}

Write-Host "✅ Uninstallation Complete."
