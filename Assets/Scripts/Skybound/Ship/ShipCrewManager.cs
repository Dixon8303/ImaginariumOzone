using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.Ship
{
    /// <summary>
    /// Manages the active crew roster. Crew bonuses stack across all filled slots per PerkType,
    /// matching the dual-slot accumulation model described in IShipManager.
    /// </summary>
    public class ShipCrewManager : MonoBehaviour
    {
        [SerializeField, Tooltip("Max crew slots the ship supports at current tier.")]
        private int maxSlots = 4;

        private readonly List<CrewMember> _roster = new List<CrewMember>();

        public IReadOnlyList<CrewMember> Roster => _roster;
        public int MaxSlots => maxSlots;
        public int FilledSlots => _roster.Count;

        public bool TryAddCrew(CrewMember member)
        {
            if (member == null || _roster.Count >= maxSlots) return false;
            if (_roster.Contains(member)) return false;
            _roster.Add(member);
            return true;
        }

        public bool RemoveCrew(CrewMember member)
        {
            return _roster.Remove(member);
        }

        public float GetTotalBonus(PerkType perk)
        {
            float total = 0f;
            foreach (var member in _roster)
                total += member.GetBonus(perk);
            return total;
        }

        public int GetCrewCount() => _roster.Count;
    }
}
