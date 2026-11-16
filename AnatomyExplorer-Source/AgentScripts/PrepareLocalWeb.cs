using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
public static class PrepareLocalWeb
{
    public static string All()
    {
        if(Application.isPlaying)throw new System.Exception("Exit Play mode before preparing a build.");
        EditorSceneManager.SaveOpenScenes();
        PlayerSettings.WebGL.compressionFormat=WebGLCompressionFormat.Disabled;
        PlayerSettings.WebGL.decompressionFallback=false;
        PlayerSettings.WebGL.threadsSupport=false;
        PlayerSettings.WebGL.template="APPLICATION:Default";
        PlayerSettings.defaultWebScreenWidth=1600;
        PlayerSettings.defaultWebScreenHeight=1000;
        AssetDatabase.SaveAssets();
        return "Web export configured: uncompressed files, single-threaded, compatible with VS Code Live Server.";
    }
}
