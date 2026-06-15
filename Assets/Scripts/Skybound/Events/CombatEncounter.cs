using UnityEngine;
using Skybound.Core;

namespace Skybound.Events
{
    /// <summary>
    /// Reference concrete encounter: a stat-checked aerial ambush.
    /// Demonstrates the data-driven resolution pattern — the Gunner accuracy bonus from
    /// the crew system is queried at resolve time and applied to the hit check. Copy this
    /// shape for DiscoveryEncounter, EnvironmentalEncounter, MythicEncounter, etc.
    /// </summary>
    [CreateAssetMenu(fileName = "NewCombatEncounter", menuName = "Skybound/Encounters/Combat")]
    public class CombatEncounter : EncounterData
    {
        [Header("Difficulty")]
        [SerializeField, Range(0f, 100f)] private float baseHitThreshold = 55f;
        [SerializeField] private string enemyName = "Imperial Interceptor";

        public override EventOutcome Resolve(IShipManager ship)
        {
            float accuracyBonus = ship.GetCrewBonus(PerkType.Accuracy);
            float roll = Random.Range(0f, 100f) + accuracyBonus;
            bool success = roll >= baseHitThreshold;

            string log = success
                ? $"{enemyName} repelled. Gunner accuracy +{accuracyBonus:0.#} secured the engagement."
                : $"{enemyName} broke through the screen. Hull strained under fire.";

            return new EventOutcome(success, log, accuracyBonus);
        }
    }
}
