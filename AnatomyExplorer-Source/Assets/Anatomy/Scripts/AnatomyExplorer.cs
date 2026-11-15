using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.EventSystems;
using TMPro;

public class AnatomyExplorer : MonoBehaviour
{
    public Transform body;
    public Camera viewCamera;
    public Transform cameraRig;
    public TMP_Text heading, explanation, detail, progress;
    public GameObject help;
    public GameObject explanationOverlay;
    public UnityEngine.UI.Button closeExplanationButton;
    public bool IsExplanationOpen => explanationOverlay != null && explanationOverlay.activeSelf;
    public float ZoomDistance => zoom;
    public Vector3 RotationCenterWorld => body.TransformPoint(rotationCenterLocal);
    public Transform[] markers;
    public AnatomyPart[] organParts;
    public UnityEngine.UI.Button[] topicButtons;
    public UnityEngine.UI.Button resetButton, helpButton, closeHelpButton, soundButton;
    public int Selected { get; private set; } = -1;
    public int VisitedCount { get; private set; }
    public bool Muted { get; private set; }
    readonly bool[] visited = new bool[5];
    Vector2 down;
    bool dragging;
    float dragStartYaw, dragStartPitch;
    InputAction pointerPress;
    readonly System.Collections.Generic.List<RaycastResult> interfaceHits = new System.Collections.Generic.List<RaycastResult>();
    float moved, yaw, pitch, targetYaw, targetPitch, zoom = 7.2f;
    AudioSource sound;
    AudioClip click;
    Vector3 rotationCenterLocal, restPosition;
    Quaternion restRotation;

    // Compatibility views for existing setup and verification helpers.
    public static string[] Titles => System.Array.ConvertAll(AnatomyTopics.All, topic => topic.Title);
    public static string[] Summaries => System.Array.ConvertAll(AnatomyTopics.All, topic => topic.Summary);
    public static string[] Details => System.Array.ConvertAll(AnatomyTopics.All, topic => topic.Details);

    void Awake()
    {
        for (int i = 0; i < topicButtons.Length; i++) { int id = i; topicButtons[i].onClick.AddListener(() => SelectTopic(id)); }
        resetButton.onClick.AddListener(ResetView);
        helpButton.onClick.AddListener(() => ToggleHelp(true));
        closeHelpButton.onClick.AddListener(() => ToggleHelp(false));
        soundButton.onClick.AddListener(ToggleSound);
        if (closeExplanationButton != null) closeExplanationButton.onClick.AddListener(CloseExplanation);
        if (explanationOverlay != null) explanationOverlay.SetActive(false);
        organParts = AnatomyPicking.Configure(body, markers);
        CacheRotationCenter();
        sound = gameObject.AddComponent<AudioSource>();
        sound.playOnAwake = false;
        click = AudioClip.Create("Soft selection", 4800, 1, 48000, false);
        float[] samples = new float[4800];
        for (int i = 0; i < samples.Length; i++) {
            float t = i / 48000f;
            float envelope = Mathf.Min(1, i / 240f) * Mathf.Min(1, (samples.Length - i) / 240f) * Mathf.Exp(-t * 40);
            samples[i] = Mathf.Sin(2 * Mathf.PI * (750 * t + 1200 * t * t)) * envelope * .16f;
        }
        click.SetData(samples, 0);
        Muted = PlayerPrefs.GetInt("AnatomyMuted", 0) == 1;
        UpdateSoundLabel();
        pointerPress = new InputAction("Inspect body", InputActionType.Button, "<Mouse>/leftButton");
        pointerPress.started += PointerDown;
        pointerPress.canceled += PointerUp;
        pointerPress.Enable();
        Debug.Log("[AnatomyExplorer] Ready: five clickable topics, drag/keyboard rotation, zoom and reset.");
    }

    public void SelectTopic(int id)
    {
        if (id < 0 || id >= AnatomyTopics.All.Length) return;
        Selected = id;
        var topic = AnatomyTopics.All[id];
        heading.text = topic.Title; explanation.text = topic.Summary; detail.text = topic.Details;
        if (explanationOverlay != null) explanationOverlay.SetActive(true);
        help.SetActive(false);
        dragging = false;
        if (!visited[id]) { visited[id] = true; VisitedCount++; }
        progress.text = VisitedCount + " / 5 topics explored";
        for (int i = 0; i < topicButtons.Length; i++) {
            topicButtons[i].GetComponent<UnityEngine.UI.Image>().color = i == id ? Palette.Accent : Palette.Panel;
            topicButtons[i].GetComponentInChildren<TMP_Text>().color = i == id ? Palette.Background : Palette.Text;
        }
        if (!Muted) sound.PlayOneShot(click);
        Debug.Log("[AnatomyExplorer] Selected " + Titles[id] + "; explanation displayed; visited=" + VisitedCount);
    }

    public void ResetView()
    {
        targetYaw = targetPitch = 0; zoom = 7.2f;
        Debug.Log("[AnatomyExplorer] View reset.");
    }
    public void CloseExplanation() { if (explanationOverlay != null) explanationOverlay.SetActive(false); dragging = false; }
    public void ToggleHelp(bool show) { if (show) CloseExplanation(); help.SetActive(show); dragging = false; }
    public void ToggleSound() { Muted = !Muted; PlayerPrefs.SetInt("AnatomyMuted", Muted ? 1 : 0); PlayerPrefs.Save(); UpdateSoundLabel(); }
    void UpdateSoundLabel() { soundButton.GetComponentInChildren<TMP_Text>().text = Muted ? "Sound: off" : "Sound: on"; }

