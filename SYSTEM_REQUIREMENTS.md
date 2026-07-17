# Gesture Assistant System Requirements

## Supported platform

The current release is a 64-bit Windows desktop application.

| Component | Minimum | Recommended for a smooth experience |
|---|---|---|
| Operating system | Windows 10 or 11, 64-bit | Windows 11, 64-bit |
| Processor | Modern x64 dual-core processor | Recent Intel Core i5, AMD Ryzen 5, or similar quad-core processor |
| Memory | 4 GB RAM | 8 GB RAM or more |
| Free storage | 750 MB | 1 GB or more for installation and updates |
| Camera | Windows-compatible webcam | 720p or better webcam at 30 FPS |
| Graphics | Integrated graphics | No dedicated GPU required |
| Internet | Required only to download the installer | Not required during normal recognition |

Windows 11 is the currently verified operating system. Windows 10 is expected to work but still needs a clean-machine release test. Very old x64 processors have not been validated.

## Runtime behavior

- Camera frames are processed locally; the application does not require a cloud service.
- Python, MediaPipe, OpenCV, NumPy, and the other runtime libraries are bundled.
- The tray process uses approximately 31-33 MB of memory while recognition is stopped.
- Development testing measured approximately 3.5-3.7% CPU while recognition was active on the original test computer. Usage varies by processor, camera driver, resolution, and frame rate.
- The current packaged folder is approximately 321 MB before installer compression.
- Camera index `0` and one detected hand are currently supported.

## Permissions and setup

- The user must allow desktop applications to access the camera in Windows privacy settings.
- Start with Windows is optional and can be changed from the tray menu.
- The installer is designed for the current user and does not require administrator rights.
- Gesture configuration and uploaded scripts are stored under `%LOCALAPPDATA%\GestureAssistant` and remain separate from application binaries.

## Recommended environment

For comfortable media control, use stable front-facing lighting, keep the hand within the webcam view, and position the camera where gestures can be performed without holding the arm at an uncomfortable height.
