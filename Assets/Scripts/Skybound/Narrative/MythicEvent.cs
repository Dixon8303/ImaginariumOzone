using UnityEngine;
using Skybound.Events;
using Skybound.Core;

namespace Skybound.Narrative
{
    /// <summary>
    /// Rare, world-altering encounter that only fires when the player has
    /// decoded enough cells and enters a VoidAnomaly or CelestialRuin biome.
    /// Resolving one unlocks a LoreFragment flagged requiresMythicEvent=true
    /// and permanently alters one world parameter for the rest of the run.
    /// </summary>
    [CreateAssetMenu(menuName = "Skybound/Events/Mythic Event")]
    public class MythicEvent : EncounterData
    {
        [Header("Mythic")]
        [TextArea(2, 6)]
        public string visionText;
        public string loreFragmentId;          // unlocked on resolve
        public float  worldDangerModifier;     // +/- applied to all DangerLevel rolls this run
        public bool   revealsHiddenBiome;      // makes one Uncharted cell permanently visible

        [Header("Trigger Gate")]
        public int minimumDecodedCells = 5;    // must have decoded this many cells first

        public override EventOutcome Resolve(IShipManager ship)
        {
            var state = ship.GetState();

            // Mythic events carry a hull cost — the vision is physically harrowing
            if (state.HullIntegrity > 0.15f)
                ship.ApplyHullDamage(0.10f);

            string narrative = $"[MYTHIC] {visionText}\n" +
                               (revealsHiddenBiome
                                   ? "A hidden sky-region shimmers into view on your charts."
                                   : $"The danger of the sky shifts. ({(worldDangerModifier >= 0 ? "+" : "")}{worldDangerModifier:P0})");

            return new EventOutcome
            {
                Narrative    = narrative,
                AppliedBonus = 0.15f  // the revelation itself is a bonus
            };
        }
    }
}
