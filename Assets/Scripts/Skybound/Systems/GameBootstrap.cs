using UnityEngine;
using Skybound.Ship;
using Skybound.World;
using Skybound.Combat;
using Skybound.Discovery;
using Skybound.Crew;
using Skybound.UI;

namespace Skybound.Systems
{
    /// <summary>
    /// Wires all runtime event connections between systems at Start().
    /// SceneBuilder handles inspector references; this handles the event graph.
    ///
    /// Connection map:
    ///   SkyWorldManager.OnCellDiscovered  → DiscoveryAtlas + UIManager feed + CrewRoster
    ///   AirshipMovement.OnCellEntered     → GameDirector.CheckForEvent + ShipManager.SetLayer
    ///   AirshipMovement.OnMovementBlocked → UIManager feed
    ///   CombatManager.OnCombatLog         → UIManager feed
    ///   CombatManager.OnCombatEnded       → CrewRoster + ShipManager hull
    ///   CrewRosterManager.OnNarrativeEvent → UIManager feed
    ///   DiscoveryAtlas.OnEntryDiscovered  → UIManager feed
    ///   DiscoveryAtlas.OnEntryUpgraded    → UIManager feed
    /// </summary>
    public class GameBootstrap : MonoBehaviour
    {
        [Header("Systems")]
        [SerializeField] private ShipManager        ship;
        [SerializeField] private ShipCrewManager    crew;
        [SerializeField] private GameDirector       director;
        [SerializeField] private UIManager          uiManager;
        [SerializeField] private SkyWorldManager    worldManager;
        [SerializeField] private Skybound.Airship.AirshipMovement airship;
        [SerializeField] private CombatManager      combatManager;
        [SerializeField] private DiscoveryAtlas     atlas;
        [SerializeField] private CrewRosterManager  crewRoster;
        [SerializeField] private EventCooldownTracker cooldownTracker;
        [SerializeField] private SaveLoadPanel       saveLoadPanel;

        [Header("Starting Crew Names (hired at boot)")]
        [SerializeField] private string[] startingCrewNames = { "Femi", "Amara", "Chidi" };

        private void Start()
        {
            if (worldManager != null)
                worldManager.OnCellDiscovered += HandleCellDiscovered;

            if (airship != null)
            {
                airship.OnCellEntered     += HandleCellEntered;
                airship.OnMovementBlocked += msg => Feed($"[Nav] {msg}");
                airship.SetShipLevel(ship != null ? ship.ShipLevel : 1);
                airship.SetPosition(Vector2Int.zero);
                if (cooldownTracker != null)
                    airship.OnCellEntered += (_, __) => cooldownTracker.OnCellMoved();
            }

            if (combatManager != null)
            {
                combatManager.SetReferences(ship, crew);
                combatManager.OnCombatLog  += msg   => Feed($"[Combat] {msg}");
                combatManager.OnCombatEnded += phase => HandleCombatEnded(phase);
            }

            if (crewRoster != null)
            {
                crewRoster.OnNarrativeEvent += msg => Feed($"[Crew] {msg}");
                foreach (var name in startingCrewNames)
                    crewRoster.HireCrew(name, worldManager != null ? worldManager.Seed : 2026);
            }

            if (atlas != null)
            {
                atlas.OnEntryDiscovered += e =>
                    Feed(e.HasIsland
                        ? $"[Atlas] New island charted: {e.IslandName} ({e.Biome})"
                        : $"[Atlas] Sky cell logged: {e.Biome} at {e.GridPos}");

                atlas.OnEntryUpgraded += e =>
                {
                    if (e.Tier == Skybound.Discovery.DiscoveryTier.Decoded && !string.IsNullOrEmpty(e.LoreFragment))
                        Feed($"[Lore] {e.LoreFragment}");
                };
            }

            if (director != null && ship != null)
                director.Initialize(ship);

            Feed("Sky systems online. Navigation ready.");
            Feed($"World seed: {(worldManager != null ? worldManager.Seed.ToString() : "unknown")}");
        }

        private void HandleCellDiscovered(SkyCell cell)
        {
            atlas?.RegisterCellSighted(cell);
            crewRoster?.BroadcastDiscovery(cell.Biome);
            ship?.SetLayer(cell.Layer);

            if (cell.HasIsland)
                Feed($"[Discovery] {cell.IslandName} — {cell.Biome}, danger {cell.DangerLevel * 100f:0.#}%");
        }

        private void HandleCellEntered(Vector2Int pos, SkyCell cell)
        {
            if (director != null && !director.HasActiveEncounter)
                director.CheckForEvent();
        }

        private void HandleCombatEnded(Skybound.Combat.CombatPhase phase)
        {
            bool victory = phase == Skybound.Combat.CombatPhase.Victory;
            crewRoster?.BroadcastCombat(victory);

            if (combatManager?.CurrentState != null)
            {
                float hullAfter = combatManager.CurrentState.PlayerHull;
                if (hullAfter < 0.3f) crewRoster?.BroadcastHullCritical();
            }

            Feed($"[Combat] Encounter concluded: {phase}");
        }

        private void Update()
        {
            // Escape = toggle Save/Load panel
            if (Input.GetKeyDown(KeyCode.Escape) && saveLoadPanel != null)
            {
                if (saveLoadPanel.IsVisible) saveLoadPanel.Hide();
                else                         saveLoadPanel.Show();
            }

            // Space = roll for encounter
            if (Input.GetKeyDown(KeyCode.Space))
            {
                if (director == null)        { Feed("[ERR] Director missing."); }
                else if (director.HasActiveEncounter) { Feed("[Nav] Encounter already active — press Enter to resolve."); }
                else
                {
                    Feed("[Nav] Scanning sky...");
                    bool fired = director.CheckForEvent();
                    if (!fired) Feed("[Nav] Nothing detected this pass.");
                }
            }

            // Enter = resolve active encounter
            if (Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter))
            {
                if (director == null)              { Feed("[ERR] Director missing."); }
                else if (!director.HasActiveEncounter) { Feed("[Nav] No active encounter to resolve."); }
                else director.ResolveActiveEncounter();
            }

            // WASD movement — blocked while moving or in active encounter
            if (airship != null && !airship.IsMoving && !director.HasActiveEncounter)
            {
                if (Input.GetKeyDown(KeyCode.W)) airship.TryMove(Vector2Int.up);
                if (Input.GetKeyDown(KeyCode.S)) airship.TryMove(Vector2Int.down);
                if (Input.GetKeyDown(KeyCode.A)) airship.TryMove(Vector2Int.left);
                if (Input.GetKeyDown(KeyCode.D)) airship.TryMove(Vector2Int.right);
            }

            // 1-6 combat actions
            if (combatManager != null && combatManager.InCombat)
            {
                if (Input.GetKeyDown(KeyCode.Alpha1)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.FireCannons);
                if (Input.GetKeyDown(KeyCode.Alpha2)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.Evade);
                if (Input.GetKeyDown(KeyCode.Alpha3)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.Ascend);
                if (Input.GetKeyDown(KeyCode.Alpha4)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.Descend);
                if (Input.GetKeyDown(KeyCode.Alpha5)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.CrewSynergy);
                if (Input.GetKeyDown(KeyCode.Alpha6)) combatManager.SubmitAction(Skybound.Combat.TacticalAction.FleeAttempt);
            }
        }

        private void Feed(string msg) => uiManager?.AppendFeed(msg);
    }
}
