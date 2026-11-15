# Anatomy Explorer — browser export

This folder contains the completed Unity Web build, including `index.html`, `Build/`, `TemplateData/`, and `StreamingAssets/`.

## Editable Unity source

[Open the editable Unity source on GitHub](https://github.com/yuxc567-blip/houston_we_re_alive/tree/main/AnatomyExplorer-Source).

Clone this repository on each device. In Unity Hub, choose **Add project from disk** and select the `AnatomyExplorer-Source` folder inside your local clone. Use **Unity 6000.6.9f1** with **Web Build Support**.

The source includes `Assets`, `Packages`, `ProjectSettings`, and `AgentScripts`. Generated caches such as `Library`, `Temp`, and `Logs` are excluded by the Unity `.gitignore`.

The five independent organ files are under `AnatomyExplorer-Source/Assets/Anatomy/Scripts/Topics/`. Python scripts remain in this repository and are not yet connected to the viewer.

Use separate local clones and Git branches for simultaneous work. Coordinate changes to shared code and Unity scenes.

VS Code Live Server serves it at:

[Open the local anatomy explorer](http://127.0.0.1:5500/anatomy-explorer/)

To reopen it later, open this repository in VS Code, open `anatomy-explorer/index.html`, and choose **Open with Live Server**. Keep the entire `Build` and `TemplateData` folders beside `index.html`.

The export is configured without build-file compression and without Web threading, so Live Server does not need custom compression or cross-origin-isolation headers.

The Unity project contains the editable model and C# behavior. Changes made there need a new Web build before they appear in the browser.


## Brain marker update
The floating brain marker is disabled in the saved Unity scene, and its legacy marker reference is cleared. The exposed brain mesh remains clickable.

This local update replaces only `data.unity3d` inside the Web data archive, using scene assets exported by the same Unity Editor. It retains the original working executable and IL2CPP metadata. Full rebuild attempts were cancelled after optimizer failures and long optimization times. The updated page was verified in the browser: marker hidden, brain mesh opens the Brain explanation.

The scene-only packaging helper is `AnatomyExplorer/AgentScripts/package_scene_update.py` in the source workspace. It is intended only for scene changes with unchanged runtime field layouts and Unity version; code changes require a complete build.

