#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEngine.UI;
using TMPro;
using Skybound.Ship;
using Skybound.Systems;
using Skybound.Save;
using Skybound.UI;
using Skybound.World;
using Skybound.Combat;
using Skybound.Discovery;
using Skybound.Crew;
using Skybound.Airship;
using Skybound.Navigation;

namespace Skybound.Editor
{
    /// <summary>
    /// Builds the complete connected Skybound scene with one menu click.
    /// All 5 core systems are instantiated and wired: World, Airship, Combat, Discovery, Crew.
    /// Run: Tools > Skybound > Build Scene
    /// Controls in Play mode:
    ///   WASD        — move airship
    ///   Space       — roll for event
    ///   Enter       — resolve active encounter
    ///   1-6         — combat actions (Fire, Evade, Ascend, Descend, Synergy, Flee)
    /// </summary>
    public static class SceneBuilder
    {
        [MenuItem("Tools/Skybound/Build Scene")]
        public static void BuildScene()
        {
            var old = GameObject.Find("[Skybound]");
            if (old != null) Object.DestroyImmediate(old);

            var root = new GameObject("[Skybound]");

            // ── Systems ──────────────────────────────────────────────────────
            var systemsGO = Child(root, "Systems");

            // Ship
            var shipGO      = Child(systemsGO, "Ship");
            var shipManager = shipGO.AddComponent<ShipManager>();
            var crewManager = shipGO.AddComponent<ShipCrewManager>();
            var saveManager = shipGO.AddComponent<SaveManager>();
            SetField(saveManager, "ship", shipManager);
            SetField(saveManager, "crew", crewManager);

            // World
            var worldGO      = Child(systemsGO, "World");
            var worldManager = worldGO.AddComponent<SkyWorldManager>();

            // Airship
            var airshipGO = Child(systemsGO, "Airship");
            var airship   = airshipGO.AddComponent<AirshipMovement>();
            SetField(airship, "world", worldManager);

            // Airship visual (attaches to same GO — follows movement transform)
            var visualGO = Child(airshipGO, "Visual");
            var visual   = visualGO.AddComponent<AirshipVisual>();
            SetField(visual, "movement",     airship);
            SetField(visual, "worldManager", worldManager);

            // Auto-navigator
            var navGO    = Child(systemsGO, "AutoNavigator");
            var navigator = navGO.AddComponent<AutoNavigator>();
            SetField(navigator, "airship",      airship);
            SetField(navigator, "worldManager", worldManager);

            // GameDirector
            var directorGO = Child(systemsGO, "GameDirector");
            var director   = directorGO.AddComponent<GameDirector>();
            var eventAssets = LoadAllAssets<Skybound.Events.SkyEvent>("Assets/Data/SkyEvents");
            if (eventAssets.Length > 0)
            {
                var so   = new SerializedObject(director);
                var pool = so.FindProperty("eventPool");
                pool.arraySize = eventAssets.Length;
                for (int i = 0; i < eventAssets.Length; i++)
                    pool.GetArrayElementAtIndex(i).objectReferenceValue = eventAssets[i];
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            // Combat
            var combatGO     = Child(systemsGO, "Combat");
            var combatManager = combatGO.AddComponent<CombatManager>();

            // Discovery
            var atlasGO = Child(systemsGO, "DiscoveryAtlas");
            var atlas   = atlasGO.AddComponent<DiscoveryAtlas>();

            // Crew
            var rosterGO    = Child(systemsGO, "CrewRoster");
            var crewRoster  = rosterGO.AddComponent<CrewRosterManager>();

            // UIManager
            var uiManagerGO = Child(systemsGO, "UIManager");
            var uiManager   = uiManagerGO.AddComponent<UIManager>();
            SetField(uiManager, "director", director);

            // ── Canvas ───────────────────────────────────────────────────────
            var canvasGO = Child(root, "Canvas");
            var canvas   = canvasGO.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGO.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasGO.AddComponent<GraphicRaycaster>();

            // Exploration HUD
            var hudLayer   = MakeCanvasGroup(canvasGO, "ExplorationHUD");
            var hullSlider = MakeSlider(hudLayer, "HullSlider",   new Vector2(0, -30),  new Vector2(300, 20));
            var layerLabel = MakeLabel(hudLayer,  "LayerLabel",   "LowSky",             new Vector2(0, -60));
            var crewLabel  = MakeLabel(hudLayer,  "CrewLabel",    "Crew 0/4",           new Vector2(0, -90));
            var posLabel   = MakeLabel(hudLayer,  "PosLabel",     "Grid (0,0)",         new Vector2(0, -120));
            var checkBtn   = MakeButton(hudLayer, "CheckEventBtn","Roll Event",         new Vector2(0, -165));

            var explorationHUD = hudLayer.AddComponent<ExplorationHUD>();
            SetField(explorationHUD, "ship",           shipManager);
            SetField(explorationHUD, "director",       director);
            SetField(explorationHUD, "hullSlider",     hullSlider);
            SetField(explorationHUD, "layerLabel",     layerLabel.GetComponent<TextMeshProUGUI>());
            SetField(explorationHUD, "crewCountLabel", crewLabel.GetComponent<TextMeshProUGUI>());
            SetField(explorationHUD, "checkEventButton", checkBtn.GetComponent<Button>());

            SetField(uiManager, "explorationHud", hudLayer.GetComponent<CanvasGroup>());

            // Combat action bar (shown during combat)
            var combatLayer = MakeCanvasGroup(canvasGO, "CombatHUD");
            combatLayer.GetComponent<CanvasGroup>().alpha = 0f;
            combatLayer.GetComponent<CanvasGroup>().interactable = false;
            combatLayer.GetComponent<CanvasGroup>().blocksRaycasts = false;

            MakeLabel(combatLayer, "CombatHelp",
                "1=Fire  2=Evade  3=Ascend  4=Descend  5=Synergy  6=Flee",
                new Vector2(0, 120), 14);

            // Minimap (top-right corner)
            var minimapGO = Child(canvasGO, "Minimap");
            var minimapRT = minimapGO.AddComponent<RectTransform>();
            minimapRT.anchorMin = new Vector2(1f, 1f);
            minimapRT.anchorMax = new Vector2(1f, 1f);
            minimapRT.pivot     = new Vector2(1f, 1f);
            minimapRT.sizeDelta = new Vector2(160, 160);
            minimapRT.anchoredPosition = new Vector2(-10, -10);
            var minimapBg = minimapGO.AddComponent<UnityEngine.UI.Image>();
            minimapBg.color = new Color(0f, 0f, 0f, 0.6f);
            var rawImg = minimapGO.AddComponent<UnityEngine.UI.RawImage>();
            rawImg.color = Color.white;

            var minimap = minimapGO.AddComponent<MinimapRenderer>();
            SetField(minimap, "worldManager", worldManager);
            SetField(minimap, "airship",      airship);
            SetField(minimap, "atlas",        atlas);

            // Encounter overlay
            var overlayLayer = MakeCanvasGroup(canvasGO, "EncounterOverlay");
            overlayLayer.GetComponent<CanvasGroup>().alpha = 0f;
            overlayLayer.GetComponent<CanvasGroup>().interactable = false;
            overlayLayer.GetComponent<CanvasGroup>().blocksRaycasts = false;

            var titleLabel   = MakeLabel(overlayLayer,  "TitleLabel",   "Encounter",   new Vector2(0,  100), 28);
            var introLabel   = MakeLabel(overlayLayer,  "IntroLabel",   "",            new Vector2(0,   40));
            var outcomeLabel = MakeLabel(overlayLayer,  "OutcomeLabel", "",            new Vector2(0,  -20));
            var resolveBtn   = MakeButton(overlayLayer, "ResolveBtn",   "Engage",      new Vector2(0,  -80));

            var encounterPanel = overlayLayer.AddComponent<EncounterPanel>();
            SetField(encounterPanel, "director",          director);
            SetField(encounterPanel, "titleLabel",        titleLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "introLabel",        introLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "outcomeLabel",      outcomeLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "resolveButton",     resolveBtn.GetComponent<Button>());
            SetField(encounterPanel, "resolveButtonLabel",resolveBtn.GetComponentInChildren<TextMeshProUGUI>());

            SetField(uiManager, "encounterOverlay", overlayLayer.GetComponent<CanvasGroup>());

            // Discovery feed (scrolling log, bottom-left)
            var feedGO      = Child(canvasGO, "FeedView");
            var feedRect    = feedGO.AddComponent<RectTransform>();
            feedRect.anchorMin = new Vector2(0f, 0f);
            feedRect.anchorMax = new Vector2(0.42f, 0.32f);
            feedRect.offsetMin = feedRect.offsetMax = Vector2.zero;

            var scrollRect = feedGO.AddComponent<ScrollRect>();
            var feedContent = Child(feedGO, "Content");
            feedContent.AddComponent<RectTransform>();
            var feedText = feedContent.AddComponent<TextMeshProUGUI>();
            feedText.fontSize = 13;
            feedText.color = new Color(0.85f, 0.95f, 1f);
            scrollRect.content    = feedContent.GetComponent<RectTransform>();
            scrollRect.vertical   = true;
            scrollRect.horizontal = false;

            var feedView = feedGO.AddComponent<FeedView>();
            SetField(feedView, "uiManager",  uiManager);
            SetField(feedView, "feedText",   feedText);
            SetField(feedView, "scrollRect", scrollRect);

            // ── Command Bar (bottom of screen) ───────────────────────────────
            var cmdBarGO = Child(canvasGO, "CommandBar");
            var cmdBarRT = cmdBarGO.AddComponent<RectTransform>();
            cmdBarRT.anchorMin = new Vector2(0f, 0f);
            cmdBarRT.anchorMax = new Vector2(1f, 0f);
            cmdBarRT.pivot     = new Vector2(0.5f, 0f);
            cmdBarRT.sizeDelta = new Vector2(0, 90);
            cmdBarRT.anchoredPosition = Vector2.zero;
            var cmdBarBg = cmdBarGO.AddComponent<Image>();
            cmdBarBg.color = new Color(0.05f, 0.05f, 0.10f, 0.85f);

            // Context label (biome name + island name)
            var ctxLabelGO = Child(cmdBarGO, "ContextLabel");
            var ctxRT = ctxLabelGO.AddComponent<RectTransform>();
            ctxRT.anchorMin = new Vector2(0f, 0.6f);
            ctxRT.anchorMax = new Vector2(1f, 1f);
            ctxRT.offsetMin = ctxRT.offsetMax = Vector2.zero;
            var ctxTmp = ctxLabelGO.AddComponent<TextMeshProUGUI>();
            ctxTmp.fontSize  = 13;
            ctxTmp.color     = new Color(0.70f, 0.85f, 1f);
            ctxTmp.alignment = TextAlignmentOptions.Center;

            // Button container (horizontal row)
            var btnContainerGO = Child(cmdBarGO, "Buttons");
            var btnContainerRT = btnContainerGO.AddComponent<RectTransform>();
            btnContainerRT.anchorMin = new Vector2(0f, 0f);
            btnContainerRT.anchorMax = new Vector2(1f, 0.58f);
            btnContainerRT.offsetMin = new Vector2(8, 6);
            btnContainerRT.offsetMax = new Vector2(-8, -4);
            var hlg = btnContainerGO.AddComponent<HorizontalLayoutGroup>();
            hlg.spacing           = 8;
            hlg.childForceExpandWidth  = false;
            hlg.childForceExpandHeight = true;
            hlg.childAlignment    = TextAnchor.MiddleCenter;

            var cmdBar = cmdBarGO.AddComponent<CommandBarController>();
            SetField(cmdBar, "worldManager",   worldManager);
            SetField(cmdBar, "airship",        airship);
            SetField(cmdBar, "atlas",          atlas);
            SetField(cmdBar, "navigator",      navigator);
            SetField(cmdBar, "uiManager",      uiManager);
            SetField(cmdBar, "buttonContainer", btnContainerGO.transform as RectTransform);
            SetField(cmdBar, "contextLabel",   ctxTmp);

            // Wire navigator → director (pause on encounters) and feed
            SetField(navigator, "director", director);

            // ── GameBootstrap (wires runtime events) ─────────────────────────
            var bootstrapGO = Child(systemsGO, "GameBootstrap");
            var bootstrap   = bootstrapGO.AddComponent<GameBootstrap>();
            SetField(bootstrap, "ship",         shipManager);
            SetField(bootstrap, "crew",         crewManager);
            SetField(bootstrap, "director",     director);
            SetField(bootstrap, "uiManager",    uiManager);
            SetField(bootstrap, "worldManager", worldManager);
            SetField(bootstrap, "airship",      airship);
            SetField(bootstrap, "combatManager",combatManager);
            SetField(bootstrap, "atlas",        atlas);
            SetField(bootstrap, "crewRoster",   crewRoster);

            // ── Camera ───────────────────────────────────────────────────────
            var camGO = Child(root, "Camera");
            var cam   = camGO.AddComponent<Camera>();
            cam.backgroundColor = new Color(0.04f, 0.06f, 0.14f);
            cam.clearFlags      = CameraClearFlags.SolidColor;
            cam.orthographic    = true;
            cam.orthographicSize = 5f;
            camGO.transform.position = new Vector3(0, 0, -10f);

            EditorUtility.SetDirty(root);
            Selection.activeGameObject = root;

            int evtCount = eventAssets.Length;
            Debug.Log($"[SceneBuilder] Scene built. {evtCount} events loaded. " +
                      "Play → WASD=move, Space=roll, Enter=resolve, 1-6=combat actions.");
        }

        // ── Helpers ──────────────────────────────────────────────────────────

        static GameObject Child(GameObject parent, string name)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent.transform, false);
            return go;
        }

