using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
public static class RefineScene
{
    public static string All()
    {
        var explorer=Object.FindAnyObjectByType<AnatomyExplorer>();
        explorer.cameraRig.position=new Vector3(0,2.25f,-7.2f);
        explorer.viewCamera.transform.position=explorer.cameraRig.position;
        foreach(var marker in explorer.markers) marker.GetChild(0).localScale=Vector3.one;
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        AssetDatabase.SaveAssets();return "Framing and marker labels refined.";
    }
}

