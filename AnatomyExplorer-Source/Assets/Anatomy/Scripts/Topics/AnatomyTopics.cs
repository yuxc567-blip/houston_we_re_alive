/// <summary>Stable topic IDs used by existing scene buttons and organ meshes.</summary>
public static class AnatomyTopics
{
    public static readonly IAnatomyTopic[] All =
    {
        new BrainTopic(),       // 0
        new HeartTopic(),       // 1
        new BoneDensityTopic(), // 2: existing Bones meshes and button
        new EyesTopic(),        // 3
        new ImmuneSystemTopic() // 4
    };
}
