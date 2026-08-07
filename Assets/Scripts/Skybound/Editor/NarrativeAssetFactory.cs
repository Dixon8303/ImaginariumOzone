#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using Skybound.NPC;
using Skybound.Narrative;
using Skybound.World;
using Skybound.Events;

namespace Skybound.Editor
{
    /// <summary>
    /// Generates sample NPC Encounter, Mythic Event, and Lore Fragment assets.
    /// Also creates matching SkyEvent wrappers so GameDirector picks them up.
    /// Run: Tools > Skybound > Generate Narrative Assets
    /// </summary>
    public static class NarrativeAssetFactory
    {
        private const string NPC_DIR   = "Assets/Data/NPCEncounters";
        private const string MYTH_DIR  = "Assets/Data/MythicEvents";
        private const string LORE_DIR  = "Assets/Data/LoreFragments";
        private const string EVENT_DIR = "Assets/Data/SkyEvents";

        [MenuItem("Tools/Skybound/Generate Narrative Assets")]
        public static void Generate()
        {
            EnsureDir("Assets/Data");
            EnsureDir(NPC_DIR);
            EnsureDir(MYTH_DIR);
            EnsureDir(LORE_DIR);
            EnsureDir(EVENT_DIR);
            EnsureDir($"{EVENT_DIR}/Encounters");

            CreateLoreFragments();
            CreateNPCEncounters();
            CreateMythicEvents();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[NarrativeAssetFactory] NPC, Mythic, and Lore assets generated.");
        }

        // ── Lore Fragments ────────────────────────────────────────────────────

        static void CreateLoreFragments()
        {
            MakeLore("lore_unmooring_01",
                era: "Age of Unmooring",
                speaker: "Elder Kemi Osei",
                body: "The sky had a floor once. We remember the day it dissolved. Our ancestors did not fall — they rose, and called it liberation.",
                hint: "High-altitude cells carry ancestral memory. Decode CelestialRuin cells to hear more.",
                minDecoded: 0, requiresMythic: false);

            MakeLore("lore_unmooring_02",
                era: "Age of Unmooring",
                speaker: "Chart-Fragment, source unknown",
                body: "Coordinates recorded here lead only to wind. Whatever the empire mapped no longer exists. They mapped the wrong things.",
                hint: "ImperialCorridor cells cost more to cross — but hide suppressed routes.",
                minDecoded: 3, requiresMythic: false);

            MakeLore("lore_imperial_veil_01",
                era: "Imperial Veil",
                speaker: "Amara Freehold Oral Record",
                body: "They called it a census. They called it a survey. They called it protection. Each word meant the same thing: your sky is now ours.",
                hint: "Imperial Syndicate standing affects event frequency in corridor biomes.",
                minDecoded: 5, requiresMythic: false);

            MakeLore("lore_imperial_veil_02",
                era: "Imperial Veil",
                speaker: "VoidWalker Transmission, partially decoded",
                body: "The empire cannot map what does not agree to be seen. We are cartographic refusal.",
                hint: "VoidAnomaly cells are ungovernable — no Imperial events trigger there.",
                minDecoded: 8, requiresMythic: true);

            MakeLore("lore_reconstruction_01",
                era: "Reconstruction",
                speaker: "Navigator Yetunde, KemiAlliance log",
                body: "We are not rebuilding what was. We are building what should have been. The difference is everything.",
                hint: "Guild tier Cartographer unlocks a bonus decode on every tenth cell.",
                minDecoded: 12, requiresMythic: false);

            MakeLore("lore_reconstruction_02",
                era: "Reconstruction",
                speaker: "The Sky Itself — interpreted",
                body: "You found the last piece. The history is complete. What you do with it is the only part we could not predict.",
                hint: "Full reconstruction unlocks the VoidWalker alliance path.",
                minDecoded: 20, requiresMythic: true);
        }

        // ── NPC Encounters ────────────────────────────────────────────────────

