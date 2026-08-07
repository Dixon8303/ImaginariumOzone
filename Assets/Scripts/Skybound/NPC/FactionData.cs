using Skybound.World;

namespace Skybound.NPC
{
    public enum FactionId
    {
        OyaCoalition,       // founding sky-nation, trade-focused, warm
        KemiNavigators,     // ancestral cartographers, discovery-focused
        AmaraFreeholds,     // decentralized resistance, anti-imperial
        ImperialSyndicate,  // antagonist faction — control + suppression
        VoidWalkers         // mythic tier — entities beyond the imperial maps
    }

    public enum FactionStanding
    {
        Hostile   = -2,
        Wary      = -1,
        Neutral   =  0,
        Friendly  =  1,
        Allied    =  2
    }

    /// <summary>
    /// Static faction profile. Defines which biomes a faction inhabits,
    /// their attitude toward the player, and what dialogue tone they carry.
    /// </summary>
    public static class FactionProfiles
    {
        public static string GetGreeting(FactionId faction, FactionStanding standing) =>
            (faction, standing) switch
            {
                (FactionId.OyaCoalition, FactionStanding.Allied)   =>
                    "Captain. The coalition's routes are yours. What do you need?",
                (FactionId.OyaCoalition, FactionStanding.Friendly) =>
                    "We've heard your name on the trade winds. You're welcome here.",
                (FactionId.OyaCoalition, FactionStanding.Neutral)  =>
                    "State your business. We don't stop ships without reason.",
                (FactionId.OyaCoalition, FactionStanding.Wary)     =>
                    "Slow your approach. Our gunners are watching.",

                (FactionId.KemiNavigators, FactionStanding.Allied)   =>
                    "The stars know you now. Come — there's a map I want to show you.",
                (FactionId.KemiNavigators, FactionStanding.Friendly) =>
                    "Your atlas grows. The ancestors are pleased.",
                (FactionId.KemiNavigators, FactionStanding.Neutral)  =>
                    "We trade in knowledge, not gold. What have you found?",
                (FactionId.KemiNavigators, FactionStanding.Wary)     =>
                    "We don't share charts with those who've sold routes to the empire.",

                (FactionId.AmaraFreeholds, FactionStanding.Allied)   =>
                    "Signal received. The resistance is with you.",
                (FactionId.AmaraFreeholds, FactionStanding.Friendly) =>
                    "You've earned your place in the free sky. What's the heading?",
                (FactionId.AmaraFreeholds, FactionStanding.Neutral)  =>
                    "Freeholds don't ask where you're from. Only where you're going.",
                (FactionId.AmaraFreeholds, FactionStanding.Hostile)  =>
                    "Imperial collaborators don't dock here. Turn around.",

                (FactionId.ImperialSyndicate, FactionStanding.Neutral)  =>
                    "Vessel identified. Present your navigation permit or be boarded.",
                (FactionId.ImperialSyndicate, FactionStanding.Wary)     =>
                    "You're flagged in our registry. This is your final warning.",
                (FactionId.ImperialSyndicate, FactionStanding.Hostile)  =>
                    "Unauthorized vessel. Imperial authority is now in effect.",

                (FactionId.VoidWalkers, _) =>
                    "You found us. Most don't. The question is what you do with that.",

                _ => "..."
            };

        public static SkyBiome[] HomeBiomes(FactionId faction) => faction switch
        {
            FactionId.OyaCoalition     => new[] { SkyBiome.TradeWinds },
            FactionId.KemiNavigators   => new[] { SkyBiome.AncestorFields, SkyBiome.CelestialRuin },
            FactionId.AmaraFreeholds   => new[] { SkyBiome.StormRift, SkyBiome.Uncharted },
            FactionId.ImperialSyndicate=> new[] { SkyBiome.ImperialCorridor },
            FactionId.VoidWalkers      => new[] { SkyBiome.VoidAnomaly },
            _                          => new[] { SkyBiome.Uncharted }
        };
    }
}
