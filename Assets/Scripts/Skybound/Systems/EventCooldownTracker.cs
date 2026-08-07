using System.Collections.Generic;
using UnityEngine;

namespace Skybound.Systems
{
    /// <summary>
    /// Prevents the same encounter from firing back-to-back.
    /// GameDirector calls RecordEvent() after each trigger and IsCoolingDown()
    /// before allowing a re-trigger. Cooldowns are step-based (cells moved),
    /// not time-based, so they feel proportional to player activity.
    /// </summary>
    public class EventCooldownTracker : MonoBehaviour
    {
        [Tooltip("Cells that must be crossed before an event type can fire again.")]
        [SerializeField] private int defaultCooldownSteps = 3;

        private readonly Dictionary<string, int> _lastFiredStep = new Dictionary<string, int>();
        private int _stepCount;

        public void OnCellMoved() => _stepCount++;

        public void RecordEvent(string eventId)
        {
            _lastFiredStep[eventId] = _stepCount;
        }

        public bool IsCoolingDown(string eventId)
        {
            if (!_lastFiredStep.TryGetValue(eventId, out int lastStep)) return false;
            return (_stepCount - lastStep) < defaultCooldownSteps;
        }

        /// <summary>Returns true if eventId can fire right now.</summary>
        public bool CanFire(string eventId) => !IsCoolingDown(eventId);

        public void Reset()
        {
            _lastFiredStep.Clear();
            _stepCount = 0;
        }
    }
}