        static void CreateNPCEncounters()
        {
            MakeNPC("npc_oya_merchant", FactionId.OyaCoalition, "Merchant Dayo",
                new[]
                {
                    "Fair winds brought you here. What are you trading?",
                    "The coalition routes are open — for a reasonable toll.",
                    "You look like someone who's seen a storm rift. Buy some hull resin?"
                },
                cooperativeDelta: 1, hostileDelta: -1, loreReward: "lore_unmooring_01",
                allBiomes: true);

            MakeNPC("npc_kemi_archivist", FactionId.KemiNavigators, "Archivist Folake",
                new[]
                {
                    "Your atlas is incomplete. Shall we trade charts?",
                    "We know routes the empire erased. Trust is the currency.",
                    "Every cell you've decoded — we felt it. The ancestors noticed."
                },
                cooperativeDelta: 1, hostileDelta: -1, loreReward: "lore_unmooring_02",
                allBiomes: true);

            MakeNPC("npc_amara_scout", FactionId.AmaraFreeholds, "Scout Rashida",
                new[]
                {
                    "Freeholds don't stop ships that fly clean. You flying clean?",
                    "Heard you caused trouble in the corridor. Good.",
                    "We track imperial patrol schedules. Useful if you're heading east."
                },
                cooperativeDelta: 1, hostileDelta: -2, loreReward: "lore_imperial_veil_01",
                allBiomes: true);

            MakeNPC("npc_imperial_inspector", FactionId.ImperialSyndicate, "Inspector Vault-7",
                new[]
                {
                    "Navigation permit. Now.",
                    "Your vessel is flagged in sector twelve. Explain.",
                    "Compliance is the fastest route through imperial space."
                },
                cooperativeDelta: 1, hostileDelta: -1, loreReward: "",
                allBiomes: false);

            MakeNPC("npc_voidwalker_echo", FactionId.VoidWalkers, "Echo-Without-Name",
                new[]
                {
                    "We are not met. We are remembered.",
                    "The rift behind you is also in front of you.",
                    "You carry a chart to somewhere that doesn't exist yet. Interesting."
                },
                cooperativeDelta: 2, hostileDelta: 0, loreReward: "lore_imperial_veil_02",
                allBiomes: false);
        }

        // ── Mythic Events ─────────────────────────────────────────────────────

        static void CreateMythicEvents()
        {
            MakeMythic("mythic_sky_collapse",
                title: "The Memory of Collapse",
                intro: "The air thickens. Your instruments read impossible altitudes. A voice that predates your crew speaks through the hull.",
                vision: "You see the sky before it was sky — solid, dark, and full. Then a crack, and light poured in from below. The ancestors rose into that light. They are still rising.",
                fragmentId: "lore_reconstruction_01",
                dangerMod: -0.05f, revealsHidden: false, minDecoded: 5);

            MakeMythic("mythic_void_gate",
                title: "The Gate That Refused the Empire",
                intro: "A structure appears on sensors — non-imperial, non-natural. Older than either. It turns toward your ship.",
                vision: "The gate shows you a cartographic lie: every imperial map you've seen was drawn to conceal, not reveal. The blank spaces are full. The empire made them blank.",
                fragmentId: "lore_imperial_veil_02",
                dangerMod: 0.10f, revealsHidden: true, minDecoded: 8);

            MakeMythic("mythic_ancestor_storm",
                title: "The Storm That Remembers",
                intro: "This storm is wrong. It moves against wind logic. It has been waiting.",
                vision: "Inside the storm: calm. Inside the calm: every navigator who crossed this cell before you, still crossing. They hand you a chart. It shows where the world ends — and what's beyond.",
                fragmentId: "lore_reconstruction_02",
                dangerMod: 0f, revealsHidden: true, minDecoded: 15);
        }

        // ── Asset builders ────────────────────────────────────────────────────

        static void MakeLore(string id, string era, string speaker,
            string body, string hint, int minDecoded, bool requiresMythic)
        {
            string path = $"{LORE_DIR}/{id}.asset";
            var frag = LoadOrCreate<LoreFragment>(path);
            var so   = new SerializedObject(frag);
            so.FindProperty("fragmentId").stringValue           = id;
            so.FindProperty("era").stringValue                  = era;
            so.FindProperty("speakerName").stringValue          = speaker;
            so.FindProperty("bodyText").stringValue             = body;
            so.FindProperty("playerHint").stringValue           = hint;
            so.FindProperty("requiredDecodedCells").intValue    = minDecoded;
            so.FindProperty("requiresMythicEvent").boolValue    = requiresMythic;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(frag);
        }

