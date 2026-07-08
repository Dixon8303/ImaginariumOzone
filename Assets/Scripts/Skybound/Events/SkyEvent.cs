using UnityEngine;
using Skybound.Core;

namespace Skybound.Events
{
    /// <summary>
    /// Data-driven definition of a triggerable sky event. Pure data plus a validation gate;
    /// it owns no scene logic. The GameDirector reads these from its pool, the UIManager
    /// presents them. New events are authored as assets — no code changes required.
    /// </summary>
    [CreateAssetMenu(fileName = "NewSkyEvent", menuName = "Skybound/Sky Event")]
    public class SkyEvent : ScriptableObject
    {
        [Header("Identity")]
        [SerializeField] private string eventId = "evt_unnamed";
        [SerializeField] private SkyEventType eventType;

        [Header("Selection Weighting")]
        [SerializeField, Range(0f, 100f)] private float baseProbability = 10f;
        [Tooltip("Layers this event is eligible in. Empty = all layers.")]
        [SerializeField] private SkyLayer[] eligibleLayers;
        [Tooltip("Minimum ship level before this event can roll.")]
        [SerializeField] private int minShipLevel = 0;

        [Header("Payload")]
        [SerializeField] private EncounterData encounter;

        public string EventId => eventId;
        public SkyEventType Type => eventType;
        public float BaseProbability => baseProbability;
        public EncounterData Encounter => encounter;

        /// <summary>
        /// Validation gate. Returns true if this event is legal against the current ship state.
        /// Pure and side-effect free — safe to call on every selection pass.
        /// </summary>
        public bool CanTrigger(ShipState state)
        {
            if (state.ShipLevel < minShipLevel) return false;
            if (eventType == SkyEventType.Combat && state.HullIntegrity01 <= 0f) return false;
            if (!IsLayerEligible(state.Layer)) return false;
            return true;
        }

        private bool IsLayerEligible(SkyLayer layer)
        {
            if (eligibleLayers == null || eligibleLayers.Length == 0) return true;
            for (int i = 0; i < eligibleLayers.Length; i++)
                if (eligibleLayers[i] == layer) return true;
            return false;
        }
    }
}
