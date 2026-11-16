using UnityEngine;
using System.Threading.Tasks;
public static class VerifyExplorer
{
    public static async Task<string> All()
    {
        var e=Object.FindAnyObjectByType<AnatomyExplorer>();
        if(e==null || !Application.isPlaying) throw new System.Exception("Explorer must be in Play mode.");
        for(int i=0;i<5;i++) {
            e.topicButtons[i].onClick.Invoke();
            if(e.Selected!=i || e.heading.text!=AnatomyExplorer.Titles[i] || e.explanation.text!=AnatomyExplorer.Summaries[i] || e.detail.text!=AnatomyExplorer.Details[i]) throw new System.Exception("Topic wiring failed: "+i);
            bool found=false;
            foreach(var part in e.organParts)if(part.topicIndex==i&&part.gameObject.activeInHierarchy)found=true;
            if(!found)throw new System.Exception("Missing organ click targets: "+i);
        }
        if(e.VisitedCount!=5) throw new System.Exception("Progress counter failed.");
        e.helpButton.onClick.Invoke();if(!e.help.activeSelf) throw new System.Exception("Help did not open.");
        e.closeHelpButton.onClick.Invoke();if(e.help.activeSelf) throw new System.Exception("Help did not close.");
        bool mute=e.Muted;e.soundButton.onClick.Invoke();if(e.Muted==mute) throw new System.Exception("Sound toggle failed.");e.soundButton.onClick.Invoke();
        typeof(AnatomyExplorer).GetField("targetYaw",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(e,85f);
        await Task.Delay(700);
        if(Quaternion.Angle(e.body.rotation,Quaternion.identity)<40) throw new System.Exception("Rotation did not advance.");
        e.resetButton.onClick.Invoke();await Task.Delay(1000);
        if(Quaternion.Angle(e.body.rotation,Quaternion.identity)>2) throw new System.Exception("Reset did not settle.");
        foreach(var renderer in Object.FindObjectsByType<Renderer>())
            if(renderer.sharedMaterial!=null && renderer.sharedMaterial.name=="Default-Material") throw new System.Exception("Default material: "+renderer.name);
        if(!e.viewCamera.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>().renderPostProcessing) throw new System.Exception("Camera post-processing disabled.");
        var volume=Object.FindAnyObjectByType<UnityEngine.Rendering.Volume>();
        if(volume==null || volume.sharedProfile.components.Count<4) throw new System.Exception("Volume baseline missing.");
        e.SelectTopic(0);
        Debug.Log("[AnatomyExplorer Verification] PASS: 5 topic buttons/explanations; 5 organ click-target groups; progress; help; sound; animated rotation; reset; materials; post-processing.");
        return "PASS: all five topics, organ targets, help, sound, progress, rotation, reset and rendering baseline.";
    }
}


