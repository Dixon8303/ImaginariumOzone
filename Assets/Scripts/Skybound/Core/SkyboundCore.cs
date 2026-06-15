namespace Skybound.Core
{
    /// <summary>
    /// High-level classification of an injected sky event.
    /// Extend here when introducing new tiers (e.g. Mythic, Rift). Selection and
    /// presentation are type-agnostic, so adding a value requires no manager changes.
    /// </summary>
    public enum EventType
    {
        Combat,
        Discovery,
        Environmental
    }

    /// <summary>Vertical world bands. Drives base risk/reward and probability weighting.</summary>
    public enum SkyLayer
    {
        LowSky,
        MidSky,
        HighSky,
        VoidSky
    }

    /// <summary>
    /// Crew perk channels. Mirrors the Crew/Gunner archetype system so bonuses
    /// stack by type when multiple crew slots are filled (dual-slot gunner model).
    /// </summary>
    public enum PerkType
    {
        Accuracy,
        Damage,
        CritChance,
        Cooldown
    }

    /// <summary>
    /// Immutable snapshot of ship/world state used to validate and weight events.
    /// Passed by value so validation logic can never mutate live ship state.
    /// </summary>
    [System.Serializable]
    public struct ShipState
    {
        public SkyLayer Layer;
        public float HullIntegrity01;   // normalized 0..1
        public int CrewCount;
        public int ShipLevel;
        public bool InCombat;

        public ShipState(SkyLayer layer, float hullIntegrity01, int crewCount, int shipLevel, bool inCombat)
        {
            Layer = layer;
            HullIntegrity01 = hullIntegrity01;
            CrewCount = crewCount;
            ShipLevel = shipLevel;
            InCombat = inCombat;
        }
    }

    /// <summary>Result of resolving an encounter. Consumed by the UI discovery/combat feed.</summary>
    public struct EventOutcome
    {
        public bool Success;
        public string LogText;
        public float AppliedBonus;   // surfaced so the UI can show which crew bonus mattered

        public EventOutcome(bool success, string logText, float appliedBonus = 0f)
        {
            Success = success;
            LogText = logText;
            AppliedBonus = appliedBonus;
        }
    }
}
