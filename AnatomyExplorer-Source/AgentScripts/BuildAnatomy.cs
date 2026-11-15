using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;
using UnityEngine.InputSystem.UI;
using TMPro;
using Unity.Cinemachine;

public static class BuildAnatomy
{
    static Transform body;
    static Material skin, bone, pink, red, mint, dark;
    static TMP_FontAsset font;
    public static string All()
    {
        EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
        if (!AssetDatabase.IsValidFolder("Assets/Anatomy")) AssetDatabase.CreateFolder("Assets", "Anatomy");
        if (!AssetDatabase.IsValidFolder("Assets/Anatomy/Materials")) AssetDatabase.CreateFolder("Assets/Anatomy", "Materials");
        if (!System.IO.File.Exists("Assets/TextMesh Pro/Resources/Fonts & Materials/LiberationSans SDF.asset"))
            TMPro.TMP_PackageResourceImporter.ImportResources(true, false, false);
        AssetDatabase.Refresh();
        font = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>("Assets/TextMesh Pro/Resources/Fonts & Materials/LiberationSans SDF.asset");
        if (font == null) throw new System.Exception("TMP font import did not complete.");
        var manager = new GameObject("Anatomy Explorer").AddComponent<AnatomyExplorer>();
        skin = Mat("Body", Palette.Body); bone = Mat("Bone", Palette.Bone);
        pink = Mat("Brain", Palette.Brain); red = Mat("Heart", Palette.Heart);
        mint = Mat("Immune", Palette.Accent); dark = Mat("Display", Palette.Panel);
        body = new GameObject("Rotatable human body").transform;
        body.position = new Vector3(-.35f, 0, 0);
        manager.body = body;
        // A continuous torso mesh gives the silhouette shoulders, waist and hips.
        Torso();
        Sphere("Head", new Vector3(0, 4.08f, 0), new Vector3(.53f,.70f,.48f), skin);
        Link("Neck", new Vector3(0,3.56f,0), new Vector3(0,3.82f,0), .17f, skin);
        Sphere("Jaw", new Vector3(0,3.90f,-.08f), new Vector3(.39f,.26f,.32f), skin);
        Sphere("Nose", new Vector3(0,4.06f,-.255f), new Vector3(.09f,.13f,.09f), skin);
        for (int side=-1; side<=1; side+=2) {
            Sphere("Ear", new Vector3(side*.28f,4.07f,0), new Vector3(.10f,.18f,.10f), skin);
            Link("Upper arm", new Vector3(side*.54f,3.48f,0),new Vector3(side*.80f,2.82f,0),.15f,skin);
            Sphere("Elbow",new Vector3(side*.80f,2.82f,0),Vector3.one*.23f,skin);
            Link("Forearm",new Vector3(side*.80f,2.82f,0),new Vector3(side*.94f,2.20f,-.03f),.11f,skin);
            Sphere("Hand",new Vector3(side*.97f,2.04f,-.02f),new Vector3(.18f,.30f,.13f),skin);
            for(int f=0;f<4;f++) Link("Finger",new Vector3(side*(.91f+f*.04f),1.98f,-.025f),new Vector3(side*(.91f+f*.05f),1.79f+Mathf.Abs(f-1)*.025f,-.025f),.021f,skin);
            Link("Thumb",new Vector3(side*.89f,2.08f,-.03f),new Vector3(side*.84f,1.94f,-.09f),.037f,skin);
            Link("Thigh",new Vector3(side*.25f,2.23f,0),new Vector3(side*.26f,1.30f,0),.22f,skin);
            Sphere("Knee",new Vector3(side*.26f,1.30f,-.02f),Vector3.one*.31f,skin);
            Link("Shin",new Vector3(side*.26f,1.30f,0),new Vector3(side*.29f,.35f,.02f),.135f,skin);
            Sphere("Foot",new Vector3(side*.29f,.21f,-.14f),new Vector3(.27f,.22f,.53f),skin);
            // Skeleton is a diagram overlay, deliberately legible rather than hidden inside skin.
            Link("Femur diagram",new Vector3(side*.25f,2.17f,-.20f),new Vector3(side*.26f,1.32f,-.18f),.046f,bone);
            Link("Tibia diagram",new Vector3(side*.26f,1.24f,-.15f),new Vector3(side*.29f,.40f,-.13f),.032f,bone);
            Link("Humerus diagram",new Vector3(side*.57f,3.43f,-.13f),new Vector3(side*.79f,2.87f,-.12f),.032f,bone);
            Link("Radius diagram",new Vector3(side*.81f,2.76f,-.11f),new Vector3(side*.93f,2.25f,-.10f),.022f,bone);
            Sphere("Eye",new Vector3(side*.125f,4.14f,-.217f),new Vector3(.12f,.09f,.065f),bone);
            Sphere("Iris",new Vector3(side*.125f,4.14f,-.251f),new Vector3(.05f,.06f,.022f),mint);
            Sphere("Pupil",new Vector3(side*.125f,4.14f,-.265f),new Vector3(.025f,.035f,.012f),dark);
        }
        // Rib arcs and vertebrae form a recognizable skeletal diagram.
        for(int j=0;j<7;j++) {
            float y=3.43f-j*.105f, width=.38f-j*.019f;
            for(int s=-1;s<=1;s+=2) {
                Vector3 last=new Vector3(0,y,-.24f);
                for(int k=1;k<=9;k++) {
                    float t=k/9f;
                    Vector3 next=new Vector3(s*width*Mathf.Sin(t*Mathf.PI*.7f), y-.075f*Mathf.Sin(t*Mathf.PI), -.24f+.11f*t);
                    Link("Rib",last,next,.016f,bone); last=next;
                }
            }
        }
        for(int j=0;j<13;j++) Sphere("Vertebra",new Vector3(0,3.52f-j*.09f,-.21f),new Vector3(.09f,.065f,.07f),bone);
        Link("Left collarbone",new Vector3(0,3.55f,-.20f),new Vector3(-.47f,3.50f,-.15f),.022f,bone);
        Link("Right collarbone",new Vector3(0,3.55f,-.20f),new Vector3(.47f,3.50f,-.15f),.022f,bone);
        // Brain hemispheres with shallow gyri.
        for(int s=-1;s<=1;s+=2) {
            Sphere("Brain hemisphere",new Vector3(s*.105f,4.36f,-.15f),new Vector3(.23f,.23f,.23f),pink);
            for(int j=0;j<5;j++) Sphere("Brain fold",new Vector3(s*(.055f+(j%2)*.06f),4.30f+j*.028f,-.265f),new Vector3(.13f,.028f,.025f),pink);
        }
        Sphere("Heart left lobe",new Vector3(.105f,3.24f,-.29f),new Vector3(.17f,.18f,.13f),red);
        Sphere("Heart right lobe",new Vector3(.23f,3.24f,-.29f),new Vector3(.15f,.17f,.13f),red);
        var tip=Sphere("Heart tapered muscle",new Vector3(.17f,3.12f,-.29f),new Vector3(.16f,.24f,.13f),red);
        tip.transform.localRotation=Quaternion.Euler(0,0,-24);
        Link("Aorta diagram",new Vector3(.14f,3.30f,-.28f),new Vector3(.12f,3.43f,-.27f),.039f,red);
        foreach(var p in new[]{new Vector3(-.18f,3.72f,-.13f),new Vector3(.18f,3.72f,-.13f),new Vector3(-.50f,3.32f,-.10f),new Vector3(.50f,3.32f,-.10f),new Vector3(-.23f,2.25f,-.19f),new Vector3(.23f,2.25f,-.19f)})
            Sphere("Representative lymph nodes",p,Vector3.one*.075f,mint);
        manager.markers = new Transform[5];
        Vector3[] positions={new Vector3(-.35f,4.41f,-.35f),new Vector3(.40f,3.22f,-.40f),new Vector3(-.48f,1.70f,-.35f),new Vector3(.39f,4.10f,-.35f),new Vector3(-.70f,3.30f,-.35f)};
        Material[] materials={pink,red,bone,mint,mint};
        for(int i=0;i<5;i++) {
            var marker=Sphere("Marker "+(i+1)+" "+AnatomyExplorer.Titles[i],positions[i],Vector3.one*.15f,materials[i]);
            marker.AddComponent<SphereCollider>(); manager.markers[i]=marker.transform;
            var label=new GameObject("Marker number").AddComponent<TextMeshPro>(); label.transform.SetParent(marker.transform,false);
            label.transform.localPosition=new Vector3(0,0,-.56f);label.transform.localScale=Vector3.one;
            label.text=(i+1).ToString();label.font=font;label.fontSize=8;label.alignment=TextAlignmentOptions.Center;label.color=Palette.Background;
            label.rectTransform.sizeDelta=new Vector2(2,2);label.fontStyle=FontStyles.Bold;
        }
        var pedestal=GameObject.CreatePrimitive(PrimitiveType.Cylinder);pedestal.name="Gallery pedestal";pedestal.transform.position=new Vector3(-.35f,.015f,0);pedestal.transform.localScale=new Vector3(1.5f,.06f,1.2f);pedestal.GetComponent<Renderer>().sharedMaterial=dark;Object.DestroyImmediate(pedestal.GetComponent<Collider>());
        var cam=new GameObject("Main Camera").AddComponent<Camera>();cam.tag="MainCamera";
        cam.transform.position=new Vector3(0,2.25f,-7.2f);cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=Palette.Background;cam.fieldOfView=43;cam.allowHDR=true;
        cam.gameObject.AddComponent<AudioListener>();cam.gameObject.AddComponent<CinemachineBrain>();
        var virtualCamera=new GameObject("Inspection camera").AddComponent<CinemachineCamera>();
        virtualCamera.transform.position=cam.transform.position;virtualCamera.Lens.FieldOfView=43;
        manager.cameraRig=virtualCamera.transform; manager.viewCamera=cam;
        var data=cam.GetUniversalAdditionalCameraData();data.renderPostProcessing=true;data.volumeLayerMask=1;
        var pipeline=GraphicsSettings.currentRenderPipeline as UniversalRenderPipelineAsset;
        if(pipeline==null) throw new System.Exception("Expected active URP.");pipeline.supportsHDR=true;
        QualitySettings.SetQualityLevel(QualitySettings.names.Length-1);
        Light("Warm key",new Vector3(35,-30,0),Palette.Bone,1.3f);
        Light("Cool fill",new Vector3(25,140,0),Palette.Body,.7f);
        RenderSettings.skybox=null;RenderSettings.ambientMode=AmbientMode.Trilight;
        RenderSettings.ambientSkyColor=Palette.Body*.45f;RenderSettings.ambientEquatorColor=Palette.Panel;RenderSettings.ambientGroundColor=Palette.Background;
        var profile=ScriptableObject.CreateInstance<VolumeProfile>();
        profile.Add<Tonemapping>(true).mode.value=TonemappingMode.ACES;
        var bloom=profile.Add<Bloom>(true);bloom.intensity.value=.3f;bloom.threshold.value=1.1f;
        profile.Add<Vignette>(true).intensity.value=.2f;
        var adjustments=profile.Add<ColorAdjustments>(true);adjustments.contrast.value=5;adjustments.saturation.value=8;
        AssetDatabase.CreateAsset(profile,"Assets/Anatomy/GalleryVolume.asset");
        foreach(var component in profile.components) AssetDatabase.AddObjectToAsset(component,profile);
        EditorUtility.SetDirty(profile);
        var volume=new GameObject("Gallery grading").AddComponent<Volume>();volume.isGlobal=true;volume.sharedProfile=profile;
        UI(manager,cam);
        EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene(),"Assets/Anatomy/AnatomyExplorer.unity");
        EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene("Assets/Anatomy/AnatomyExplorer.unity",true)};
        PlayerSettings.productName="Anatomy Explorer";PlayerSettings.defaultScreenWidth=1600;PlayerSettings.defaultScreenHeight=1000;
        AssetDatabase.SaveAssets();return "Anatomy explorer scene built and saved.";
    }

    static Material Mat(string name,Color color) {
        var m=new Material(GraphicsSettings.currentRenderPipeline.defaultMaterial);m.name=name;m.color=color;
        m.SetFloat("_Smoothness",.30f);AssetDatabase.CreateAsset(m,"Assets/Anatomy/Materials/"+name+".mat");return m;
    }
    static GameObject Sphere(string name,Vector3 pos,Vector3 scale,Material mat) {
        var o=GameObject.CreatePrimitive(PrimitiveType.Sphere);o.name=name;o.transform.SetParent(body,false);o.transform.localPosition=pos;o.transform.localScale=scale;o.GetComponent<Renderer>().sharedMaterial=mat;Object.DestroyImmediate(o.GetComponent<Collider>());return o;
    }
    static void Link(string name,Vector3 a,Vector3 b,float radius,Material mat) {
        var o=GameObject.CreatePrimitive(PrimitiveType.Capsule);o.name=name;o.transform.SetParent(body,false);o.transform.localPosition=(a+b)/2;o.transform.up=(b-a).normalized;o.transform.localScale=new Vector3(radius*2,(b-a).magnitude/2+radius,radius*2);o.GetComponent<Renderer>().sharedMaterial=mat;Object.DestroyImmediate(o.GetComponent<Collider>());
    }
    static void Torso() {
        float[] y={2.12f,2.30f,2.55f,2.85f,3.10f,3.36f,3.52f,3.60f};
        float[] w={.28f,.40f,.34f,.30f,.39f,.46f,.51f,.23f};
        float[] d={.20f,.24f,.21f,.20f,.23f,.24f,.19f,.14f};
        var vertices=new System.Collections.Generic.List<Vector3>();var triangles=new System.Collections.Generic.List<int>();
        const int segments=40;
        for(int r=0;r<y.Length;r++)for(int j=0;j<segments;j++){float t=j*Mathf.PI*2/segments;vertices.Add(new Vector3(Mathf.Cos(t)*w[r],y[r],Mathf.Sin(t)*d[r]));}
        for(int r=0;r<y.Length-1;r++)for(int j=0;j<segments;j++){int a=r*segments+j,b=r*segments+(j+1)%segments,c=a+segments,e=b+segments;triangles.AddRange(new[]{a,c,b,b,c,e});}
        var mesh=new Mesh();mesh.name="Sculpted torso";mesh.SetVertices(vertices);mesh.SetTriangles(triangles,0);mesh.RecalculateNormals();
        AssetDatabase.CreateAsset(mesh,"Assets/Anatomy/Torso.asset");
        var obj=new GameObject("Torso");obj.transform.SetParent(body,false);obj.AddComponent<MeshFilter>().sharedMesh=mesh;obj.AddComponent<MeshRenderer>().sharedMaterial=skin;
    }
    static void Light(string name,Vector3 angles,Color tint,float intensity) {var l=new GameObject(name).AddComponent<Light>();l.type=LightType.Directional;l.color=tint;l.intensity=intensity;l.shadows=LightShadows.Soft;l.transform.rotation=Quaternion.Euler(angles);}

    static RectTransform Rect(string name,Transform parent,Vector2 min,Vector2 max,Vector2 insetMin,Vector2 insetMax) {
        var r=new GameObject(name,typeof(RectTransform)).GetComponent<RectTransform>();r.SetParent(parent,false);r.anchorMin=min;r.anchorMax=max;r.offsetMin=insetMin;r.offsetMax=insetMax;return r;
    }
    static TMP_Text Text(string name,Transform parent,string value,int size,Vector2 min,Vector2 max) {
        var r=Rect(name,parent,min,max,new Vector2(12,4),new Vector2(-12,-4));var t=r.gameObject.AddComponent<TextMeshProUGUI>();t.font=font;t.text=value;t.fontSize=size;t.color=Palette.Text;t.raycastTarget=false;t.characterSpacing=1;t.fontStyle=size>=26?FontStyles.Bold:FontStyles.Normal;t.textWrappingMode=TextWrappingModes.Normal;return t;
    }
    static UnityEngine.UI.Button Button(string name,Transform parent,string value,Vector2 min,Vector2 max) {
        var r=Rect(name,parent,min,max,new Vector2(10,5),new Vector2(-10,-5));var image=r.gameObject.AddComponent<UnityEngine.UI.Image>();image.color=Palette.Panel;
        var b=r.gameObject.AddComponent<UnityEngine.UI.Button>();var colors=b.colors;colors.highlightedColor=Palette.Body;colors.pressedColor=Palette.Accent;colors.selectedColor=Palette.Body;b.colors=colors;
        var t=Text("Label",r,value,21,Vector2.zero,Vector2.one);t.alignment=TextAlignmentOptions.MidlineLeft;return b;
    }
    static void UI(AnatomyExplorer m,Camera cam) {
        var canvas=new GameObject("Explorer UI",typeof(RectTransform)).AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceCamera;canvas.worldCamera=cam;canvas.planeDistance=1;
        var scaler=canvas.gameObject.AddComponent<UnityEngine.UI.CanvasScaler>();scaler.uiScaleMode=UnityEngine.UI.CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1600,1000);scaler.matchWidthOrHeight=.5f;
        canvas.gameObject.AddComponent<UnityEngine.UI.GraphicRaycaster>();
        var es=new GameObject("EventSystem").AddComponent<UnityEngine.EventSystems.EventSystem>();es.gameObject.AddComponent<InputSystemUIInputModule>();
        Text("Brand",canvas.transform,"ANATOMY / EXPLORER",33,new Vector2(.025f,.91f),new Vector2(.70f,.98f));
        Text("Subtitle",canvas.transform,"An interactive guide to the human body",20,new Vector2(.025f,.86f),new Vector2(.70f,.92f));
        var left=Rect("Topics",canvas.transform,new Vector2(.025f,.25f),new Vector2(.205f,.79f),Vector2.zero,Vector2.zero);
        Text("Topics heading",left,"EXPLORE THE BODY",17,new Vector2(0,.91f),Vector2.one);
        m.topicButtons=new UnityEngine.UI.Button[5];
        for(int i=0;i<5;i++)m.topicButtons[i]=Button("Topic "+i,left,(i+1)+"   "+AnatomyExplorer.Titles[i],new Vector2(0,.74f-i*.15f),new Vector2(1,.87f-i*.15f));
        var right=Rect("Explanation panel",canvas.transform,new Vector2(.705f,.16f),new Vector2(.975f,.82f),Vector2.zero,Vector2.zero);
        var panel=right.gameObject.AddComponent<UnityEngine.UI.Image>();panel.color=Palette.Panel;panel.raycastTarget=false;
        Text("Panel eyebrow",right,"DISCOVER / 01—05",17,new Vector2(.04f,.91f),new Vector2(.96f,.98f));
        m.heading=Text("Topic title",right,"A body of discovery",34,new Vector2(.04f,.76f),new Vector2(.96f,.91f));
        m.explanation=Text("Summary",right,"Click an organ on the body, or choose a topic on the left.",24,new Vector2(.04f,.54f),new Vector2(.96f,.76f));
        m.detail=Text("Details",right,"Rotate the model to explore from every angle.\n\nThe colored diagrams show selected structures at simplified locations.\n\nStart with 1 — Brain.",21,new Vector2(.04f,.07f),new Vector2(.96f,.54f));
        m.detail.enableAutoSizing=true;m.detail.fontSizeMin=16;m.detail.fontSizeMax=21;
        m.progress=Text("Progress",canvas.transform,"0 / 5 topics explored",20,new Vector2(.705f,.10f),new Vector2(.975f,.15f));
        Text("Controls",canvas.transform,"DRAG to rotate   ·   SCROLL to zoom   ·   R to reset",19,new Vector2(.24f,.07f),new Vector2(.69f,.12f));
        Text("Disclaimer",canvas.transform,"Simplified educational model · Representative markers · Not for medical diagnosis",16,new Vector2(.025f,.015f),new Vector2(.97f,.06f));
        m.resetButton=Button("Reset view",canvas.transform,"Reset view",new Vector2(.025f,.16f),new Vector2(.20f,.22f));
        m.helpButton=Button("Help",canvas.transform,"Controls / help",new Vector2(.79f,.91f),new Vector2(.975f,.97f));
        m.soundButton=Button("Sound",canvas.transform,"Sound: on",new Vector2(.025f,.09f),new Vector2(.20f,.15f));
        var help=Rect("Help overlay",canvas.transform,new Vector2(.23f,.24f),new Vector2(.69f,.80f),Vector2.zero,Vector2.zero);
        help.gameObject.AddComponent<UnityEngine.UI.Image>().color=Palette.Panel;
        Text("Help title",help,"Make yourself at home",33,new Vector2(.04f,.78f),new Vector2(.96f,.94f));
        Text("Help instructions",help,"Drag the body: rotate\nScroll wheel: zoom\nArrow keys: rotate\n1–5: select an anatomy topic\nR: reset the view\nEscape: open / close this help\n\nClick the organs on the body or topic buttons to read an explanation.",23,new Vector2(.04f,.22f),new Vector2(.96f,.78f));
        m.closeHelpButton=Button("Close help",help,"Continue exploring",new Vector2(.07f,.04f),new Vector2(.93f,.19f));m.help=help.gameObject;m.help.SetActive(false);
    }
}


