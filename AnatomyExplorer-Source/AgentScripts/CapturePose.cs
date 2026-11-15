using UnityEngine;
public static class CapturePose
{
    public static string Set(int topic,float distance)
    {
        var e=Object.FindAnyObjectByType<AnatomyExplorer>();
        e.ResetView();e.SelectTopic(topic);
        typeof(AnatomyExplorer).GetField("zoom",System.Reflection.BindingFlags.NonPublic|System.Reflection.BindingFlags.Instance).SetValue(e,distance);
        return "Capture pose set.";
    }
}
