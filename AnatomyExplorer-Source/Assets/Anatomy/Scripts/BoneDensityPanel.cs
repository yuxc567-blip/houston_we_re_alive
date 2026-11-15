using System;
using System.Globalization;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

public sealed class BoneDensityPanel
{
    [Serializable]
    sealed class Report
    {
        public float baseline, current, deviation, error;
        public string date, urgency_level, intervention_status, prevention;
    }

    readonly RectTransform chart;
    public string Details { get; }

    public BoneDensityPanel(TMP_Text explanation)
    {
        RectTransform area = explanation.rectTransform;
        chart = Place("Bone density chart", area.parent, area.anchorMin, area.anchorMax);
        chart.offsetMin = area.offsetMin;
        chart.offsetMax = area.offsetMax;
        chart.SetSiblingIndex(area.GetSiblingIndex());

        TextAsset asset = Resources.Load<TextAsset>("BoneDensityReport");
        Report report = asset == null ? null : JsonUtility.FromJson<Report>(asset.text);
        if (report == null || report.baseline <= 0 || string.IsNullOrEmpty(report.date))
        {
            Label("Bone density report unavailable", explanation, Vector2.zero, Vector2.one);
            Details = "Generate a report with python test.py --unity-report.";
        }
        else
        {
            float max = Mathf.Max(report.baseline, report.current);
            AddBar("Baseline", report.baseline, max, .56f, Palette.Accent, explanation);
            AddBar("Reading", report.current, max, .12f, Palette.Text, explanation);
            Details = FormattableString.Invariant(
                $"<b>Sample reading</b>  {report.date}\n<b>Urgency</b>  {report.urgency_level}\n<b>Deviation</b>  {report.deviation:0.##} (baseline − reading)  |  <b>Relative error</b>  {report.error:P1}\n<b>Action status</b>  {report.intervention_status}\n<b>Prevention</b>  {report.prevention}");
        }

        SetVisible(false);
    }

    public void SetVisible(bool visible) => chart.gameObject.SetActive(visible);

    void AddBar(string name, float value, float max, float bottom, Color fill, TMP_Text style)
    {
        Label(name, style, new Vector2(0, bottom), new Vector2(.24f, bottom + .29f));
        Label(value.ToString("0.##", CultureInfo.InvariantCulture), style,
            new Vector2(.87f, bottom), new Vector2(1, bottom + .29f));

        RectTransform track = Place(name + " track", chart,
            new Vector2(.25f, bottom + .075f), new Vector2(.84f, bottom + .215f));
        AddImage(track, Palette.Panel);
        RectTransform bar = Place(name + " bar", track, Vector2.zero,
            new Vector2(Mathf.Clamp01(value / max), 1));
        AddImage(bar, fill);
    }

    void Label(string value, TMP_Text style, Vector2 min, Vector2 max)
    {
        RectTransform bounds = Place(value, chart, min, max);
        var label = bounds.gameObject.AddComponent<TextMeshProUGUI>();
        label.text = value;
        label.font = style.font;
        label.color = style.color;
        label.enableAutoSizing = true;
        label.fontSizeMin = 12;
        label.fontSizeMax = 24;
        label.alignment = TextAlignmentOptions.MidlineLeft;
        label.raycastTarget = false;
    }

    static void AddImage(RectTransform rect, Color color)
    {
        var image = rect.gameObject.AddComponent<Image>();
        image.color = color;
        image.raycastTarget = false;
    }

    static RectTransform Place(string name, Transform parent, Vector2 min, Vector2 max)
    {
        var rect = (RectTransform)new GameObject(name, typeof(RectTransform)).transform;
        rect.SetParent(parent, false);
        rect.anchorMin = min;
        rect.anchorMax = max;
        rect.offsetMin = rect.offsetMax = Vector2.zero;
        return rect;
    }
}

