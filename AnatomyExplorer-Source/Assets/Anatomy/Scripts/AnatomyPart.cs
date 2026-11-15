using UnityEngine;

/// <summary>Connects a visible anatomy mesh to its explanation.</summary>
[DisallowMultipleComponent]
public class AnatomyPart : MonoBehaviour
{
    [Range(0, 4)] public int topicIndex;
}

public static class AnatomyPicking
{
    public static AnatomyPart[] Configure(Transform body, Transform[] oldMarkers)
    {
        var parts = new System.Collections.Generic.List<AnatomyPart>();
        foreach (var renderer in body.GetComponentsInChildren<MeshRenderer>(true))
        {
            bool isMarker = false;
            bool isBrainSphere = oldMarkers.Length > 0 && oldMarkers[0] != null && renderer.transform == oldMarkers[0];
            foreach (var marker in oldMarkers)
                if (marker != null && (renderer.transform == marker || renderer.transform.IsChildOf(marker)))
                    isMarker = true;
            if (isMarker && !isBrainSphere) continue;

            string objectName = renderer.name.ToLowerInvariant();
            string materialName = renderer.sharedMaterial == null ? "" : renderer.sharedMaterial.name.Replace(" (Instance)", "").ToLowerInvariant();
            var part = renderer.GetComponent<AnatomyPart>();
            int topic = part != null ? part.topicIndex : -1;
            // Eyes contain both white and green meshes, so their identity comes first.
            if (isBrainSphere) topic = 0;
            else if (objectName == "eye" || objectName == "iris" || objectName == "pupil" || objectName.StartsWith("eye ")) topic = 3;
            else if (materialName == "brain") topic = 0;
            else if (materialName == "heart") topic = 1;
            else if (materialName == "bone") topic = 2;
            else if (materialName == "immune") topic = 4;
            var filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null) continue;
            // Follow the actual visible mesh, including thin ribs and modified proportions.
            var collider = renderer.GetComponent<MeshCollider>();
            if (collider == null) collider = renderer.gameObject.AddComponent<MeshCollider>();
            collider.sharedMesh = filter.sharedMesh;
            collider.convex = false;
            collider.isTrigger = false;
            collider.enabled = true;
            // Skin also blocks the ray, so a miss cannot select an organ hidden behind it.
            if (topic < 0) continue;
            if (part == null) part = renderer.gameObject.AddComponent<AnatomyPart>();
            part.topicIndex = topic;
            parts.Add(part);
        }
        for (int i = 0; i < oldMarkers.Length; i++)
        {
            if (oldMarkers[i] == null) continue;
            // Keep the user's pink sphere as the visible brain representation, without its number.
            oldMarkers[i].gameObject.SetActive(i == 0);
            if (i == 0)
                foreach (var label in oldMarkers[i].GetComponentsInChildren<TMPro.TMP_Text>(true))
                    label.gameObject.SetActive(false);
        }
        return parts.ToArray();
    }
}
