using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Events;

/// <summary>
/// Bridge between the Unity scene and the OrbitCare blood and immune monitor,
/// which is an HTML overlay drawn on top of the WebGL canvas.
///
/// Put this component on a GameObject named exactly "OrbitCareBridge" so the
/// page can reach it:
///     unityInstance.SendMessage('OrbitCareBridge', 'OnMonitorOpen', '1')
///
/// Outside WebGL player builds every outbound call is a no-op, so the scene
/// still runs in the editor and on other platforms.
/// </summary>
public class WebBridge : MonoBehaviour
{
    public static WebBridge Instance { get; private set; }

    [Tooltip("Raised when the web overlay opens (true) or closes (false) the monitor.")]
    public UnityEvent<bool> monitorVisibilityChanged;

    [Tooltip("Set by the immune topic when it opens the monitor; lets other systems react.")]
    public bool MonitorVisible { get; private set; }

#if UNITY_WEBGL && !UNITY_EDITOR
    [DllImport("__Internal")] private static extern void OrbitCare_Open();
    [DllImport("__Internal")] private static extern void OrbitCare_Close();
    [DllImport("__Internal")] private static extern void OrbitCare_Toggle();
#endif

    void Awake()
    {
        Instance = this;
    }

    public static void OpenMonitor()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        OrbitCare_Open();
#endif
    }

    public static void CloseMonitor()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        OrbitCare_Close();
#endif
    }

    public static void ToggleMonitor()
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        OrbitCare_Toggle();
#endif
    }

    /// <summary>Called from the page when the overlay opens or closes.</summary>
    public void OnMonitorOpen(string state)
    {
        bool open = state == "1"
                    || string.Equals(state, "true", System.StringComparison.OrdinalIgnoreCase);
        MonitorVisible = open;
        monitorVisibilityChanged?.Invoke(open);
        Debug.Log("[OrbitCare] monitor visible = " + open);
    }
}
