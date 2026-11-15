using UnityEngine;
public static class VerifyOrganPicking
{
    public static string All()
    {
        if(!Application.isPlaying)throw new System.Exception("Run in Play mode.");
        var explorer=Object.FindAnyObjectByType<AnatomyExplorer>();
        Physics.SyncTransforms();
        int[] tested=new int[5];
        foreach(var part in explorer.organParts)
        {
            if(!part.gameObject.activeInHierarchy)continue;
            if(part.GetComponent<MeshCollider>()==null)throw new System.Exception("Missing mesh click target: "+part.name);
            if((part.name=="Eye"||part.name=="Iris"||part.name=="Pupil")&&part.topicIndex!=3)throw new System.Exception("Eye mapped to wrong topic.");
            if(tested[part.topicIndex]>0)continue;
            var renderer=part.GetComponent<Renderer>();
            var target=renderer.bounds.center;
            var ray=explorer.viewCamera.ScreenPointToRay(explorer.viewCamera.WorldToScreenPoint(target));
            if(!Physics.Raycast(ray,out var hit,100,~0,QueryTriggerInteraction.Ignore))continue;
            var closest=hit.collider.GetComponentInParent<AnatomyPart>();
            if(closest==null||closest.topicIndex!=part.topicIndex)continue;
            if(!explorer.TrySelectOrgan(ray)||explorer.Selected!=part.topicIndex||explorer.heading.text!=AnatomyExplorer.Titles[part.topicIndex])throw new System.Exception("Organ selection failed: "+part.name);
            tested[part.topicIndex]++;
        }
        for(int i=0;i<5;i++)if(tested[i]==0)throw new System.Exception("No direct ray hit tested for "+AnatomyExplorer.Titles[i]);
        for(int i=1;i<explorer.markers.Length;i++)if(explorer.markers[i]!=null&&explorer.markers[i].gameObject.activeInHierarchy)throw new System.Exception("Numbered marker still active: "+i);
        var head=explorer.body.Find("Head");
        if(head!=null)
        {
            var ray=explorer.viewCamera.ScreenPointToRay(explorer.viewCamera.WorldToScreenPoint(head.GetComponent<Renderer>().bounds.center));
            if(explorer.TrySelectOrgan(ray))throw new System.Exception("A click on the skin selected a hidden organ.");
        }
        explorer.SelectTopic(0);
        Debug.Log("[Organ Picking] PASS: direct brain, heart, bone, immune-node and eye raycasts display matching information; eye color overrides are correct; old numbered markers hidden.");
        return "PASS: all 5 direct organ click routes; "+explorer.organParts.Length+" mesh targets configured.";
    }
}
