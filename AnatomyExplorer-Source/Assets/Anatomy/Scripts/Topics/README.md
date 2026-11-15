# Editing organ popup content

Each topic owns its title, summary, details, and future result formatting:

| Topic | File |
| --- | --- |
| Brain | `BrainTopic.cs` |
| Eyes | `EyesTopic.cs` |
| Immune system | `ImmuneSystemTopic.cs` |
| Bone density / existing Bones popup | `BoneDensityTopic.cs` |
| Heart | `HeartTopic.cs` |

Edit your topic's `Summary` and `Details` properties. These properties are read
each time its popup opens, so future calculation results can be formatted here.
This separation does not yet run Python or load Python results.

`IAnatomyTopic.cs` defines the common content fields. `AnatomyTopics.cs` maps the
existing scene IDs to their topic files. Keep that ID order stable. The shared
`AnatomyExplorer.cs` still owns opening/closing the popup, input, and navigation.

The bone topic keeps the existing **Bones** label and explanation. No bone-density
calculation or new medical interpretation has been added.

## Working together

Use separate Git branches and local Unity project copies. Each collaborator can
edit their topic file without changing the other topic files or the scene. Changes
to the shared interface, registry, controller, or scene should be coordinated.
Keep Unity-generated `.meta` files with the corresponding scripts in source control.

C# changes require a new Web build before they appear in the browser. This refactor
preserves the existing displayed content, so the existing browser export continues
to look the same. Python scripts are unchanged and their integration is separate work.