        static void MakeNPC(string assetName, FactionId faction, string npcName,
            string[] lines, int cooperativeDelta, int hostileDelta,
            string loreReward, bool allBiomes)
        {
            string encPath = $"{NPC_DIR}/{assetName}.asset";
            var enc = LoadOrCreate<NPCEncounter>(encPath);
            var so  = new SerializedObject(enc);
            so.FindProperty("encounterTitle").stringValue        = npcName;
            so.FindProperty("introText").stringValue             = lines.Length > 0 ? lines[0] : "";
            so.FindProperty("faction").enumValueIndex            = (int)faction;
            so.FindProperty("npcName").stringValue               = npcName;
            so.FindProperty("cooperativeStandingDelta").intValue = cooperativeDelta;
            so.FindProperty("hostileStandingDelta").intValue     = hostileDelta;
            so.FindProperty("loreReward").stringValue            = loreReward ?? "";

            var linesProp = so.FindProperty("dialogueLines");
            if (linesProp != null)
            {
                linesProp.arraySize = lines.Length;
                for (int i = 0; i < lines.Length; i++)
                    linesProp.GetArrayElementAtIndex(i).stringValue = lines[i];
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(enc);

            // SkyEvent wrapper
            string evtPath = $"{EVENT_DIR}/{assetName}_event.asset";
            var evt = LoadOrCreate<SkyEvent>(evtPath);
            var evtSo = new SerializedObject(evt);
            evtSo.FindProperty("eventId").stringValue                = assetName;
            evtSo.FindProperty("eventType").enumValueIndex           = (int)Skybound.Core.SkyEventType.Discovery;
            evtSo.FindProperty("baseProbability").floatValue         = 18f;
            evtSo.FindProperty("encounter").objectReferenceValue     = enc;

            var layersProp = evtSo.FindProperty("eligibleLayers");
            var allLayers  = new[] { Skybound.Core.SkyLayer.LowSky, Skybound.Core.SkyLayer.MidSky,
                                     Skybound.Core.SkyLayer.HighSky, Skybound.Core.SkyLayer.VoidSky };
            var npcLayers  = allBiomes ? allLayers : new[] { Skybound.Core.SkyLayer.LowSky, Skybound.Core.SkyLayer.MidSky };
            if (layersProp != null)
            {
                layersProp.arraySize = npcLayers.Length;
                for (int i = 0; i < npcLayers.Length; i++)
                    layersProp.GetArrayElementAtIndex(i).enumValueIndex = (int)npcLayers[i];
            }
            evtSo.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(evt);
        }

        static void MakeMythic(string assetName, string title, string intro,
            string vision, string fragmentId, float dangerMod,
            bool revealsHidden, int minDecoded)
        {
            string encPath = $"{MYTH_DIR}/{assetName}.asset";
            var enc = LoadOrCreate<MythicEvent>(encPath);
            var so  = new SerializedObject(enc);
            so.FindProperty("encounterTitle").stringValue      = title;
            so.FindProperty("introText").stringValue           = intro;
            so.FindProperty("visionText").stringValue          = vision;
            so.FindProperty("loreFragmentId").stringValue      = fragmentId;
            so.FindProperty("worldDangerModifier").floatValue  = dangerMod;
            so.FindProperty("revealsHiddenBiome").boolValue    = revealsHidden;
            so.FindProperty("minimumDecodedCells").intValue    = minDecoded;
            so.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(enc);

            string evtPath = $"{EVENT_DIR}/{assetName}_event.asset";
            var evt = LoadOrCreate<SkyEvent>(evtPath);
            var evtSo = new SerializedObject(evt);
            evtSo.FindProperty("eventId").stringValue               = assetName;
            evtSo.FindProperty("eventType").enumValueIndex          = (int)Skybound.Core.SkyEventType.Discovery;
            evtSo.FindProperty("baseProbability").floatValue        = 6f;
            evtSo.FindProperty("encounter").objectReferenceValue    = enc;

            var layersProp = evtSo.FindProperty("eligibleLayers");
            var mythLayers = new[] { Skybound.Core.SkyLayer.HighSky, Skybound.Core.SkyLayer.VoidSky };
            if (layersProp != null)
            {
                layersProp.arraySize = mythLayers.Length;
                for (int i = 0; i < mythLayers.Length; i++)
                    layersProp.GetArrayElementAtIndex(i).enumValueIndex = (int)mythLayers[i];
            }
            evtSo.ApplyModifiedPropertiesWithoutUndo();
            EditorUtility.SetDirty(evt);
        }

        static T LoadOrCreate<T>(string path) where T : ScriptableObject
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing != null) return existing;
            var asset = ScriptableObject.CreateInstance<T>();
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        static void EnsureDir(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            int last   = path.LastIndexOf('/');
            string par = path.Substring(0, last);
            string leaf = path.Substring(last + 1);
            EnsureDir(par);
            AssetDatabase.CreateFolder(par, leaf);
        }
    }
}
#endif
