using System.Collections.Generic;
using UnityEngine;
using Skybound.Events;

namespace Skybound.Core
{
    [CreateAssetMenu(fileName = "NewSkyEvent", menuName = "Skybound/Sky Event")]
    public class SkyEvent : ScriptableObject
    {
        [SerializeField] private string eventId;
        [SerializeField] private EventType eventType;
        [SerializeField, Range(0f, 100f)] private float baseProbability = 20f;
        [SerializeField] private List<SkyLayer> eligibleLayers = new List<SkyLayer>();
        [SerializeField] private int minShipLevel = 1;
        [SerializeField] private EncounterData encounter;

        public string EventId => eventId;
        public EventType EventType => eventType;
        public float BaseProbability => baseProbability;
        public EncounterData Encounter => encounter;

        public bool CanTrigger(ShipState state)
        {
            if (state.ShipLevel < minShipLevel) return false;
            if (eligibleLayers.Count == 0) return true;
            return eligibleLayers.Contains(state.Layer);
        }
    }
}
