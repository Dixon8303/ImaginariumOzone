using UnityEngine;
using Skybound.Events;
using Skybound.Core;

namespace Skybound.NPC
{
    /// <summary>
    /// NPC faction encounter — feeds into the GameDirector event pool alongside
    /// CombatEncounter and DiscoveryEncounter. Outcome shifts faction standing
    /// and unlocks dialogue branches that persist across the run.
    /// </summary>
    [CreateAssetMenu(menuName = "Skybound/Events/NPC Encounter")]
    public class NPCEncounter : EncounterData
    {
        [Header("Faction")]
        public FactionId  faction;
        public string     npcName     = "Unknown Courier";
        public string[]   dialogueLines;

        [Header("Outcome")]
        [Tooltip("Standing delta on a cooperative resolve (+1 = gain Friendly, etc.)")]
        public int cooperativeStandingDelta =  1;
        [Tooltip("Standing delta when player is hostile or refuses")]
        public int hostileStandingDelta     = -1;
        [Tooltip("Loot fragment unlocked on cooperative resolve")]
        public string loreReward;

        public override EventOutcome Resolve(IShipManager ship)
        {
            var state   = ship.GetState();
            bool allied = state.ShipLevel >= 3;  // high-level ships get diplomatic edge

            float roll  = Random.Range(0f, 1f);
            bool  coop  = allied || roll > 0.4f;

            int standingDelta = coop ? cooperativeStandingDelta : hostileStandingDelta;

            string dialogue = dialogueLines != null && dialogueLines.Length > 0
                ? dialogueLines[Random.Range(0, dialogueLines.Length)]
                : FactionProfiles.GetGreeting(faction, FactionStanding.Neutral);

            string result = coop
                ? $"[NPC] {npcName}: \"{dialogue}\"  — Standing with {faction} improved."
                : $"[NPC] {npcName} turned hostile. Standing with {faction} worsened.";

            return new EventOutcome
            {
                Narrative    = result,
                AppliedBonus = standingDelta * 0.05f  // small perk bonus for cooperative outcomes
            };
        }
    }
}
