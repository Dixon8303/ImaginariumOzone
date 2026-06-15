using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.Systems
{
    /// <summary>
    /// DEV-ONLY placeholder implementing IShipManager so the event + UI slice runs without the
    /// production crew system. Replace with the real ShipManager / ShipCrewManager when ready.
    /// Crew bonuses are summed per PerkType here, mirroring the dual-slot stacking model so the
    /// rest of the pipeline is exercised against realistic behaviour.
    /// </summary>
    public class DebugShipManager : MonoBehaviour, IShipManager
    {
        [Header("Mock Ship State")]
        [SerializeField] private SkyLayer layer = SkyLayer.LowSky;
        [SerializeField, Range(0f, 1f)] private float hullIntegrity01 = 1f;
        [SerializeField] private int crewCount = 3;
        [SerializeField] private int shipLevel = 1;

        [Header("Mock Crew Bonuses")]
        [SerializeField] private List<PerkEntry> crewPerks = new List<PerkEntry>();

        [System.Serializable]
        private struct PerkEntry
        {
            public PerkType perk;
            public float value;
        }

        public SkyLayer CurrentLayer => layer;

        public ShipState GetState()
            => new ShipState(layer, hullIntegrity01, crewCount, shipLevel, inCombat: false);

        public float GetCrewBonus(PerkType perk)
        {
            float sum = 0f;
            foreach (var entry in crewPerks)
                if (entry.perk == perk) sum += entry.value;
            return sum;
        }
    }
}