    void CacheRotationCenter()
    {
        restPosition = body.localPosition;
        restRotation = body.localRotation;
        Bounds bounds = new Bounds();
        bool hasBounds = false;
        foreach (var renderer in body.GetComponentsInChildren<MeshRenderer>())
        {
            if (!renderer.enabled || renderer.GetComponent<TMP_Text>() != null) continue;
            bool marker = false;
            foreach (var oldMarker in markers)
                if (oldMarker != null && renderer.transform.IsChildOf(oldMarker)) marker = true;
            if (marker) continue;
            if (!hasBounds) { bounds = renderer.bounds; hasBounds = true; }
            else bounds.Encapsulate(renderer.bounds);
        }
        rotationCenterLocal = hasBounds ? body.InverseTransformPoint(bounds.center) : Vector3.zero;
    }

    public void ZoomByScroll(float wheelDelta)
    {
        if (Mathf.Approximately(wheelDelta, 0)) return;
        // Support both normalized Input System steps and legacy 120-unit wheel notches.
        float steps = Mathf.Abs(wheelDelta) >= 20 ? wheelDelta / 120f : wheelDelta;
        zoom = Mathf.Clamp(zoom - steps * .55f, 3.5f, 10f);
    }

    bool PointerOverInterface(Vector2 position)
    {
        if (EventSystem.current == null) return false;
        var data = new PointerEventData(EventSystem.current) { position = position };
        interfaceHits.Clear();
        EventSystem.current.RaycastAll(data, interfaceHits);
        foreach (var hit in interfaceHits) if (hit.module is UnityEngine.UI.GraphicRaycaster) return true;
        return false;
    }

    void PointerDown(InputAction.CallbackContext context)
    {
        if (Mouse.current == null || help.activeSelf || IsExplanationOpen) return;
        var position = Mouse.current.position.ReadValue();
        if (PointerOverInterface(position)) return;
        down = position; moved = 0; dragging = true;
        dragStartYaw = targetYaw; dragStartPitch = targetPitch;
    }

    void ApplyPointerDrag(Vector2 position)
    {
        Vector2 offset = position - down;
        moved = Mathf.Max(moved, offset.magnitude);
        if (moved <= 5) return;
        targetYaw = dragStartYaw - offset.x * .35f;
        targetPitch = dragStartPitch + offset.y * .22f;
    }

    void PointerUp(InputAction.CallbackContext context)
    {
        if (!dragging || Mouse.current == null) return;
        var position = Mouse.current.position.ReadValue();
        ApplyPointerDrag(position);
        dragging = false;
        if (moved <= 5 && !help.activeSelf && !IsExplanationOpen)
            TrySelectOrgan(viewCamera.ScreenPointToRay(position));
    }

    void OnDestroy()
    {
        if (pointerPress == null) return;
        pointerPress.started -= PointerDown;
        pointerPress.canceled -= PointerUp;
        pointerPress.Dispose();
    }

    public bool TrySelectOrgan(Ray ray)
    {
        Physics.SyncTransforms();
        if (!Physics.Raycast(ray, out var hit, 100, ~0, QueryTriggerInteraction.Ignore)) return false;
        var part = hit.collider.GetComponentInParent<AnatomyPart>();
        if (part == null) return false;
        SelectTopic(part.topicIndex);
        return true;
    }

    void Update()
    {
        var keyboard = Keyboard.current;
        if (keyboard != null) {
            if (keyboard.escapeKey.wasPressedThisFrame) {
                if (IsExplanationOpen) CloseExplanation(); else ToggleHelp(!help.activeSelf);
            }
            if (keyboard.rKey.wasPressedThisFrame) ResetView();
            var keys = new[] { keyboard.digit1Key, keyboard.digit2Key, keyboard.digit3Key, keyboard.digit4Key, keyboard.digit5Key };
            for (int i = 0; i < keys.Length; i++) if (keys[i].wasPressedThisFrame) SelectTopic(i);
            if (!help.activeSelf && !IsExplanationOpen) {
                targetYaw += ((keyboard.rightArrowKey.isPressed ? 1 : 0) - (keyboard.leftArrowKey.isPressed ? 1 : 0)) * 65 * Time.unscaledDeltaTime;
                targetPitch += ((keyboard.downArrowKey.isPressed ? 1 : 0) - (keyboard.upArrowKey.isPressed ? 1 : 0)) * 40 * Time.unscaledDeltaTime;
            }
        }
        var mouse = Mouse.current;
        if (mouse != null && !help.activeSelf && !IsExplanationOpen) {
            Vector2 pos = mouse.position.ReadValue();
            if (dragging) ApplyPointerDrag(pos);
            ZoomByScroll(mouse.scroll.ReadValue().y);
        }
        targetPitch = Mathf.Clamp(targetPitch, -35, 35);
        yaw = Mathf.Lerp(yaw, targetYaw, 1 - Mathf.Exp(-12 * Time.unscaledDeltaTime));
        pitch = Mathf.Lerp(pitch, targetPitch, 1 - Mathf.Exp(-12 * Time.unscaledDeltaTime));
        body.localRotation = restRotation * Quaternion.Euler(pitch, yaw, 0);
        Vector3 pivotOffset = Vector3.Scale(rotationCenterLocal, body.localScale);
        body.localPosition = restPosition + restRotation * pivotOffset - body.localRotation * pivotOffset;
        cameraRig.position = Vector3.Lerp(cameraRig.position, new Vector3(0, 2.25f, -zoom), 1 - Mathf.Exp(-10 * Time.unscaledDeltaTime));
    }
}

