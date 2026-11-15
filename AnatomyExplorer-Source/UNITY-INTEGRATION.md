# Blood and immune monitor — Unity side

The monitor itself is an HTML overlay (`anatomy-explorer/immune.html`) drawn on
top of the WebGL canvas. This folder holds the two small pieces that let the
scene drive it.

## What was added

| File | Purpose |
| --- | --- |
| `Assets/Anatomy/Plugins/OrbitCareBridge.jslib` | Three functions that call `window.OrbitCare` |
| `Assets/Anatomy/Scripts/WebBridge.cs` | `[DllImport("__Internal")]` wrappers plus the inbound callback |
| `Assets/Anatomy/Scripts/Topics/AnatomyTopics.cs` | Topic id constants (`Brain` … `ImmuneSystem`) |
| `Assets/Anatomy/Scripts/AnatomyExplorer.cs` | Two hooks, marked `// The immune system is the one topic…` |

## Behaviour

- Selecting the **Immune system** topic opens the monitor.
- Selecting any other topic closes it.
- Closing the explanation overlay closes it.

## Scene setup (one step)

Create an empty GameObject named exactly **`OrbitCareBridge`** and add the
`WebBridge` component. The name matters: the page reaches it by name.

Optional: wire `monitorVisibilityChanged` to react when the user closes the
panel from the web side.

## Building

The `.jslib` is picked up automatically on a WebGL build — no build settings
change. Outside WebGL player builds every outbound call compiles to nothing,
so the editor and other platforms are unaffected.

After rebuilding, replace `anatomy-explorer/Build/` with the new output, or
run the exporter that produces both together.

## Notes

- `WebBridge` has no `.meta` file yet; Unity will create one on first import.
  Commit it with the rest.
- The page calls back with `SendMessage('OrbitCareBridge', 'OnMonitorOpen', '1')`
  or `'0'`. Nothing breaks if the object is absent — the page swallows the error.
