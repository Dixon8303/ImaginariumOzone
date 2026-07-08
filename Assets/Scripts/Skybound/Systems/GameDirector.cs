using System;
using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;
using Skybound.Events;

namespace Skybound.Systems
{
    /// <summary>
    /// Selects and sequences sky events from a data-driven pool.
    /// Owns selection + resolution logic only. Presentation is delegated through C# events,
    /// so the director has zero compile-time dependency on the UI layer — the UIManager
    /// (or any other listener) subscribes without the director knowing it exists.
    /// </summary>
    public class GameDirector : MonoBehaviour
    {
        [Header("Event Pool")]
        [SerializeField] private List<SkyEvent> eventPool = new List<SkyEvent>();

        [Header("Pacing")]
        [Tooltip("Master chance (0-100) that ANY event fires on a given CheckForEvent pass.")]
        [SerializeField, Range(0f, 100f)] private float eventChancePerCheck = 35f;

        [Header("Biome Weighting")]
        [Tooltip("Per-layer multiplier applied to every event's base probability.")]
        [SerializeField] private LayerWeight[] layerWeights;

        private readonly Dictionary<SkyLayer, float> _layerWeightLookup = new Dictionary<SkyLayer, float>();
        private readonly List<EventWeight> _weightBuffer = new List<EventWeight>(); // reused: no per-pass GC
        private IShipManager _ship;
        private SkyEvent _activeEvent;

        /// <summary>Raised when an event is selected and should be presented. UI transitions to Encounter mode.</summary>
        public event Action<SkyEvent> OnEncounterStarted;

        /// <summary>Raised when the active encounter resolves. UI logs the outcome and may return to Exploration.</summary>
        public event Action<SkyEvent, EventOutcome> OnEncounterResolved;

        public SkyEvent ActiveEvent => _activeEvent;
        public bool HasActiveEncounter => _activeEvent != null;

        [Serializable]
        private struct LayerWeight
        {
            public SkyLayer layer;
            [Range(0f, 3f)] public float multiplier;
        }

        private struct EventWeight
        {
            public SkyEvent Event;
            public float Weight;
            public EventWeight(SkyEvent e, float w) { Event = e; Weight = w; }
        }

        /// <summary>Inject the ship data source. Call once during scene bootstrap.</summary>
        public void Initialize(IShipManager ship)
        {
            _ship = ship;
            _layerWeightLookup.Clear();
            if (layerWeights != null)
                foreach (var lw in layerWeights)
                    _layerWeightLookup[lw.layer] = lw.multiplier;
        }

        /// <summary>
        /// Run one selection pass. First rolls the master pacing gate; if it passes, filters the
        /// pool by CanTrigger and selects one event weighted by base probability x layer multiplier.
        /// Returns true if an encounter started.
        /// </summary>
        public bool CheckForEvent()
        {
            if (_ship == null)
            {
                Debug.LogWarning("[GameDirector] No IShipManager injected. Call Initialize() first.");
                return false;
            }
            if (_activeEvent != null) return false;                          // one encounter at a time
            if (UnityEngine.Random.Range(0f, 100f) > eventChancePerCheck)
                return false;                                                // quiet pass — exploration continues

            SkyEvent selected = SelectWeighted(_ship.GetState());
            if (selected == null) return false;

            _activeEvent = selected;
            OnEncounterStarted?.Invoke(selected);
            return true;
        }

        /// <summary>Resolve the active encounter against current crew bonuses and broadcast the outcome.</summary>
        public void ResolveActiveEncounter()
        {
            if (_activeEvent == null) return;

            EventOutcome outcome = _activeEvent.Encounter != null
                ? _activeEvent.Encounter.Resolve(_ship)
                : new EventOutcome(true, $"{_activeEvent.EventId} resolved.");

            SkyEvent resolved = _activeEvent;
            _activeEvent = null;                       // clear before broadcast so listeners can re-check safely
            OnEncounterResolved?.Invoke(resolved, outcome);
        }

        /// <summary>Roulette-wheel selection over eligible, layer-weighted events.</summary>
        private SkyEvent SelectWeighted(ShipState state)
        {
            _weightBuffer.Clear();
            float total = 0f;
            float layerMult = LayerMultiplier(state.Layer);

            foreach (var evt in eventPool)
            {
                if (evt == null || !evt.CanTrigger(state)) continue;
                float weight = evt.BaseProbability * layerMult;
                if (weight <= 0f) continue;
                _weightBuffer.Add(new EventWeight(evt, weight));
                total += weight;
            }

            if (_weightBuffer.Count == 0) return null;

            float roll = UnityEngine.Random.Range(0f, total);
            float cursor = 0f;
            for (int i = 0; i < _weightBuffer.Count; i++)
            {
                cursor += _weightBuffer[i].Weight;
                if (roll <= cursor) return _weightBuffer[i].Event;
            }
            return _weightBuffer[_weightBuffer.Count - 1].Event;   // float-edge fallback
        }

        private float LayerMultiplier(SkyLayer layer)
            => _layerWeightLookup.TryGetValue(layer, out float m) ? m : 1f;
    }
}
