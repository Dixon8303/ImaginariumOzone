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
using Skybound.NPC;
using Skybound.Narrative;
using Skybound.Fleet;
using Skybound.Economy;
using Skybound.Guild;
using Skybound.Input;
using Skybound.Quest;

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

            // Cooldown tracker (must exist before GameDirector)
            var cooldownGO      = Child(systemsGO, "EventCooldownTracker");
            var cooldownTracker = cooldownGO.AddComponent<EventCooldownTracker>();

            // GameDirector
            var directorGO = Child(systemsGO, "GameDirector");
            var director   = directorGO.AddComponent<GameDirector>();
            SetField(director, "cooldownTracker", cooldownTracker);
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

            // NPC / Faction systems
            var factionGO      = Child(systemsGO, "FactionSystems");
            var standingManager = factionGO.AddComponent<FactionStandingManager>();
            var dialogueEngine  = factionGO.AddComponent<NPCDialogueEngine>();
            SetField(dialogueEngine, "standingManager", standingManager);

            // Narrative / Lore archive
            var narrativeGO = Child(systemsGO, "Narrative");
            var loreArchive = narrativeGO.AddComponent<LoreArchive>();

            // Fleet
            var fleetGO      = Child(systemsGO, "Fleet");
            var fleetManager = fleetGO.AddComponent<FleetManager>();

            // Economy & Progression
            var ecoGO      = Child(systemsGO, "Economy");
            var economy    = ecoGO.AddComponent<EconomyManager>();
            var progression = ecoGO.AddComponent<ProgressionManager>();
            SetField(progression, "ship",     shipManager);
            SetField(progression, "economy",  economy);

            // Guild
            var guildGO      = Child(systemsGO, "Guild");
            var guildManager = guildGO.AddComponent<GuildManager>();
            SetField(guildManager, "atlas",        atlas);
            SetField(guildManager, "worldManager", worldManager);

            // Quests
            var questGO      = Child(systemsGO, "QuestManager");
            var questManager = questGO.AddComponent<QuestManager>();
            SetField(questManager, "factionStandings", standingManager);
            SetField(questManager, "economy",          economy);
            SetField(questManager, "loreArchive",      loreArchive);
            SetField(questManager, "uiManager",        uiManager);
            var questAssets = LoadAllAssets<QuestData>("Assets/Data/Quests");
            if (questAssets.Length > 0)
            {
                var so   = new SerializedObject(questManager);
                var pool = so.FindProperty("allQuests");
                pool.arraySize = questAssets.Length;
                for (int i = 0; i < questAssets.Length; i++)
                    pool.GetArrayElementAtIndex(i).objectReferenceValue = questAssets[i];
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            // UIManager (created here so later systems can reference it)
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
            SetField(cmdBar, "questManager",   questManager);
            SetField(cmdBar, "ship",           shipManager);
            SetField(cmdBar, "questPanel",     questPanel);
            SetField(cmdBar, "buttonContainer", btnContainerGO.transform as RectTransform);
            SetField(cmdBar, "contextLabel",   ctxTmp);

            // Wire uiManager references into late systems
            SetField(fleetManager,  "uiManager", uiManager);
            SetField(guildManager,  "uiManager", uiManager);

            // Wire navigator → director (pause on encounters) and feed
            SetField(navigator, "director", director);

            // Wire airship cell-moved events into cooldown tracker
            // (done at runtime by GameBootstrap)

            // ── Quest Panel (centered, hidden by default) ─────────────────────
            var questPanelGO = MakeCanvasGroup(canvasGO, "QuestPanel");
            var questPanelCG = questPanelGO.GetComponent<CanvasGroup>();
            questPanelCG.alpha = 0f; questPanelCG.interactable = false; questPanelCG.blocksRaycasts = false;
            var questPanelBg = questPanelGO.AddComponent<Image>();
            questPanelBg.color = new Color(0.06f, 0.04f, 0.14f, 0.96f);

            MakeLabel(questPanelGO, "QuestTitle",   "Quest", new Vector2(0, 180), 22);
            var questSpeaker = MakeLabel(questPanelGO, "SpeakerLabel", "", new Vector2(0, 130), 15);
            var questBody    = MakeLabel(questPanelGO, "BodyLabel",    "", new Vector2(0,  40), 13);

            // Choice button container — vertical layout
            var qChoiceContGO = Child(questPanelGO, "ChoiceContainer");
            var qChoiceRT     = qChoiceContGO.AddComponent<RectTransform>();
            qChoiceRT.anchorMin = new Vector2(0.1f, 0.1f);
            qChoiceRT.anchorMax = new Vector2(0.9f, 0.38f);
            qChoiceRT.offsetMin = qChoiceRT.offsetMax = Vector2.zero;
            var vlg = qChoiceContGO.AddComponent<VerticalLayoutGroup>();
            vlg.spacing = 8;
            vlg.childForceExpandWidth  = true;
            vlg.childForceExpandHeight = false;
            vlg.childAlignment = TextAnchor.UpperCenter;

            var questPanel = questPanelGO.AddComponent<QuestPanel>();
            SetField(questPanel, "questManager",    questManager);
            SetField(questPanel, "canvasGroup",     questPanelCG);
            SetField(questPanel, "titleLabel",      questPanelGO.transform.Find("QuestTitle")?.GetComponent<TextMeshProUGUI>());
            SetField(questPanel, "speakerLabel",    questSpeaker.GetComponent<TextMeshProUGUI>());
            SetField(questPanel, "bodyLabel",       questBody.GetComponent<TextMeshProUGUI>());
            SetField(questPanel, "choiceContainer", qChoiceRT);

            // ── Save/Load Panel (centered, hidden by default) ─────────────────
            var savePanel   = MakeCanvasGroup(canvasGO, "SaveLoadPanel");
            var savePanelCG = savePanel.GetComponent<CanvasGroup>();
            savePanelCG.alpha          = 0f;
            savePanelCG.interactable   = false;
            savePanelCG.blocksRaycasts = false;
            var savePanelBg = savePanel.AddComponent<Image>();
            savePanelBg.color = new Color(0.05f, 0.05f, 0.12f, 0.95f);

            MakeLabel(savePanel, "PanelTitle", "Save / Load", new Vector2(0, 160), 24);

            var slotLabels  = new TextMeshProUGUI[3];
            var saveBtns    = new Button[3];
            var loadBtns    = new Button[3];
            for (int s = 0; s < 3; s++)
            {
                float y = 80f - s * 80f;
                var row = Child(savePanel, $"Slot{s}");
                row.AddComponent<RectTransform>().anchoredPosition = new Vector2(0, y);

                var lbl = MakeLabel(row, "Label", $"Slot {s+1}  —  Empty", new Vector2(-120, 0), 14);
                slotLabels[s] = lbl.GetComponent<TextMeshProUGUI>();

                var sb = MakeButton(row, "SaveBtn", "Save", new Vector2(80, 0));
                sb.GetComponent<RectTransform>().sizeDelta = new Vector2(90, 36);
                saveBtns[s] = sb.GetComponent<Button>();

                var lb = MakeButton(row, "LoadBtn", "Load", new Vector2(180, 0));
                lb.GetComponent<RectTransform>().sizeDelta = new Vector2(90, 36);
                loadBtns[s] = lb.GetComponent<Button>();
            }
            var closeBtn = MakeButton(savePanel, "CloseBtn", "Close", new Vector2(0, -180));

            var savePanelComp = savePanel.AddComponent<SaveLoadPanel>();
            SetField(savePanelComp, "saveManager", saveManager);
            // Slot arrays need direct assignment — use SerializedObject for arrays
            {
                var so = new SerializedObject(savePanelComp);
                var lblProp  = so.FindProperty("slotLabels");
                var saveProp = so.FindProperty("saveButtons");
                var loadProp = so.FindProperty("loadButtons");
                if (lblProp != null)
                {
                    lblProp.arraySize = 3;
                    for (int s = 0; s < 3; s++) lblProp.GetArrayElementAtIndex(s).objectReferenceValue = slotLabels[s];
                }
                if (saveProp != null)
                {
                    saveProp.arraySize = 3;
                    for (int s = 0; s < 3; s++) saveProp.GetArrayElementAtIndex(s).objectReferenceValue = saveBtns[s];
                }
                if (loadProp != null)
                {
                    loadProp.arraySize = 3;
                    for (int s = 0; s < 3; s++) loadProp.GetArrayElementAtIndex(s).objectReferenceValue = loadBtns[s];
                }
                so.FindProperty("closeButton")?.objectReferenceValue.Equals(closeBtn.GetComponent<Button>());
                SetField(savePanelComp, "closeButton", closeBtn.GetComponent<Button>());
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            // ── GameBootstrap (wires runtime events) ─────────────────────────
            var bootstrapGO = Child(systemsGO, "GameBootstrap");
            var bootstrap   = bootstrapGO.AddComponent<GameBootstrap>();
            SetField(bootstrap, "ship",            shipManager);
            SetField(bootstrap, "crew",            crewManager);
            SetField(bootstrap, "director",        director);
            SetField(bootstrap, "uiManager",       uiManager);
            SetField(bootstrap, "worldManager",    worldManager);
            SetField(bootstrap, "airship",         airship);
            SetField(bootstrap, "combatManager",   combatManager);
            SetField(bootstrap, "atlas",           atlas);
            SetField(bootstrap, "crewRoster",      crewRoster);
            SetField(bootstrap, "cooldownTracker", cooldownTracker);
            SetField(bootstrap, "saveLoadPanel",   savePanelComp);

            // ── Touch Input ──────────────────────────────────────────────────
            var touchGO    = Child(systemsGO, "TouchInput");
            var touchInput = touchGO.AddComponent<TouchInputHandler>();
            SetField(touchInput, "airship",       airship);
            SetField(touchInput, "director",      director);
            SetField(touchInput, "saveLoadPanel", savePanelComp);

            // ── Status Bar (top strip) ────────────────────────────────────────
            var statusBarGO = Child(canvasGO, "StatusBar");
            var statusRT    = statusBarGO.AddComponent<RectTransform>();
            statusRT.anchorMin       = new Vector2(0f, 1f);
            statusRT.anchorMax       = new Vector2(1f, 1f);
            statusRT.pivot           = new Vector2(0.5f, 1f);
            statusRT.sizeDelta       = new Vector2(0, 48);
            statusRT.anchoredPosition = Vector2.zero;
            var statusBg = statusBarGO.AddComponent<Image>();
            statusBg.color = new Color(0.04f, 0.06f, 0.16f, 0.92f);

            var hlgStatus = statusBarGO.AddComponent<HorizontalLayoutGroup>();
            hlgStatus.childAlignment        = TextAnchor.MiddleCenter;
            hlgStatus.childForceExpandWidth = true;
            hlgStatus.spacing               = 16;
            hlgStatus.padding               = new RectOffset(12, 12, 4, 4);

            var coinsLbl   = MakeStatusLabel(statusBarGO, "CoinsLabel",   "◈ 100",  new Color(1f, 0.85f, 0.3f));
            var guildLbl   = MakeStatusLabel(statusBarGO, "GuildLabel",   "Guild: Scout · 0 rep", new Color(0.6f, 1f, 0.7f));
            var factionLbl = MakeStatusLabel(statusBarGO, "FactionLabel", "OYA● KEM● AMR● IMP● VWK●", new Color(0.8f, 0.9f, 1f));

            var statusBar = statusBarGO.AddComponent<StatusBarController>();
            SetField(statusBar, "economy",          economy);
            SetField(statusBar, "guild",            guildManager);
            SetField(statusBar, "factionStandings", standingManager);
            SetField(statusBar, "coinsLabel",       coinsLbl);
            SetField(statusBar, "guildLabel",       guildLbl);
            SetField(statusBar, "factionLabel",     factionLbl);

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
            Debug.Log($"[SceneBuilder] Scene built. {evtCount} events loaded.\n" +
                      "Keyboard: WASD=move, Space=roll, Enter=resolve, 1-6=combat, Esc=save panel\n" +
                      "Touch: swipe=move, tap=roll, 2-finger tap=resolve, 3-finger tap=save panel\n" +
                      "Run Tools > Skybound > Generate Narrative Assets to populate NPC/Mythic/Lore data.");
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

        static TextMeshProUGUI MakeStatusLabel(GameObject parent, string name, string text, Color color)
        {
            var go = Child(parent, name);
            go.AddComponent<RectTransform>();
            var tmp    = go.AddComponent<TextMeshProUGUI>();
            tmp.text      = text;
            tmp.fontSize  = 12;
            tmp.color     = color;
            tmp.alignment = TextAlignmentOptions.Center;
            return tmp;
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
