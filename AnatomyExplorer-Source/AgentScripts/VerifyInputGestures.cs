using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.InputSystem.LowLevel;
using System.Threading.Tasks;
public static class VerifyInputGestures
{
    public static async Task<string> All()
    {
        var e=Object.FindAnyObjectByType<AnatomyExplorer>();
        if(!Application.isPlaying)throw new System.Exception("Run in Play mode.");
        e.CloseExplanation();e.ToggleHelp(false);e.ResetView();await Task.Delay(500);
        var mouse=Mouse.current;var savedPointer=mouse.position.ReadValue();
        Vector2 start=e.viewCamera.WorldToScreenPoint(e.RotationCenterWorld);
        Quaternion original=e.body.rotation;Vector3 center=e.RotationCenterWorld;
        // Both events arrive before the next game frame: the old polling controller lost this drag.
        InputSystem.QueueStateEvent(mouse,new MouseState { position=start, buttons=1 });
        InputSystem.QueueStateEvent(mouse,new MouseState { position=start+new Vector2(100,50), buttons=0 });
        await Task.Delay(700);
        if(Quaternion.Angle(original,e.body.rotation)<20)throw new System.Exception("Fast drag events did not rotate the body.");
        if(Vector3.Distance(center,e.RotationCenterWorld)>.001f)throw new System.Exception("Fast drag moved the body center.");
        e.ResetView();await Task.Delay(500);
        float before=e.ZoomDistance;
        InputSystem.QueueDeltaStateEvent(mouse.scroll,new Vector2(0,120));
        await Task.Delay(600);
        if(before-e.ZoomDistance<.4f)throw new System.Exception("Real wheel input did not zoom.");
        InputSystem.QueueDeltaStateEvent(mouse.position,savedPointer);
        e.ResetView();await Task.Delay(500);
        Debug.Log("[Input Gestures] PASS: same-frame mouse down/up drag rotates about the body center; wheel input changes zoom.");
        return "PASS: fast drag events, centered rotation and wheel input.";
    }
}
