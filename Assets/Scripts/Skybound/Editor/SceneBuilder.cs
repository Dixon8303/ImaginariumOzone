#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using UnityEngine.UI;
using TMPro;
using Skybound.Ship;
using Skybound.Systems;
using Skybound.Save;
using Skybound.UI;

namespace Skybound.Editor
{
    /// <summary>
    /// Builds the full Skybound scene from scratch with one menu click.
    /// Run: Tools > Skybound > Build Scene
    /// Safe to re-run — clears old Skybound root first.
    /// After running: hit Play and press Space to roll for events, Enter to resolve.
    /// </summary>
    public static class SceneBuilder
    {
        [MenuItem("Tools/Skybound/Build Scene")]
        public static void BuildScene()
        {
            // Remove previous Skybound root so re-runs are clean
            var old = GameObject.Find("[Skybound]");
            if (old != null) Object.DestroyImmediate(old);

            var root = new GameObject("[Skybound]");

            // ── Game Systems ────────────────────────────────────────────────
            var systemsGO = Child(root, "Systems");

            var shipGO = Child(systemsGO, "Ship");
            var shipManager = shipGO.AddComponent<ShipManager>();
            var crewManager = shipGO.AddComponent<ShipCrewManager>();
            var saveManager = shipGO.AddComponent<SaveManager>();
            SetField(saveManager, "ship", shipManager);
            SetField(saveManager, "crew", crewManager);

            var directorGO = Child(systemsGO, "GameDirector");
            var director = directorGO.AddComponent<GameDirector>();

            // Load any SkyEvent assets from Assets/Data/SkyEvents/ into the pool
            var eventAssets = LoadAllAssets<Skybound.Events.SkyEvent>("Assets/Data/SkyEvents");
            var eventPoolProp = new SerializedObject(director).FindProperty("eventPool");
            if (eventAssets.Length > 0)
            {
                var so = new SerializedObject(director);
                var pool = so.FindProperty("eventPool");
                pool.arraySize = eventAssets.Length;
                for (int i = 0; i < eventAssets.Length; i++)
                    pool.GetArrayElementAtIndex(i).objectReferenceValue = eventAssets[i];
                so.ApplyModifiedPropertiesWithoutUndo();
            }

            // Bootstrap (keyboard test controls: Space=check, Enter=resolve)
            var bootstrap = systemsGO.AddComponent<SkyboundBootstrap>();
            SetField(bootstrap, "director", director);
            SetField(bootstrap, "ship", shipGO.GetComponent<Skybound.Systems.DebugShipManager>());

            // Wire director → UIManager later after UI is built

            // ── Canvas ──────────────────────────────────────────────────────
            var canvasGO = Child(root, "Canvas");
            var canvas = canvasGO.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasGO.AddComponent<CanvasScaler>().uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            canvasGO.AddComponent<GraphicRaycaster>();

            // Exploration HUD layer
            var hudLayer = MakeCanvasGroup(canvasGO, "ExplorationHUD");
            var hullSlider = MakeSlider(hudLayer, "HullSlider", new Vector2(0, -30), new Vector2(300, 20));
            var layerLabel = MakeLabel(hudLayer, "LayerLabel", "LowSky", new Vector2(0, -60));
            var crewLabel  = MakeLabel(hudLayer, "CrewLabel",  "Crew 0/4", new Vector2(0, -90));
            var checkBtn   = MakeButton(hudLayer, "CheckEventBtn", "Roll Event", new Vector2(0, -130));

            var explorationHUD = hudLayer.AddComponent<ExplorationHUD>();
            SetField(explorationHUD, "ship", shipManager);
            SetField(explorationHUD, "director", director);
            SetField(explorationHUD, "hullSlider", hullSlider);
            SetField(explorationHUD, "layerLabel", layerLabel.GetComponent<TextMeshProUGUI>());
            SetField(explorationHUD, "crewCountLabel", crewLabel.GetComponent<TextMeshProUGUI>());
            SetField(explorationHUD, "checkEventButton", checkBtn.GetComponent<Button>());

            // Encounter overlay layer (hidden by default)
            var overlayLayer = MakeCanvasGroup(canvasGO, "EncounterOverlay");
            overlayLayer.GetComponent<CanvasGroup>().alpha = 0f;
            overlayLayer.GetComponent<CanvasGroup>().interactable = false;
            overlayLayer.GetComponent<CanvasGroup>().blocksRaycasts = false;

            var titleLabel   = MakeLabel(overlayLayer, "TitleLabel",   "Encounter Title", new Vector2(0, 100), fontSize: 28);
            var introLabel   = MakeLabel(overlayLayer, "IntroLabel",   "Intro text here.", new Vector2(0, 40));
            var outcomeLabel = MakeLabel(overlayLayer, "OutcomeLabel", "",                 new Vector2(0, -20));
            var resolveBtn   = MakeButton(overlayLayer, "ResolveBtn", "Engage",            new Vector2(0, -80));

            var encounterPanel = overlayLayer.AddComponent<EncounterPanel>();
            SetField(encounterPanel, "director", director);
            SetField(encounterPanel, "titleLabel",        titleLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "introLabel",        introLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "outcomeLabel",      outcomeLabel.GetComponent<TextMeshProUGUI>());
            SetField(encounterPanel, "resolveButton",     resolveBtn.GetComponent<Button>());
            SetField(encounterPanel, "resolveButtonLabel", resolveBtn.GetComponentInChildren<TextMeshProUGUI>());

            // Feed (scrolling log — sits below HUD)
            var feedGO = Child(canvasGO, "FeedView");
            var feedRect = feedGO.AddComponent<RectTransform>();
            feedRect.anchorMin = new Vector2(0, 0);
            feedRect.anchorMax = new Vector2(0.4f, 0.35f);
            feedRect.offsetMin = feedRect.offsetMax = Vector2.zero;

            var scrollRect = feedGO.AddComponent<ScrollRect>();
            var feedContent = Child(feedGO, "Content");
            feedContent.AddComponent<RectTransform>();
            var feedText = feedContent.AddComponent<TextMeshProUGUI>();
            feedText.fontSize = 14;
            feedText.color = Color.white;
            scrollRect.content = feedContent.GetComponent<RectTransform>();
            scrollRect.vertical = true;
            scrollRect.horizontal = false;

            var uiManagerGO = Child(systemsGO, "UIManager");
            var uiManager = uiManagerGO.AddComponent<UIManager>();
            SetField(uiManager, "director", director);
            SetField(uiManager, "explorationHud", hudLayer.GetComponent<CanvasGroup>());
            SetField(uiManager, "encounterOverlay", overlayLayer.GetComponent<CanvasGroup>());

            var feedView = feedGO.AddComponent<FeedView>();
            SetField(feedView, "uiManager", uiManager);
            SetField(feedView, "feedText", feedText);
            SetField(feedView, "scrollRect", scrollRect);

            // ── Background ──────────────────────────────────────────────────
            var bgGO = Child(root, "Background");
            var cam = bgGO.AddComponent<Camera>();
            cam.backgroundColor = new Color(0.05f, 0.07f, 0.15f);
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.orthographic = true;

            EditorUtility.SetDirty(root);
            Selection.activeGameObject = root;
            Debug.Log("[SceneBuilder] Scene built. Hit Play, then Space to roll events, Enter to resolve.");
        }

        // ── Helpers ─────────────────────────────────────────────────────────

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
            rt.sizeDelta = new Vector2(400, 40);
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
            img.color = new Color(0.2f, 0.4f, 0.8f);
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
            bg.AddComponent<Image>().color = new Color(0.3f, 0.1f, 0.1f);

            var fill = Child(go, "Fill");
            fill.AddComponent<RectTransform>().sizeDelta = size;
            var fillImg = fill.AddComponent<Image>();
            fillImg.color = new Color(0.8f, 0.2f, 0.2f);

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
            var so = new SerializedObject(target);
            var prop = so.FindProperty(field);
            if (prop != null) { prop.objectReferenceValue = value; so.ApplyModifiedPropertiesWithoutUndo(); }
        }
    }
}
#endif
