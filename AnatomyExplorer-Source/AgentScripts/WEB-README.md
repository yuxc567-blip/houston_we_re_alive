# Anatomy Explorer — browser export

This folder is the destination for the Unity Web build. The export is **not ready until `index.html`, `Build/`, and `TemplateData/` have been generated**. Unity is currently completing its first Web-platform compilation after a compiler recovery.

The Unity source project is at:

`C:\Users\yuxc5\OneDrive\Documents\Codex\AnatomyExplorer`

Once the build is ready, VS Code Live Server serves it at:

[Open the local anatomy explorer](http://127.0.0.1:5500/anatomy-explorer/)

To reopen it later, open this repository in VS Code, open `anatomy-explorer/index.html`, and choose **Open with Live Server**. Keep the entire `Build` and `TemplateData` folders beside `index.html`.

The export is configured without build-file compression and without Web threading, so Live Server does not need custom compression or cross-origin-isolation headers.

The Unity project contains the editable model and C# behavior. Changes made there need a new Web build before they appear in the browser.
