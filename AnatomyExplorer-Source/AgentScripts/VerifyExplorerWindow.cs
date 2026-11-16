using UnityEngine;
using System.Threading.Tasks;
using System.Reflection;
public static class VerifyExplorerWindow
{
    public static async Task<string> All()
    {
        var e=Object.FindAnyObjectByType<AnatomyExplorer>();
        if(!Application.isPlaying)throw new System.Exception("Run in Play mode.");
        e.SelectTopic(1);
        if(!e.IsExplanationOpen||e.heading.text!="Heart")throw new System.Exception("Explanation window failed to open.");
        var panel=(RectTransform)e.heading.transform.parent;
        if(panel.anchorMax.x-panel.anchorMin.x<.65f||panel.anchorMax.y-panel.anchorMin.y<.75f)throw new System.Exception("Explanation window too small.");
        e.closeExplanationButton.onClick.Invoke();
        if(e.IsExplanationOpen)throw new System.Exception("Close button failed.");
        e.ResetView();await Task.Delay(500);
        float cameraBefore=e.viewCamera.transform.position.z;
        e.ZoomByScroll(1);float normalized=e.ZoomDistance;
        await Task.Delay(700);
        if(Mathf.Abs(e.viewCamera.transform.position.z-cameraBefore)<.35f)throw new System.Exception("Actual camera did not zoom.");
        e.ResetView();e.ZoomByScroll(120);
        if(Mathf.Abs(e.ZoomDistance-normalized)>.001f)throw new System.Exception("Wheel units are inconsistent.");
        e.ZoomByScroll(-120);
        if(Mathf.Abs(e.ZoomDistance-7.2f)>.001f)throw new System.Exception("Zoom out failed.");
        Vector3 center=e.RotationCenterWorld,rootPosition=e.body.position;
        bool rootAlreadyCentered=Vector3.Distance(rootPosition,center)<.05f;
        typeof(AnatomyExplorer).GetField("targetPitch",BindingFlags.NonPublic|BindingFlags.Instance).SetValue(e,30f);
        typeof(AnatomyExplorer).GetField("targetYaw",BindingFlags.NonPublic|BindingFlags.Instance).SetValue(e,55f);
        await Task.Delay(900);
        if(Vector3.Distance(center,e.RotationCenterWorld)>.001f)throw new System.Exception("Rotation center moved.");
        if(!rootAlreadyCentered&&Vector3.Distance(rootPosition,e.body.position)<.2f)throw new System.Exception("Body still rotates at its original feet pivot.");
        if(Quaternion.Angle(e.body.rotation,Quaternion.identity)<30)throw new System.Exception("Rotation did not advance.");
        e.ResetView();await Task.Delay(800);e.SelectTopic(1);
        Debug.Log("[Explorer Controls] PASS: large modal and Close button; normalized and legacy wheel units; actual camera zoom; fixed body-center pivot under yaw and pitch.");
        return "PASS: modal, close, zoom in/out, actual camera motion and center pivot.";
    }
}
