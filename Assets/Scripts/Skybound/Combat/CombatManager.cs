using UnityEngine;
using Skybound.Ship;
using Skybound.Core;

namespace Skybound.Combat
{
    /// <summary>
    /// MonoBehaviour wrapper for CombatEngine. Instantiates a new engine per
    /// encounter and exposes Unity-friendly events for the UI and feed systems.
    /// </summary>
    public class CombatManager : MonoBehaviour
    {
        [SerializeField] private ShipManager ship;
        [SerializeField] private ShipCrewManager crew;

        private CombatEngine _engine;

        public bool InCombat => _engine != null && _engine.State.Phase == CombatPhase.PlayerTurn
                                                || (_engine != null && _engine.State.Phase == CombatPhase.EnemyTurn);

        public CombatState CurrentState => _engine?.State;

        public System.Action<string>      OnCombatLog;
        public System.Action<CombatState> OnTurnResolved;
        public System.Action<CombatPhase> OnCombatEnded;

        public void StartCombat()
        {
            if (ship == null || crew == null)
            {
                Debug.LogWarning("[CombatManager] ShipManager or ShipCrewManager not assigned.");
                return;
            }
            _engine = new CombatEngine(ship, crew);
            _engine.OnCombatLog      += msg   => OnCombatLog?.Invoke(msg);
            _engine.OnTurnResolved   += state => OnTurnResolved?.Invoke(state);
            _engine.OnCombatEnded    += phase =>
            {
                ship.SetCombat(false);
                OnCombatEnded?.Invoke(phase);
                _engine = null;
            };
            ship.SetCombat(true);
            _engine.BeginCombat();
        }

        public void SubmitAction(TacticalAction action)
        {
            _engine?.SubmitPlayerAction(action);
        }

        public void SetReferences(ShipManager s, ShipCrewManager c)
        {
            ship = s;
            crew = c;
        }
    }
}
