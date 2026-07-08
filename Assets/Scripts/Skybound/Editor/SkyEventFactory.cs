#if UNITY_EDITOR
using UnityEngine;
using UnityEditor;
using Skybound.Core;
using Skybound.Events;

namespace Skybound.Editor
{
    /// <summary>
    /// Generates a starter set of SkyEvent + Encounter ScriptableObject assets.
    /// Run via Tools > Skybound > Generate Sample Events.
    /// Assets are placed in Assets/Data/SkyEvents/ — safe to regenerate; existing
    /// assets with the same path are overwritten so values reset to defaults.
    /// </summary>
    public static class SkyEventFactory
    {
        private const string OutputRoot = "Assets/Data/SkyEvents";

        [MenuItem("Tools/Skybound/Generate Sample Events")]
        public static void GenerateSampleEvents()
        {
            EnsureFolder("Assets/Data");
            EnsureFolder(OutputRoot);
            EnsureFolder($"{OutputRoot}/Encounters");

            CreateCombatEvent("evt_imperial_intercept", "Imperial Interceptor",
                layer: SkyLayer.MidSky, probability: 20f, hitThreshold: 55f, enemyName: "Imperial Interceptor");

            CreateCombatEvent("evt_pirate_ambush", "Pirate Ambush",
                layer: SkyLayer.LowSky, probability: 30f, hitThreshold: 40f, enemyName: "Sky Pirate Sloop");

            CreateDiscoveryEvent("evt_derelict_freighter", "Derelict Freighter",
                layer: SkyLayer.LowSky, probability: 25f, minGold: 20, maxGold: 60, grantsArtifact: false);

            CreateDiscoveryEvent("evt_ancient_ruin", "Ancient Sky Ruin",
                layer: SkyLayer.HighSky, probability: 10f, minGold: 50, maxGold: 150,
                grantsArtifact: true, artifactName: "Navigator's Sextant");

            CreateEnvironmentalEvent("evt_aether_storm", "Aether Storm",
                layer: SkyLayer.MidSky, probability: 20f, hullDamage: 0.15f, evadeThreshold: 45f);

            CreateEnvironmentalEvent("evt_void_turbulence", "Void Turbulence",
                layer: SkyLayer.VoidSky, probability: 35f, hullDamage: 0.25f, evadeThreshold: 60f);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[SkyEventFactory] Sample events generated in Assets/Data/SkyEvents/");
        }

        private static void CreateCombatEvent(string id, string title, SkyLayer layer,
            float probability, float hitThreshold, string enemyName)
        {
            var encounter = CreateOrReplace<CombatEncounter>($"{OutputRoot}/Encounters/{id}_encounter.asset");
            SetEncounterBase(encounter, title, $"An enemy vessel moves to intercept. Engage or be boarded.");
            SetField(encounter, "baseHitThreshold", hitThreshold);
            SetField(encounter, "enemyName", enemyName);
            EditorUtility.SetDirty(encounter);

            var evt = CreateOrReplace<SkyEvent>($"{OutputRoot}/{id}.asset");
            SetEventBase(evt, id, SkyEventType.Combat, probability, new[] { layer }, encounter);
            EditorUtility.SetDirty(evt);
        }

        private static void CreateDiscoveryEvent(string id, string title, SkyLayer layer,
            float probability, int minGold, int maxGold, bool grantsArtifact, string artifactName = "")
        {
            var encounter = CreateOrReplace<DiscoveryEncounter>($"{OutputRoot}/Encounters/{id}_encounter.asset");
            SetEncounterBase(encounter, title, "A derelict structure drifts into view. Investigate?");
            SetField(encounter, "minLootGold", minGold);
            SetField(encounter, "maxLootGold", maxGold);
            SetField(encounter, "grantsArtifact", grantsArtifact);
            if (grantsArtifact) SetField(encounter, "artifactName", artifactName);
            EditorUtility.SetDirty(encounter);

            var evt = CreateOrReplace<SkyEvent>($"{OutputRoot}/{id}.asset");
            SetEventBase(evt, id, SkyEventType.Discovery, probability, new[] { layer }, encounter);
            EditorUtility.SetDirty(evt);
        }

        private static void CreateEnvironmentalEvent(string id, string title, SkyLayer layer,
            float probability, float hullDamage, float evadeThreshold)
        {
            var encounter = CreateOrReplace<EnvironmentalEncounter>($"{OutputRoot}/Encounters/{id}_encounter.asset");
            SetEncounterBase(encounter, title, "A violent sky phenomenon closes in. Brace the hull.");
            SetField(encounter, "hazardName", title);
            SetField(encounter, "hullDamage01", hullDamage);
            SetField(encounter, "evadeThreshold", evadeThreshold);
            EditorUtility.SetDirty(encounter);

            var evt = CreateOrReplace<SkyEvent>($"{OutputRoot}/{id}.asset");
            SetEventBase(evt, id, SkyEventType.Environmental, probability, new[] { layer }, encounter);
            EditorUtility.SetDirty(evt);
        }

        private static void SetEncounterBase(EncounterData enc, string title, string intro)
        {
            var so = new SerializedObject(enc);
            so.FindProperty("encounterTitle").stringValue = title;
            so.FindProperty("introText").stringValue = intro;
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void SetEventBase(SkyEvent evt, string id, SkyEventType type,
            float probability, SkyLayer[] layers, EncounterData encounter)
        {
            var so = new SerializedObject(evt);
            so.FindProperty("eventId").stringValue = id;
            so.FindProperty("eventType").enumValueIndex = (int)type;
            so.FindProperty("baseProbability").floatValue = probability;
            so.FindProperty("encounter").objectReferenceValue = encounter;
            var layersProp = so.FindProperty("eligibleLayers");
            layersProp.arraySize = layers.Length;
            for (int i = 0; i < layers.Length; i++)
                layersProp.GetArrayElementAtIndex(i).enumValueIndex = (int)layers[i];
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        private static void SetField(Object target, string fieldName, object value)
        {
            var so = new SerializedObject(target);
            var prop = so.FindProperty(fieldName);
            if (prop == null) return;
            switch (value)
            {
                case float f: prop.floatValue = f; break;
                case int i: prop.intValue = i; break;
                case bool b: prop.boolValue = b; break;
                case string s: prop.stringValue = s; break;
            }
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        private static T CreateOrReplace<T>(string path) where T : ScriptableObject
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing != null) return existing;
            var asset = ScriptableObject.CreateInstance<T>();
            AssetDatabase.CreateAsset(asset, path);
            return asset;
        }

        private static void EnsureFolder(string path)
        {
            if (!AssetDatabase.IsValidFolder(path))
            {
                int last = path.LastIndexOf('/');
                AssetDatabase.CreateFolder(path.Substring(0, last), path.Substring(last + 1));
            }
        }
    }
}
#endif
