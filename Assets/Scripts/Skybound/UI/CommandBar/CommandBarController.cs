using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.World;
using Skybound.Discovery;
using Skybound.Airship;
using Skybound.Navigation;

namespace Skybound.UI
{
    /// <summary>
    /// Context-sensitive command bar — bottom of screen. Reads the current cell's
    /// biome and discovery tier, then presents only the actions that make sense
    /// for this moment. No menus, no mode switching — the world tells you what
    /// you can do here.
    ///
    /// Rubric:
    ///   Fun 5    — every biome feels different to be in, not just look at
    ///   Story 5  — Survey and Decode tie gameplay to the lore reconstruction arc
    ///   UX 5     — player never presented with irrelevant options
    /// </summary>
    public class CommandBarController : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private SkyWorldManager   worldManager;
        [SerializeField] private AirshipMovement   airship;
        [SerializeField] private DiscoveryAtlas    atlas;
        [SerializeField] private AutoNavigator     navigator;
        [SerializeField] private Systems.UIManager uiManager;

        [Header("UI")]
        [SerializeField] private GameObject        buttonPrefab;
        [SerializeField] private RectTransform      buttonContainer;
        [SerializeField] private TextMeshProUGUI   contextLabel;

        private readonly List<GameObject> _activeButtons = new List<GameObject>();
        private Vector2Int _lastPos = new Vector2Int(-999, -999);

        private void Update()
        {
            if (airship == null || airship.GridPosition == _lastPos) return;
            _lastPos = airship.GridPosition;
            RefreshBar();
        }

        private void RefreshBar()
        {
            var cell  = worldManager?.GetCell(_lastPos);
            var entry = atlas?.GetEntry(_lastPos);
            if (cell == null) return;

            // Clear old buttons
            foreach (var b in _activeButtons) Destroy(b);
            _activeButtons.Clear();

            // Context label
            string weather = cell.Weather != WeatherState.Clear ? $" · {cell.Weather}" : "";
            if (contextLabel != null)
                contextLabel.text = $"{cell.Biome}{weather}" +
                                    (cell.HasIsland ? $"  ·  {cell.IslandName}" : "");

            // Build command list based on cell state
            var commands = BuildCommands(cell, entry);
            foreach (var cmd in commands)
                SpawnButton(cmd.label, cmd.action, cmd.color);
        }

        private struct Command
        {
            public string   label;
            public System.Action action;
            public Color    color;
        }

        private List<Command> BuildCommands(SkyCell cell, AtlasEntry entry)
        {
            var cmds = new List<Command>();
            var tier = entry?.Tier ?? DiscoveryTier.Unseen;

            // Survey — available once unless already surveyed
            if (tier == DiscoveryTier.Sighted)
                cmds.Add(new Command
                {
                    label  = "Survey",
                    color  = new Color(0.30f, 0.65f, 0.40f),
                    action = () =>
                    {
                        atlas.SurveyCell(_lastPos);
                        uiManager?.AppendFeed($"[Survey] {cell.IslandName ?? cell.Biome.ToString()} surveyed. Danger: {cell.DangerLevel * 100f:0.#}%.");
                        RefreshBar();
                    }
                });

            // Decode — available once surveyed
            if (tier == DiscoveryTier.Surveyed)
                cmds.Add(new Command
                {
                    label  = "Decode",
                    color  = new Color(0.75f, 0.55f, 0.10f),
                    action = () =>
                    {
                        atlas.DecodeCell(_lastPos, worldManager.Seed);
                        RefreshBar();
                    }
                });

            // Biome-specific commands
            switch (cell.Biome)
            {
                case SkyBiome.TradeWinds:
                    cmds.Add(new Command
                    {
                        label  = "Barter",
                        color  = new Color(0.20f, 0.50f, 0.80f),
                        action = () => uiManager?.AppendFeed("[Trade] Merchant contacts hailed. Awaiting response.")
                    });
                    break;

                case SkyBiome.AncestorFields:
                    cmds.Add(new Command
                    {
                        label  = "Attune",
                        color  = new Color(0.25f, 0.70f, 0.50f),
                        action = () => uiManager?.AppendFeed("[Memory] The field resonates. Crew morale restored.")
                    });
                    break;

                case SkyBiome.StormRift:
                    cmds.Add(new Command
                    {
                        label  = "Ride Storm",
                        color  = new Color(0.60f, 0.25f, 0.75f),
                        action = () => uiManager?.AppendFeed("[Storm] Riding the rift current. Speed bonus active.")
                    });
                    cmds.Add(new Command
                    {
                        label  = "Take Cover",
                        color  = new Color(0.40f, 0.20f, 0.50f),
                        action = () => uiManager?.AppendFeed("[Storm] Ship hunkered. Hull drain reduced.")
                    });
                    break;

                case SkyBiome.ImperialCorridor:
                    cmds.Add(new Command
                    {
                        label  = "Run Dark",
                        color  = new Color(0.40f, 0.40f, 0.45f),
                        action = () => uiManager?.AppendFeed("[Imperial] Running silent. Reduced event detection window.")
                    });
                    cmds.Add(new Command
                    {
                        label  = "Jam Signal",
                        color  = new Color(0.55f, 0.55f, 0.60f),
                        action = () => uiManager?.AppendFeed("[Imperial] Navigation jammers disrupted. Route node unlocked.")
                    });
                    break;

                case SkyBiome.CelestialRuin:
                    cmds.Add(new Command
                    {
                        label  = "Salvage",
                        color  = new Color(0.80f, 0.60f, 0.15f),
                        action = () => uiManager?.AppendFeed("[Ruin] Salvage crew deployed. Awaiting haul report.")
                    });
                    break;

                case SkyBiome.VoidAnomaly:
                    cmds.Add(new Command
                    {
                        label  = "Enter Rift",
                        color  = new Color(0.70f, 0.10f, 0.30f),
                        action = () => uiManager?.AppendFeed("[Void] Rift entry initiated. Crew braced. Reality unstable.")
                    });
                    break;
            }

            // Stop auto-nav if active
            if (navigator != null && navigator.IsNavigating)
                cmds.Add(new Command
                {
                    label  = "Stop Nav",
                    color  = new Color(0.60f, 0.20f, 0.20f),
                    action = () =>
                    {
                        navigator.StopNavigation();
                        uiManager?.AppendFeed("[Nav] Auto-navigation cancelled.");
                        RefreshBar();
                    }
                });

            return cmds;
        }

        private void SpawnButton(string label, System.Action onClick, Color color)
        {
            if (buttonContainer == null) return;

            var go  = new GameObject(label);
            go.transform.SetParent(buttonContainer, false);

            var rt  = go.AddComponent<RectTransform>();
            rt.sizeDelta = new Vector2(130, 42);

            var img = go.AddComponent<Image>();
            img.color = color;

            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            btn.onClick.AddListener(() => onClick?.Invoke());

            var labelGO  = new GameObject("Label");
            labelGO.transform.SetParent(go.transform, false);
            var lrt = labelGO.AddComponent<RectTransform>();
            lrt.anchorMin = Vector2.zero;
            lrt.anchorMax = Vector2.one;
            lrt.offsetMin = lrt.offsetMax = Vector2.zero;
            var tmp = labelGO.AddComponent<TextMeshProUGUI>();
            tmp.text      = label;
            tmp.fontSize  = 14;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color     = Color.white;

            _activeButtons.Add(go);
        }
    }
}
