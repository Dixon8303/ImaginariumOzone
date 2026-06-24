namespace Skybound.Core
{
    public enum SkyLayer { LowSky, MidSky, HighSky, VoidSky }

    public enum PerkType { Accuracy, Damage, Cooldown, Repair, Evasion }

    public enum EventType { Combat, Discovery, Environmental, Mythic }

    public readonly struct ShipState
    {
        public readonly SkyLayer Layer;
        public readonly float HullIntegrity01;
        public readonly int CrewCount;
        public readonly int ShipLevel;
        public readonly bool InCombat;

        public ShipState(SkyLayer layer, float hull, int crew, int level, bool inCombat)
        {
            Layer = layer;
            HullIntegrity01 = hull;
            CrewCount = crew;
            ShipLevel = level;
            InCombat = inCombat;
        }
    }

    public readonly struct EventOutcome
    {
        public readonly bool Success;
        public readonly string LogText;
        public readonly float CrewBonusApplied;

        public EventOutcome(bool success, string logText, float crewBonus = 0f)
        {
            Success = success;
            LogText = logText;
            CrewBonusApplied = crewBonus;
        }
    }
}
