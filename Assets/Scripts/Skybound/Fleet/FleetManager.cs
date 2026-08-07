using System.Collections.Generic;
using UnityEngine;

namespace Skybound.Fleet
{
    /// <summary>
    /// MonoBehaviour wrapper for FleetCombatEngine. Exposes fleet state to the
    /// UI and wires the feed log. Add ships via the Inspector roster; call
    /// StartFleetBattle from CommandBarController or GameBootstrap when a
    /// fleet encounter triggers.
    /// </summary>
    public class FleetManager : MonoBehaviour
    {
        [Header("Player Fleet (configure in Inspector)")]
        [SerializeField] private List<FleetShipConfig> shipConfigs;
        [SerializeField] private FormationType startFormation = FormationType.Diamond;

        [Header("Dependencies")]
        [SerializeField] private Skybound.Systems.UIManager uiManager;

        private FleetCombatEngine _engine;
        public bool InBattle => _engine != null && (_engine.Phase == FleetCombatPhase.PlayerTurn
                                                 || _engine.Phase == FleetCombatPhase.EnemyTurn
                                                 || _engine.Phase == FleetCombatPhase.Resolving);

        [System.Serializable]
        public class FleetShipConfig
        {
            public string name      = "Sky Vessel";
            public float  hull      = 1f;
            public float  firepower = 0.25f;
        }

        public void StartFleetBattle(List<FleetShip> enemies)
        {
            _engine = new FleetCombatEngine();
            _engine.OnLog          += msg => uiManager?.AppendFeed(msg);
            _engine.OnVictory      += () => uiManager?.AppendFeed("[Fleet] Victory! Route secured.");
            _engine.OnDefeat       += () => uiManager?.AppendFeed("[Fleet] Fleet broken. Retreating.");

            var fleet = new List<FleetShip>();
            if (shipConfigs != null)
                foreach (var cfg in shipConfigs)
                    fleet.Add(new FleetShip { name = cfg.name, hull = cfg.hull, firepower = cfg.firepower });

            if (fleet.Count == 0)
                fleet.Add(new FleetShip { name = "Flagship", hull = 1f, firepower = 0.30f });

            _engine.StartBattle(fleet, enemies, new FleetFormation { type = startFormation });
        }

        public void PlayerAttack()  { _engine?.PlayerAttack();  AfterPlayerAction(); }
        public void PlayerRetreat() { _engine?.PlayerRetreat(); }

        private void AfterPlayerAction()
        {
            if (_engine?.Phase == FleetCombatPhase.EnemyTurn)
                _engine.EnemyTurn();
        }
    }
}
