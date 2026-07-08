using System;
using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.Crew
{
    public enum PersonalityTrait
    {
        Historian,      // bonus to Decoded discoveries; triggered by Ancestor Fields
        Gunfighter,     // accuracy bonus in consecutive combats
        Wanderer,       // bonus in Uncharted biomes; penalty in Trade routes (restless)
        Engineer,       // repair bonus; triggered by hull damage events
        Mystic,         // bonuses in VoidSky; unsettled in ImperialCorridor
        Diplomat,       // unlocks NPC negotiation options; reduces combat events
        Rebel           // bonus when fighting Imperial enemies; high rivalry potential
    }

    public enum EmotionalState
    {
        Steady,     // baseline
        Inspired,   // bonus +10% to all perks (triggered by major discoveries)
        Strained,   // penalty -10% (hull below 30%, prolonged combat)
        Bonded,     // +15% when paired with trusted crewmate
        Rivalrous   // -5% but +20% to direct action against rival's trigger type
    }

    [Serializable]
    public class CrewRelationship
    {
        public string CrewMemberName;
        public float TrustLevel;   // -1 (deep rivalry) to +1 (deep bond)
        public bool IsRival => TrustLevel < -0.4f;
        public bool IsBonded => TrustLevel > 0.6f;
    }

    /// <summary>
    /// Runtime personality and emotional state for a crew member.
    /// Wraps the CrewMember ScriptableObject with dynamic state that evolves
    /// through play — trust, rivalries, emotional arc, narrative triggers.
    ///
    /// Rubric:
    ///   Memorability 5 — "Femi and Chidi rivalry broke open at VoidSky"
    ///   Story 5        — personalities reflect cultural archetypes, not generic classes
    ///   Fun 5          — managing crew relationships is a parallel strategy layer
    ///   Replay 5       — randomised starting relationships change crew dynamics each run
    /// </summary>
    public class CrewPersonality
    {
        public string Name;
        public PersonalityTrait Trait;
        public EmotionalState Emotion = EmotionalState.Steady;

        private readonly Dictionary<string, CrewRelationship> _relationships
            = new Dictionary<string, CrewRelationship>();

        private int _consecutiveCombats = 0;
        private int _discoveriesMade = 0;

        public IReadOnlyDictionary<string, CrewRelationship> Relationships => _relationships;

        public event Action<string, EmotionalState> OnEmotionChanged;  // (name, newState)
        public event Action<string, string, float>  OnTrustShifted;   // (a, b, delta)
        public event Action<string>                 OnNarrativeTrigger; // (description)

        public CrewPersonality(string name, PersonalityTrait trait)
        {
            Name  = name;
            Trait = trait;
        }

        /// <summary>
        /// Bonus multiplier applied on top of base perk values.
        /// Emotional state and personality both contribute.
        /// </summary>
        public float GetPerkMultiplier(PerkType perk, Skybound.World.SkyBiome currentBiome)
        {
            float mult = EmotionMultiplier();
            mult += TraitBiomeBonus(currentBiome);
            return Mathf.Max(0.1f, mult);
        }

        /// <summary>Notify this crew member that combat occurred.</summary>
        public void OnCombatOccurred(bool wasVictory)
        {
            _consecutiveCombats++;
            if (Trait == PersonalityTrait.Gunfighter && _consecutiveCombats >= 2)
            {
                SetEmotion(EmotionalState.Inspired);
                OnNarrativeTrigger?.Invoke($"{Name} is in the zone — consecutive engagements sharpen their edge.");
            }
            if (!wasVictory)
            {
                _consecutiveCombats = 0;
                if (Emotion == EmotionalState.Inspired) SetEmotion(EmotionalState.Steady);
            }
        }

        /// <summary>Notify this crew member of a discovery event.</summary>
        public void OnDiscoveryMade(Skybound.World.SkyBiome biome)
        {
            _discoveriesMade++;
            _consecutiveCombats = 0;

            if (Trait == PersonalityTrait.Historian && biome == Skybound.World.SkyBiome.AncestorFields)
            {
                SetEmotion(EmotionalState.Inspired);
                OnNarrativeTrigger?.Invoke(
                    $"{Name} grows quiet at the controls. \"I've read about this place,\" they say. " +
                    "\"It shouldn't be here.\"");
            }

            if (_discoveriesMade == 5 && Trait == PersonalityTrait.Wanderer)
                OnNarrativeTrigger?.Invoke(
                    $"{Name} marks the fifth uncharted cell. They haven't slept. They don't seem to want to.");
        }

        /// <summary>Shift trust between this crew member and another.</summary>
        public void ShiftTrust(string otherName, float delta)
        {
            if (!_relationships.ContainsKey(otherName))
                _relationships[otherName] = new CrewRelationship { CrewMemberName = otherName };

            var rel = _relationships[otherName];
            float prev = rel.TrustLevel;
            rel.TrustLevel = Mathf.Clamp(rel.TrustLevel + delta, -1f, 1f);

            OnTrustShifted?.Invoke(Name, otherName, delta);

            if (prev < 0.6f && rel.IsBonded)
            {
                SetEmotion(EmotionalState.Bonded);
                OnNarrativeTrigger?.Invoke(
                    $"{Name} and {otherName} have found their rhythm. The ship runs better for it.");
            }
            else if (prev > -0.4f && rel.IsRival)
            {
                SetEmotion(EmotionalState.Rivalrous);
                OnNarrativeTrigger?.Invoke(
                    $"Tension between {Name} and {otherName} has reached a breaking point. " +
                    "The crew feels it.");
            }
        }

        public void OnHullCritical()
        {
            if (Trait == PersonalityTrait.Engineer)
            {
                SetEmotion(EmotionalState.Inspired);
                OnNarrativeTrigger?.Invoke(
                    $"{Name} is already in the hull plating — tools out before the order came.");
            }
            else
                SetEmotion(EmotionalState.Strained);
        }

        private void SetEmotion(EmotionalState next)
        {
            if (Emotion == next) return;
            Emotion = next;
            OnEmotionChanged?.Invoke(Name, next);
        }

        private float EmotionMultiplier() => Emotion switch
        {
            EmotionalState.Inspired   =>  1.10f,
            EmotionalState.Strained   =>  0.90f,
            EmotionalState.Bonded     =>  1.15f,
            EmotionalState.Rivalrous  =>  1.00f, // rivalrous: neutral base, spikes per action
            _                         =>  1.00f
        };

        private float TraitBiomeBonus(Skybound.World.SkyBiome biome)
        {
            return (Trait, biome) switch
            {
                (PersonalityTrait.Historian,  Skybound.World.SkyBiome.AncestorFields)   =>  0.20f,
                (PersonalityTrait.Historian,  Skybound.World.SkyBiome.CelestialRuin)    =>  0.15f,
                (PersonalityTrait.Wanderer,   Skybound.World.SkyBiome.Uncharted)        =>  0.20f,
                (PersonalityTrait.Wanderer,   Skybound.World.SkyBiome.TradeWinds)       => -0.10f,
                (PersonalityTrait.Mystic,     Skybound.World.SkyBiome.VoidAnomaly)      =>  0.25f,
                (PersonalityTrait.Mystic,     Skybound.World.SkyBiome.ImperialCorridor) => -0.15f,
                (PersonalityTrait.Rebel,      Skybound.World.SkyBiome.ImperialCorridor) =>  0.20f,
                (PersonalityTrait.Diplomat,   Skybound.World.SkyBiome.TradeWinds)       =>  0.15f,
                _                                                                         =>  0.00f
            };
        }
    }
}
