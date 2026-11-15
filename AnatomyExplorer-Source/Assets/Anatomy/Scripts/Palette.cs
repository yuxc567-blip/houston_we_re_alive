using UnityEngine;

public static class Palette
{
    public static Color Hex(string value) { ColorUtility.TryParseHtmlString(value, out var c); return c; }
    public static readonly Color Background = Hex("#0B1724"), Panel = Hex("#142C3D"),
        Body = Hex("#8CAEB9"), Bone = Hex("#F0DFC0"), Brain = Hex("#C99ECF"),
        Heart = Hex("#EE7776"), Accent = Hex("#58D8C5"), Text = Hex("#E3F0EF");
}
