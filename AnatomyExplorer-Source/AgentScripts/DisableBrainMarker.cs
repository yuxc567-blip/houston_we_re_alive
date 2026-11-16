using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using System.Linq;

public static class DisableBrainMarker
{
    public static string All()
    {
        if (Application.isPlaying) throw new System.Exception("Apply in Edit mode.");
        var explorer = Object.FindAnyObjectByType<AnatomyExplorer>();
        var marker = explorer.markers[0];
        if (marker != null)
        {
            Undo.RecordObject(marker.gameObject, "Disable brain marker");
            marker.gameObject.SetActive(false);
            EditorUtility.SetDirty(marker.gameObject);
            Undo.RecordObject(explorer, "Remove legacy brain marker reference");
            explorer.markers[0] = null;
            explorer.organParts = explorer.organParts.Where(p => p != null && p.transform != marker && !p.transform.IsChildOf(marker)).ToArray();
        }
        EditorUtility.SetDirty(explorer);
        EditorSceneManager.MarkSceneDirty(explorer.gameObject.scene);
        EditorSceneManager.SaveScene(explorer.gameObject.scene);
        AssetDatabase.SaveAssets();
        return "Brain marker disabled and legacy reference cleared; actual brain meshes preserved.";
    }
}
