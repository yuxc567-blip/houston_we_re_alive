/// <summary>Stable topic IDs used by existing scene buttons and organ meshes.</summary>
public static class AnatomyTopics
{
    // Stable ids. Scene buttons and organ meshes already rely on this order.
    public const int Brain = 0;
    public const int Heart = 1;
    public const int Bones = 2;
    public const int Eyes = 3;
    public const int ImmuneSystem = 4;

    public static readonly IAnatomyTopic[] All =
    {
        new BrainTopic(),       // 0
        new HeartTopic(),       // 1
        new BoneDensityTopic(), // 2: existing Bones meshes and button
        new EyesTopic(),        // 3
        new ImmuneSystemTopic() // 4
    };
}
