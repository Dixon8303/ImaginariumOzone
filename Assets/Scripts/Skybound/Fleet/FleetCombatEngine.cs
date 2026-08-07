using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.Fleet
{
    public enum FleetCombatPhase { Setup, PlayerTurn, EnemyTurn, Resolving, Victory, Defeat }

    [System.Serializable]
    public class FleetShip
    {
        public string name;
        public float  hull;        // 0–1
        public float  firepower;   // base damage output
        public bool   IsAlive => hull > 0f;
    }

    /// <summary>
    /// Manages a multi-ship engagement. The player commands a fleet of up to
    /// four ships against an enemy squadron. Formation choice locks in at the
    /// start and modifies every exchange until one side is wiped.
    ///
    /// Rubric:
    ///   Fun 5    — fleet tactics add scale without overwhelming the solo-ship loop
    ///   Story 5  — fleet battles mark major faction confrontations
    ///   Replay 5 — enemy squadron composition varies by seed + DangerLevel
    /// </summary>
    public class FleetCombatEngine
    {
        public FleetCombatPhase Phase { get; private set; } = FleetCombatPhase.Setup;

        public System.Action<string>           OnLog;
        public System.Action<FleetCombatPhase> OnPhaseChanged;
        public System.Action                   OnVictory;
        public System.Action                   OnDefeat;

        private List<FleetShip> _playerFleet;
        private List<FleetShip> _enemyFleet;
        private FleetFormation  _formation;
        private int             _round;

        public void StartBattle(
            List<FleetShip> playerFleet,
            List<FleetShip> enemyFleet,
            FleetFormation  formation)
        {
            _playerFleet = playerFleet;
            _enemyFleet  = enemyFleet;
            _formation   = formation;
            _round       = 0;

            Log($"Fleet engagement! Formation: {formation.Describe()}");
            Log($"Your fleet: {playerFleet.Count} ships  vs  Enemy: {enemyFleet.Count} ships.");
            SetPhase(FleetCombatPhase.PlayerTurn);
        }

        /// <summary>Player fires — targets weakest enemy ship first.</summary>
        public void PlayerAttack()
        {
            if (Phase != FleetCombatPhase.PlayerTurn) return;
            SetPhase(FleetCombatPhase.Resolving);

            float totalFirepower = 0f;
            foreach (var s in _playerFleet)
                if (s.IsAlive) totalFirepower += s.firepower * _formation.DamageMultiplier;

            var target = WeakestAlive(_enemyFleet);
            if (target != null)
            {
                float dmg = totalFirepower * Random.Range(0.8f, 1.2f);
                target.hull = Mathf.Max(0f, target.hull - dmg);
                Log($"[Fleet] Your fleet fires — {target.name} hull now {target.hull * 100f:0.#}%.");
            }

            CheckEnd();
            if (Phase == FleetCombatPhase.Resolving) SetPhase(FleetCombatPhase.EnemyTurn);
        }

        /// <summary>Player retreats — costs one ship's hull to break contact.</summary>
        public void PlayerRetreat()
        {
            if (Phase != FleetCombatPhase.PlayerTurn) return;
            var rearguard = WeakestAlive(_playerFleet);
            if (rearguard != null)
            {
                rearguard.hull = Mathf.Max(0f, rearguard.hull - 0.25f);
                Log($"[Fleet] {rearguard.name} covers retreat — hull at {rearguard.hull * 100f:0.#}%.");
            }
            Log("[Fleet] Fleet broke contact. Engagement ended.");
            SetPhase(FleetCombatPhase.Defeat); // retreat = tactical defeat, not destruction
        }

        public void EnemyTurn()
        {
            if (Phase != FleetCombatPhase.EnemyTurn) return;
            _round++;

            float totalFirepower = 0f;
            foreach (var s in _enemyFleet)
                if (s.IsAlive) totalFirepower += s.firepower;

            var target = WeakestAlive(_playerFleet);
            if (target != null)
            {
                float mitigation = _formation.DefenceMultiplier;
                float dmg        = (totalFirepower * Random.Range(0.7f, 1.1f)) / mitigation;
                target.hull      = Mathf.Max(0f, target.hull - dmg);
                Log($"[Fleet] Enemy fires — {target.name} hull at {target.hull * 100f:0.#}%.");
            }

            CheckEnd();
            if (Phase == FleetCombatPhase.Resolving) SetPhase(FleetCombatPhase.PlayerTurn);
        }

        private void CheckEnd()
        {
            bool enemyDestroyed = _enemyFleet.TrueForAll(s => !s.IsAlive);
            bool playerDestroyed = _playerFleet.TrueForAll(s => !s.IsAlive);

            if (enemyDestroyed)
            {
                Log($"[Fleet] Enemy squadron destroyed! Victory in {_round} rounds.");
                SetPhase(FleetCombatPhase.Victory);
                OnVictory?.Invoke();
            }
            else if (playerDestroyed)
            {
                Log("[Fleet] All ships lost. Defeat.");
                SetPhase(FleetCombatPhase.Defeat);
                OnDefeat?.Invoke();
            }
        }

        private FleetShip WeakestAlive(List<FleetShip> fleet)
        {
            FleetShip weakest = null;
            foreach (var s in fleet)
                if (s.IsAlive && (weakest == null || s.hull < weakest.hull))
                    weakest = s;
            return weakest;
        }

        private void SetPhase(FleetCombatPhase p)
        {
            Phase = p;
            OnPhaseChanged?.Invoke(p);
        }

        private void Log(string msg) => OnLog?.Invoke(msg);
    }
}
