using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using TMPro;
public static class ApplyExplorerWindow
{
    static void Layout(RectTransform r,Vector2 min,Vector2 max)
    {
        r.anchorMin=min;r.anchorMax=max;r.pivot=new Vector2(.5f,.5f);r.offsetMin=Vector2.zero;r.offsetMax=Vector2.zero;
    }
    public static string All()
    {
        if(Application.isPlaying)throw new System.Exception("Apply in Edit mode.");
        var explorer=Object.FindAnyObjectByType<AnatomyExplorer>();
        // Recenter the actual root pivot while preserving every mesh's world position.
        Bounds bounds=new Bounds();bool hasBounds=false;
        foreach(var renderer in explorer.body.GetComponentsInChildren<MeshRenderer>())
        {
            if(!renderer.enabled||renderer.GetComponent<TMP_Text>()!=null)continue;
            bool marker=false;foreach(var oldMarker in explorer.markers)if(oldMarker!=null&&renderer.transform.IsChildOf(oldMarker))marker=true;
            if(marker)continue;
            if(!hasBounds){bounds=renderer.bounds;hasBounds=true;}else bounds.Encapsulate(renderer.bounds);
        }
        if(hasBounds&&Vector3.Distance(explorer.body.position,bounds.center)>.001f)
        {
            var children=new Transform[explorer.body.childCount];var positions=new Vector3[children.Length];
            for(int i=0;i<children.Length;i++){children[i]=explorer.body.GetChild(i);positions[i]=children[i].position;}
            Undo.RecordObject(explorer.body,"Center body pivot");
            explorer.body.position=bounds.center;
            for(int i=0;i<children.Length;i++){Undo.RecordObject(children[i],"Preserve anatomy placement");children[i].position=positions[i];}
        }
        var panel=(RectTransform)explorer.heading.transform.parent;
        var canvas=panel.GetComponentInParent<Canvas>();
        if(explorer.explanationOverlay==null)
        {
            var overlay=new GameObject("Organ explanation window",typeof(RectTransform),typeof(UnityEngine.UI.Image));
            overlay.transform.SetParent(canvas.transform,false);
            Layout((RectTransform)overlay.transform,Vector2.zero,Vector2.one);
            var image=overlay.GetComponent<UnityEngine.UI.Image>();var tint=Palette.Background;tint.a=.8f;image.color=tint;image.raycastTarget=true;
            panel.SetParent(overlay.transform,false);
            explorer.explanationOverlay=overlay;
        }
        Layout(panel,new Vector2(.15f,.10f),new Vector2(.85f,.90f));
        panel.GetComponent<UnityEngine.UI.Image>().raycastTarget=true;
        Layout(explorer.heading.rectTransform,new Vector2(.045f,.76f),new Vector2(.77f,.89f));
        explorer.heading.fontSize=42;
        Layout(explorer.explanation.rectTransform,new Vector2(.045f,.56f),new Vector2(.955f,.75f));
        explorer.explanation.fontSize=28;explorer.explanation.enableAutoSizing=true;explorer.explanation.fontSizeMin=22;explorer.explanation.fontSizeMax=28;
        Layout(explorer.detail.rectTransform,new Vector2(.045f,.12f),new Vector2(.955f,.54f));
        explorer.detail.fontSize=24;explorer.detail.enableAutoSizing=true;explorer.detail.fontSizeMin=20;explorer.detail.fontSizeMax=24;
        var eyebrow=panel.Find("Panel eyebrow") as RectTransform;
        if(eyebrow!=null)Layout(eyebrow,new Vector2(.045f,.91f),new Vector2(.70f,.97f));
        if(explorer.closeExplanationButton==null)
        {
            var close=new GameObject("Close explanation",typeof(RectTransform),typeof(UnityEngine.UI.Image),typeof(UnityEngine.UI.Button));
            close.transform.SetParent(panel,false);
            Layout((RectTransform)close.transform,new Vector2(.78f,.90f),new Vector2(.96f,.97f));
            close.GetComponent<UnityEngine.UI.Image>().color=Palette.Accent;
            var label=new GameObject("Close label",typeof(RectTransform),typeof(TextMeshProUGUI));
            label.transform.SetParent(close.transform,false);Layout((RectTransform)label.transform,Vector2.zero,Vector2.one);
            var text=label.GetComponent<TextMeshProUGUI>();text.font=explorer.heading.font;text.text="Close  X";text.fontSize=24;text.fontStyle=FontStyles.Bold;text.color=Palette.Background;text.alignment=TextAlignmentOptions.Center;text.raycastTarget=false;
            explorer.closeExplanationButton=close.GetComponent<UnityEngine.UI.Button>();
        }
        var hint=panel.Find("Close hint");
        if(hint==null)
        {
            var go=new GameObject("Close hint",typeof(RectTransform),typeof(TextMeshProUGUI));go.transform.SetParent(panel,false);
            Layout((RectTransform)go.transform,new Vector2(.045f,.035f),new Vector2(.95f,.085f));
            var text=go.GetComponent<TextMeshProUGUI>();text.font=explorer.heading.font;text.text="Press Esc or Close to return to the body.";text.fontSize=19;text.color=Palette.Text;text.raycastTarget=false;
        }
        explorer.explanationOverlay.transform.SetAsLastSibling();
        explorer.explanationOverlay.SetActive(false);
        EditorUtility.SetDirty(explorer);
        EditorSceneManager.MarkSceneDirty(explorer.gameObject.scene);EditorSceneManager.SaveScene(explorer.gameObject.scene);AssetDatabase.SaveAssets();
        return "Large centered explanation window configured and saved.";
    }
}
