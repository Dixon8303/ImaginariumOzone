using UnityEngine;

namespace Skybound.Fleet
{
    public enum FormationType
    {
        Vanguard,       // one ship absorbs hits, others fire freely
        Diamond,        // balanced — damage and defence even
        ScatterRun,     // speed boost, accuracy penalty
        HammerAnvil     // two-prong — one flanks while one holds
    }

    /// <summary>
    /// Describes the tactical arrangement of the player's fleet for a given
    /// engagement. Formation bonuses are applied by FleetCombatEngine each round.
    /// </summary>
    [System.Serializable]
    public class FleetFormation
    {
        public FormationType type;

        public float DamageMultiplier => type switch
        {
            FormationType.Vanguard    => 1.20f,
            FormationType.Diamond     => 1.00f,
            FormationType.ScatterRun  => 0.75f,
            FormationType.HammerAnvil => 1.35f,
            _                         => 1.00f
        };

        public float DefenceMultiplier => type switch
        {
            FormationType.Vanguard    => 1.40f,
            FormationType.Diamond     => 1.00f,
            FormationType.ScatterRun  => 0.60f,
            FormationType.HammerAnvil => 0.85f,
            _                         => 1.00f
        };

        public float SpeedMultiplier => type switch
        {
            FormationType.ScatterRun  => 1.50f,
            _                         => 1.00f
        };

        public string Describe() => type switch
        {
            FormationType.Vanguard    => "Vanguard: lead ship shields the fleet. +Def, +Dmg.",
            FormationType.Diamond     => "Diamond: balanced formation. Standard stats.",
            FormationType.ScatterRun  => "Scatter Run: fast retreat posture. -Def, -Acc, +Spd.",
            FormationType.HammerAnvil => "Hammer & Anvil: flanking split. High damage, lower defence.",
            _                         => "Unknown formation."
        };
    }
}
