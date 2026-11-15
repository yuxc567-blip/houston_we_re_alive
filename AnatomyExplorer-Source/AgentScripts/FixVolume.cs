using UnityEngine;
using UnityEditor;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
public static class FixVolume
{
    public static string All()
    {
        var profile=AssetDatabase.LoadAssetAtPath<VolumeProfile>("Assets/Anatomy/GalleryVolume.asset");
        profile.components.RemoveAll(c=>c==null);
        if(!profile.TryGet<Tonemapping>(out var tone))tone=profile.Add<Tonemapping>(true);
        tone.mode.Override(TonemappingMode.ACES);
        if(!profile.TryGet<Bloom>(out var bloom))bloom=profile.Add<Bloom>(true);
        bloom.intensity.Override(.3f);bloom.threshold.Override(1.1f);
        if(!profile.TryGet<Vignette>(out var vignette))vignette=profile.Add<Vignette>(true);
        vignette.intensity.Override(.2f);
        if(!profile.TryGet<ColorAdjustments>(out var color))color=profile.Add<ColorAdjustments>(true);
        color.contrast.Override(5);color.saturation.Override(8);
        foreach(var component in profile.components){if(!AssetDatabase.Contains(component))AssetDatabase.AddObjectToAsset(component,profile);EditorUtility.SetDirty(component);}
        EditorUtility.SetDirty(profile);AssetDatabase.SaveAssets();
        return "Persisted "+profile.components.Count+" Volume overrides as subassets.";
    }
}
