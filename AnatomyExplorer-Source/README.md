# Anatomy Explorer — beginner guide

Open the `AnatomyExplorer` project in Unity. In the Project panel, open `Assets/Anatomy/AnatomyExplorer.unity`, then press the triangle **Play** button at the top. Click the Game tab to use the explorer. Press Play again to return to editing.

## Explore

- Drag on the body to turn it around its center. Close the explanation window, then scroll to zoom in or out. Click the exposed brain on the head, red heart, white bones, green immune structures, or either eye. The five topic buttons also work.
- Arrow keys rotate; keys 1–5 select topics; R resets the view; Escape opens help.
- A large centered pop-up explains the selected structure. Press Escape or Close to return to the body. The progress indicator counts topics visited during this session.
- Sound can be toggled with the Sound button. This preference is saved locally.

## Edit your project

- `Assets/Anatomy/Scripts/Topics/` contains separate Brain, Eyes, Immune System, Bone Density, and Heart popup files.
- `Assets/Anatomy/Scripts/AnatomyExplorer.cs` contains shared popup and interaction controls.
- `Assets/Anatomy/Scripts/Palette.cs` contains the display colors.
- `AgentScripts/BuildAnatomy.cs` is the original scene builder. Rebuilding replaces the current scene, so save edits first.
- Materials and the post-processing profile live under `Assets/Anatomy`.

This is a simplified educational model. The organ and lymph-node diagrams indicate representative locations. The immune system is distributed across the body. This project is not a clinical anatomy reference or a medical diagnostic tool.

Unity setup uses the official Unity CLI and its `new-unity-project` skill. For command-line work, open a new PowerShell window so the installed Unity CLI is on PATH.

## Reference reading

- [NCI: Introduction to the human body](https://training.seer.cancer.gov/anatomy/body/)
- [NCI: Nervous system](https://training.seer.cancer.gov/anatomy/nervous/)
- [NCI: Cardiovascular system](https://training.seer.cancer.gov/anatomy/cardiovascular/)
- [NCI: Skeletal system](https://training.seer.cancer.gov/anatomy/skeletal/)
- [NCI: Lymphatic system](https://training.seer.cancer.gov/anatomy/lymphatic/)
- [NEI: How the eyes work](https://www.nei.nih.gov/learn-about-eye-health/healthy-vision/how-eyes-work)

Rendering references: Unity 6000.6 URP Volumes manual and Cinemachine camera manual. Craft references used: art direction, placeholder assets, scene lighting, camera rigs, game feel, game audio, game shell, live floor and visual scorecard.


