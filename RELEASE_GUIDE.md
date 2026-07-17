# Gesture Assistant Release Guide

## Release readiness

Before publishing a version, verify the installer on a clean Windows user account or virtual machine:

1. Install without Python or project dependencies already present.
2. Launch from the Start Menu and Desktop shortcut.
3. Confirm Task Manager displays `GestureAssistant` and duplicate launches are rejected.
4. Allow camera access and test every gesture class and action type.
5. Test preview hide/show, Start/Stop, Start with Windows, configuration persistence, Exit, and uninstall.
6. Confirm user settings remain under `%LOCALAPPDATA%\GestureAssistant` after an application update.
7. Scan the installer and publish its SHA-256 checksum.

The application is currently unsigned. Windows SmartScreen may warn users until the installer and executable are signed with a trusted code-signing certificate.

## Build the application

```powershell
.\build_app.ps1
```

Output: `dist\GestureAssistant\GestureAssistant.exe`

## Build the installer

Install the current Inno Setup release, then run:

```powershell
.\build_installer.ps1
```

Output: `release\GestureAssistant-Setup-0.1.1.exe`

## Create a public download link

GitHub Releases is the recommended distribution path. Keep generated binaries out of normal Git history.

1. Push the source repository to GitHub without `build`, `dist`, or `release` folders.
2. Open the repository's **Releases** page and choose **Draft a new release**.
3. Create a version tag such as `v0.1.1`.
4. Upload `GestureAssistant-Setup-0.1.1.exe` and a SHA-256 checksum file.
5. Add release notes, supported systems, known limitations, and a link to `SYSTEM_REQUIREMENTS.md`.
6. Publish the release and share its release-page URL.

GitHub currently permits each release asset to be under 2 GiB, with no total release-size or bandwidth limit. See [GitHub's release documentation](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases).

A stable latest-release page uses this form:

```text
https://github.com/OWNER/REPOSITORY/releases/latest
```

A version-specific direct installer link uses this form:

```text
https://github.com/OWNER/REPOSITORY/releases/download/v0.1.1/GestureAssistant-Setup-0.1.1.exe
```
