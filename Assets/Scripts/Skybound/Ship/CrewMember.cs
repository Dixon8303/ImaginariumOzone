using UnityEngine;
using Skybound.Core;

namespace Skybound.Ship
{
    [CreateAssetMenu(fileName = "NewCrewMember", menuName = "Skybound/Crew Member")]
    public class CrewMember : ScriptableObject
    {
        [SerializeField] private string crewName = "Unknown";
        [SerializeField] private Sprite portrait;
        [SerializeField] private int level = 1;

        [Header("Perk Slots (dual-slot model)")]
        [SerializeField] private PerkType primaryPerk = PerkType.Accuracy;
        [SerializeField, Range(0f, 50f)] private float primaryBonus = 10f;
        [SerializeField] private bool hasSecondaryPerk = false;
        [SerializeField] private PerkType secondaryPerk = PerkType.Damage;
        [SerializeField, Range(0f, 50f)] private float secondaryBonus = 5f;

        public string CrewName => crewName;
        public Sprite Portrait => portrait;
        public int Level => level;

        public float GetBonus(PerkType perk)
        {
            float total = 0f;
            if (primaryPerk == perk) total += primaryBonus;
            if (hasSecondaryPerk && secondaryPerk == perk) total += secondaryBonus;
            return total;
        }
    }
}