        static GameObject MakeCanvasGroup(GameObject parent, string name)
        {
            var go = Child(parent, name);
            var rt = go.AddComponent<RectTransform>();
            rt.anchorMin = Vector2.zero;
            rt.anchorMax = Vector2.one;
            rt.offsetMin = rt.offsetMax = Vector2.zero;
            go.AddComponent<CanvasGroup>();
            return go;
        }

        static GameObject MakeLabel(GameObject parent, string name, string text,
            Vector2 anchoredPos, int fontSize = 18)
        {
            var go = Child(parent, name);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = new Vector2(500, 40);
            rt.anchoredPosition = anchoredPos;
            var tmp = go.AddComponent<TextMeshProUGUI>();
            tmp.text = text;
            tmp.fontSize = fontSize;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color = Color.white;
            return go;
        }

        static GameObject MakeButton(GameObject parent, string name, string label, Vector2 anchoredPos)
        {
            var go = Child(parent, name);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = new Vector2(200, 50);
            rt.anchoredPosition = anchoredPos;
            var img = go.AddComponent<Image>();
            img.color = new Color(0.18f, 0.36f, 0.72f);
            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;

            var labelGO = Child(go, "Label");
            var lrt = labelGO.AddComponent<RectTransform>();
            lrt.anchorMin = Vector2.zero;
            lrt.anchorMax = Vector2.one;
            lrt.offsetMin = lrt.offsetMax = Vector2.zero;
            var tmp = labelGO.AddComponent<TextMeshProUGUI>();
            tmp.text = label;
            tmp.fontSize = 16;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color = Color.white;
            return go;
        }

