using UnityEngine;
using Skybound.Core;

namespace Skybound.Events
{
    [CreateAssetMenu(fileName = "NewEnvironmentalEncounter", menuName = "Skybound/Encounters/Environmental")]
    public class EnvironmentalEncounter : EncounterData
    {
        [Header("Hazard")]
        [SerializeField] private string hazardName = "Aether Storm";
        [SerializeField, Range(0f, 0.5f)] private float hullDamage01 = 0.15f;

        [Header("Evasion")]
        [Tooltip("Damage perk represents structural reinforcement; reduces incoming hull damage.")]
        [SerializeField, Range(0f, 50f)] private float damageReductionPerPoint = 0.005f;
        [SerializeField, Range(0f, 100f)] private float evadeThreshold = 40f;

        public override EventOutcome Resolve(IShipManager ship)
        {
            float damageBonus = ship.GetCrewBonus(PerkType.Damage);
            float roll = Random.Range(0f, 100f) + damageBonus;
            bool evaded = roll >= evadeThreshold;

            string log;
            if (evaded)
            {
                log = $"{hazardName} navigated. Hull reinforcement (DMG+{damageBonus:0.#}) absorbed the worst.";
            }
            else
            {
                float actualDamage = Mathf.Max(0f, hullDamage01 - damageBonus * damageReductionPerPoint);
                log = $"{hazardName} struck hard. Hull integrity reduced by {actualDamage * 100f:0.#}%.";
            }

            return new EventOutcome(evaded, log, damageBonus);
        }
    }
}
