using Skybound.Core;

namespace Skybound.Combat
{
    public enum CombatPhase { PlayerTurn, EnemyTurn, Victory, Defeat, Fled }

    public enum WindDirection { North, South, East, West, Calm }

    public enum TacticalAction
    {
        FireCannons,    // accuracy-based attack
        Evade,          // spend momentum to dodge next hit
        Ascend,         // gain altitude advantage (+damage next turn)
        Descend,        // lose altitude, gain speed (cheaper evade next turn)
        CrewSynergy,    // activate a crew combo chain (special)
        FleeAttempt     // attempt escape — costs hull integrity
    }

    public class CombatState
    {
        public float PlayerHull;       // normalized 0..1
        public float EnemyHull;
        public int   PlayerAltitude;   // 0=low, 1=mid, 2=high — higher = damage bonus
        public int   EnemyAltitude;
        public WindDirection Wind;
        public CombatPhase Phase;
        public int TurnNumber;
        public int MaxTurns;           // defeat if not resolved by then

        public bool AltitudeAdvantage  => PlayerAltitude > EnemyAltitude;
        public bool AltitudePenalty    => PlayerAltitude < EnemyAltitude;
        public bool WindFavorsPlayer;  // set by CombatEngine each turn

        public CombatState(float playerHull, int maxTurns = 8)
        {
            PlayerHull    = playerHull;
            EnemyHull     = 1f;
            PlayerAltitude = 1;
            EnemyAltitude  = 1;
            Phase          = CombatPhase.PlayerTurn;
            TurnNumber     = 0;
            MaxTurns       = maxTurns;
            Wind           = WindDirection.Calm;
            WindFavorsPlayer = false;
        }
    }
}