        static GameObject MakeSlider(GameObject parent, string name, Vector2 pos, Vector2 size)
        {
            var go = Child(parent, name);
            var rt = go.AddComponent<RectTransform>();
            rt.sizeDelta = size;
            rt.anchoredPosition = pos;

            var bg = Child(go, "Background");
            bg.AddComponent<RectTransform>().sizeDelta = size;
            bg.AddComponent<Image>().color = new Color(0.25f, 0.08f, 0.08f);

            var fill = Child(go, "Fill");
            fill.AddComponent<RectTransform>().sizeDelta = size;
            var fillImg = fill.AddComponent<Image>();
            fillImg.color = new Color(0.75f, 0.18f, 0.18f);

            var slider = go.AddComponent<Slider>();
            slider.fillRect = fill.GetComponent<RectTransform>();
            slider.value = 1f;
            slider.interactable = false;
            return go;
        }

        static T[] LoadAllAssets<T>(string folder) where T : Object
        {
            var guids = AssetDatabase.FindAssets($"t:{typeof(T).Name}", new[] { folder });
            var results = new T[guids.Length];
            for (int i = 0; i < guids.Length; i++)
                results[i] = AssetDatabase.LoadAssetAtPath<T>(AssetDatabase.GUIDToAssetPath(guids[i]));
            return results;
        }

        static void SetField(Object target, string field, Object value)
        {
            var so   = new SerializedObject(target);
            var prop = so.FindProperty(field);
            if (prop != null) { prop.objectReferenceValue = value; so.ApplyModifiedPropertiesWithoutUndo(); }
            else Debug.LogWarning($"[SceneBuilder] Field '{field}' not found on {target.GetType().Name}");
        }
    }
}
#endif
