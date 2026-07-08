using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;
using Skybound.World;

namespace Skybound.Crew
{
    /// <summary>
    /// Runtime manager for all crew personalities. Bridges the static CrewMember
    /// ScriptableObjects (stats) with dynamic CrewPersonality instances (story).
    /// Handles relationship initialisation, event routing, and perk bonus queries
    /// that include personality multipliers.
    /// </summary>
    public class CrewRosterManager : MonoBehaviour
    {
        private readonly List<CrewPersonality> _personalities = new List<CrewPersonality>();

        public IReadOnlyList<CrewPersonality> Personalities => _personalities;

        public System.Action<string> OnNarrativeEvent;

        /// <summary>
        /// Add a crew member at hire time. Randomises their personality trait
        /// and seeds starting relationships with existing crew.
        /// </summary>
        public CrewPersonality HireCrew(string name, int worldSeed)
        {
            Random.InitState(worldSeed ^ name.GetHashCode());
            var traits = (PersonalityTrait[])System.Enum.GetValues(typeof(PersonalityTrait));
            var trait  = traits[Random.Range(0, traits.Length)];

            var personality = new CrewPersonality(name, trait);
            personality.OnNarrativeTrigger += msg => OnNarrativeEvent?.Invoke(msg);

            // Seed starting relationships — some crews start with mild trust or suspicion
            foreach (var existing in _personalities)
            {
                float startingTrust = Random.Range(-0.3f, 0.4f);
                personality.ShiftTrust(existing.Name, startingTrust);
                existing.ShiftTrust(name, startingTrust * 0.8f);
            }

            _personalities.Add(personality);
            Debug.Log($"[CrewRoster] {name} joined as {trait}.");
            return personality;
        }

        public void BroadcastCombat(bool victory)
        {
            foreach (var p in _personalities) p.OnCombatOccurred(victory);

            // Combat stress shifts trust slightly negative between random pair
            if (!victory && _personalities.Count >= 2)
            {
                int a = Random.Range(0, _personalities.Count);
                int b = (a + 1) % _personalities.Count;
                _personalities[a].ShiftTrust(_personalities[b].Name, -0.05f);
                _personalities[b].ShiftTrust(_personalities[a].Name, -0.05f);
            }
        }

        public void BroadcastDiscovery(SkyBiome biome)
        {
            foreach (var p in _personalities) p.OnDiscoveryMade(biome);

            // Shared discovery builds trust between crew
            if (_personalities.Count >= 2)
            {
                int a = Random.Range(0, _personalities.Count);
                int b = (a + 1) % _personalities.Count;
                _personalities[a].ShiftTrust(_personalities[b].Name, +0.08f);
                _personalities[b].ShiftTrust(_personalities[a].Name, +0.08f);
            }
        }

        public void BroadcastHullCritical()
        {
            foreach (var p in _personalities) p.OnHullCritical();
        }

        /// <summary>
        /// Returns the combined perk bonus from all crew, with personality multipliers applied.
        /// This replaces the flat sum in ShipCrewManager for any system that needs the full value.
        /// </summary>
        public float GetPersonalityWeightedBonus(PerkType perk, SkyBiome currentBiome,
            Skybound.Ship.ShipCrewManager crewManager)
        {
            float total = 0f;
            foreach (var member in crewManager.Roster)
            {
                float baseBonus = member.GetBonus(perk);
                var personality = _personalities.Find(p => p.Name == member.CrewName);
                float mult = personality?.GetPerkMultiplier(perk, currentBiome) ?? 1f;
                total += baseBonus * mult;
            }
            return total;
        }
    }
}
