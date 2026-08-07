using System.Collections.Generic;
using UnityEngine;

namespace Skybound.NPC
{
    /// <summary>
    /// Tracks the player's standing with each faction across the run.
    /// Standing is clamped to FactionStanding enum range [-2, +2].
    /// Raises OnStandingChanged whenever a faction relationship shifts.
    /// </summary>
    public class FactionStandingManager : MonoBehaviour
    {
        public System.Action<FactionId, FactionStanding> OnStandingChanged;

        private readonly Dictionary<FactionId, int> _standings = new Dictionary<FactionId, int>();

        private void Awake()
        {
            foreach (FactionId id in System.Enum.GetValues(typeof(FactionId)))
                _standings[id] = (int)FactionStanding.Neutral;
        }

        public FactionStanding GetStanding(FactionId faction)
        {
            int raw = _standings.TryGetValue(faction, out int v) ? v : 0;
            return (FactionStanding)Mathf.Clamp(raw, -2, 2);
        }

        public void ShiftStanding(FactionId faction, int delta)
        {
            if (!_standings.ContainsKey(faction)) _standings[faction] = 0;
            _standings[faction] = Mathf.Clamp(_standings[faction] + delta, -2, 2);
            OnStandingChanged?.Invoke(faction, GetStanding(faction));
        }

        public void SetStanding(FactionId faction, FactionStanding standing)
        {
            _standings[faction] = (int)standing;
            OnStandingChanged?.Invoke(faction, standing);
        }

        /// <summary>Returns true if any home biome of faction is politically accessible.</summary>
        public bool FactionWillDock(FactionId faction)
            => GetStanding(faction) >= FactionStanding.Neutral;
    }
}
