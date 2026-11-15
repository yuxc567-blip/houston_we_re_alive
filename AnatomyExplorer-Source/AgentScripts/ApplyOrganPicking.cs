using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
public static class ApplyOrganPicking
{
    public static string All()
    {
        if (Application.isPlaying) throw new System.Exception("Apply in Edit mode.");
        var explorer=Object.FindAnyObjectByType<AnatomyExplorer>();
        Undo.RecordObject(explorer,"Select organs directly");
        explorer.organParts=AnatomyPicking.Configure(explorer.body,explorer.markers);
        foreach(var text in Object.FindObjectsByType<TMPro.TMP_Text>(FindObjectsInactive.Include))
        {
            if(text.text.Contains("Select a numbered marker"))text.text="Click an organ on the body, or choose a topic on the left.";
            if(text.text.Contains("Click the numbered markers"))text.text=text.text.Replace("Click the numbered markers or topic buttons","Click the organs on the body or topic buttons");
            EditorUtility.SetDirty(text);
        }
        EditorUtility.SetDirty(explorer);
        EditorSceneManager.MarkSceneDirty(explorer.gameObject.scene);
        EditorSceneManager.SaveScene(explorer.gameObject.scene);
        AssetDatabase.SaveAssets();
        var counts=new int[5];foreach(var part in explorer.organParts)if(part.gameObject.activeInHierarchy)counts[part.topicIndex]++;
        return "Active organ click targets (brain, heart, bones, eyes, immunity): "+string.Join(", ",counts);
    }
}
