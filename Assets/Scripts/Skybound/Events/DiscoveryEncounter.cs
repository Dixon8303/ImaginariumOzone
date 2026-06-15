using UnityEngine;
using Skybound.Core;

namespace Skybound.Events
{
    [CreateAssetMenu(fileName = "NewDiscoveryEncounter", menuName = "Skybound/Encounters/Discovery")]
    public class DiscoveryEncounter : EncounterData
    {
        [Header("Reward")]
        [SerializeField] private int minLootGold = 10;
        [SerializeField] private int maxLootGold = 50;
        [SerializeField] private string artifactName = "Ancient Compass";
        [SerializeField] private bool grantsArtifact = false;

        [Header("Difficulty")]
        [Tooltip("Cooldown perk reduces the time cost of investigation; threshold to earn bonus loot.")]
        [SerializeField, Range(0f, 30f)] private float cooldownBonusThreshold = 15f;

        public override EventOutcome Resolve(IShipManager ship)
        {
            float cooldownBonus = ship.GetCrewBonus(PerkType.Cooldown);
            int gold = Random.Range(minLootGold, maxLootGold + 1);
            bool bonusLoot = cooldownBonus >= cooldownBonusThreshold;

            string log;
            if (grantsArtifact)
            {
                log = $"Discovery: {artifactName} recovered. +{gold} gold." +
                      (bonusLoot ? " Swift investigation netted bonus salvage." : "");
            }
            else
            {
                log = $"Derelict swept. +{gold} gold." +
                      (bonusLoot ? $" Crew efficiency (CD+{cooldownBonus:0.#}) recovered extra supplies." : "");
            }

            return new EventOutcome(true, log, cooldownBonus);
        }
    }
}
