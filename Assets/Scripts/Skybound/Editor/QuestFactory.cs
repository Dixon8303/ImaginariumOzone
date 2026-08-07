#if UNITY_EDITOR
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using Skybound.Quest;
using Skybound.NPC;
using Skybound.World;

namespace Skybound.Editor
{
    /// <summary>
    /// Generates the three sample quests.
    /// Run: Tools > Skybound > Generate Quests
    /// </summary>
    public static class QuestFactory
    {
        private const string DIR = "Assets/Data/Quests";

        [MenuItem("Tools/Skybound/Generate Quests")]
        public static void Generate()
        {
            EnsureDir("Assets/Data");
            EnsureDir(DIR);

            CreateCartographersDebt();
            CreateWhatTheCorridorErased();
            CreateTheCrewMembersSky();

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("[QuestFactory] Three quests generated in Assets/Data/Quests/");
        }

        // ── Quest 1: The Cartographer's Debt ──────────────────────────────────
        // Witcher-style: a person you want to help is also holding something
        // the empire wants. You decide who pays.

        static void CreateCartographersDebt()
        {
            var q = LoadOrCreate<QuestData>($"{DIR}/quest_cartographers_debt.asset");
            var so = new SerializedObject(q);
            so.FindProperty("questId").stringValue     = "quest_cartographers_debt";
            so.FindProperty("questTitle").stringValue  = "The Cartographer's Debt";
            so.FindProperty("hookText").stringValue    = "A Kemi archivist flags your ship. She has something the empire wants — and a reason you shouldn't give it to them.";
            so.FindProperty("giverFaction").enumValueIndex  = (int)FactionId.KemiNavigators;
            so.FindProperty("triggerBiome").enumValueIndex  = (int)SkyBiome.AncestorFields;
            so.FindProperty("minShipLevel").intValue        = 1;
            so.ApplyModifiedPropertiesWithoutUndo();

            var stages = new List<QuestStage>
            {
                new QuestStage
                {
                    stageId = "s1",
                    speakerName = "Archivist Yemi",
                    bodyText = "I mapped a corridor route three years ago. The empire has it now — or thinks they do. I kept a copy. If they find me with it, they'll use it to raze the Amara freeholds to the east.\n\nI need you to carry it. You're not on their list.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Take the map",
                            outcomeText = "You take the route data. Yemi's relief is visible.",
                            nextStageId = "s2_carry",
                            factionDelta = 1,
                            affectedFaction = FactionId.KemiNavigators,
                            crewNarrativeLine = "The crew understands what's at stake. Something shifts in the hold."
                        },
                        new QuestChoice
                        {
                            label = "Turn her in",
                            outcomeText = "You contact the imperial beacon. Yemi sees it in your face before you finish.",
                            nextStageId = "s2_betray",
                            factionDelta = 1,
                            affectedFaction = FactionId.ImperialSyndicate,
                            crewNarrativeLine = "One of your crew goes quiet. Doesn't look at you at dinner."
                        },
                        new QuestChoice
                        {
                            label = "Walk away",
                            outcomeText = "You fly on. The archivist's ship falls behind your wake.",
                            endsQuest = true,
                            factionDelta = -1,
                            affectedFaction = FactionId.KemiNavigators
                        }
                    }
                },
                new QuestStage
                {
                    stageId = "s2_carry",
                    speakerName = "Imperial Checkpoint",
                    bodyText = "An imperial patrol hails you. Routine inspection. They're looking for something specific — you can feel it in the way the officer watches your hands.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Bluff through",
                            outcomeText = "You hold their gaze and lie well. The patrol moves on.",
                            endsQuest = true,
                            factionDelta = -1,
                            affectedFaction = FactionId.ImperialSyndicate,
                            coinReward = 0,
                            loreFragmentId = "lore_imperial_veil_01",
                            crewNarrativeLine = "Nobody breathes until the patrol is out of sensor range."
                        },
                        new QuestChoice
                        {
                            label = "Dump the map",
                            outcomeText = "You jettison the data before they board. Clean, but the route is gone forever.",
                            endsQuest = true,
                            factionDelta = -1,
                            affectedFaction = FactionId.KemiNavigators,
                            crewNarrativeLine = "The crew watches the data packet tumble into cloud cover. Nobody speaks."
                        }
                    }
                },
                new QuestStage
                {
                    stageId = "s2_betray",
                    speakerName = "Imperial Officer Rein",
                    bodyText = "Good work. The empire rewards cooperation.\n\nThe archivist was carrying more than a route. We found correspondence — names of Amara operatives. We'll be visiting them next.\n\nHere's your payment.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Take the coin",
                            outcomeText = "You take the reward. You don't ask what happens next.",
                            endsQuest = true,
                            coinReward = 80,
                            factionDelta = -2,
                            affectedFaction = FactionId.AmaraFreeholds,
                            crewNarrativeLine = "One crew member requests transfer off your ship at the next dock."
                        },
                        new QuestChoice
                        {
                            label = "Warn the Amara",
                            outcomeText = "You burn the imperial reward and send a signal east. It might be enough.",
                            endsQuest = true,
                            coinReward = -20,
                            factionDelta = 2,
                            affectedFaction = FactionId.AmaraFreeholds,
                            crewNarrativeLine = "Your crew doesn't ask questions. They help encode the signal.",
                            loreFragmentId = "lore_reconstruction_01"
                        }
                    }
                }
            };

            WriteStages(q, stages);
            EditorUtility.SetDirty(q);
        }

        // ── Quest 2: What the Corridor Erased ─────────────────────────────────
        // Environmental mystery — the absent thing is the story.

        static void CreateWhatTheCorridorErased()
        {
            var q = LoadOrCreate<QuestData>($"{DIR}/quest_corridor_erased.asset");
            var so = new SerializedObject(q);
            so.FindProperty("questId").stringValue     = "quest_corridor_erased";
            so.FindProperty("questTitle").stringValue  = "What the Corridor Erased";
            so.FindProperty("hookText").stringValue    = "An old imperial map shows an island that isn't there. Somebody made it disappear. The question is why.";
            so.FindProperty("giverFaction").enumValueIndex  = (int)FactionId.AmaraFreeholds;
            so.FindProperty("triggerBiome").enumValueIndex  = (int)SkyBiome.ImperialCorridor;
            so.FindProperty("minShipLevel").intValue        = 2;
            so.ApplyModifiedPropertiesWithoutUndo();

            var stages = new List<QuestStage>
            {
                new QuestStage
                {
                    stageId = "s1",
                    speakerName = "Resistance Courier",
                    bodyText = "This map is forty years old. See that grid reference? It marks an island — population 2,000, Kemi-aligned. Now look at the new imperial charts.\n\nNothing. Not erased — *never there*. They rewrote the coordinates entirely.\n\nSomebody who knew those people wants you to know they existed.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Investigate the coordinates",
                            outcomeText = "You set course. The grid reference is inside imperial patrol range.",
                            nextStageId = "s2_investigate"
                        },
                        new QuestChoice
                        {
                            label = "Leave it buried",
                            outcomeText = "Some histories stay buried because opening them costs more than the knowing.",
                            endsQuest = true,
                            factionDelta = -1,
                            affectedFaction = FactionId.AmaraFreeholds
                        }
                    }
                },
                new QuestStage
                {
                    stageId = "s2_investigate",
                    speakerName = "Sky Record — Recovered",
                    bodyText = "You find it. Not an island — ruins of one, floating in debris field, marked with imperial suppression beacons.\n\nAmong the wreckage: a Kemi cartography station. Still transmitting. It has been transmitting for forty years, to no one.\n\nThe signal contains a complete atlas of the pre-imperial sky.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Download the atlas",
                            outcomeText = "You take the signal. Forty years of hidden sky, yours now.",
                            endsQuest = true,
                            factionDelta = 2,
                            affectedFaction = FactionId.KemiNavigators,
                            coinReward = 0,
                            loreFragmentId = "lore_unmooring_02",
                            crewNarrativeLine = "The historian in your crew is crying and pretending she isn't."
                        },
                        new QuestChoice
                        {
                            label = "Broadcast it to all channels",
                            outcomeText = "You open the signal wide. Everyone hears it. The empire will know within the hour.",
                            endsQuest = true,
                            factionDelta = -2,
                            affectedFaction = FactionId.ImperialSyndicate,
                            loreFragmentId = "lore_unmooring_02",
                            crewNarrativeLine = "Someone on the crew whispers: 'They'll come for us now.' Somebody else: 'Good.'"
                        }
                    }
                }
            };

            WriteStages(q, stages);
            EditorUtility.SetDirty(q);
        }

        // ── Quest 3: The Crew Member's Sky ────────────────────────────────────
        // Vox Machina style: small, personal, the stakes are one person's history.

        static void CreateTheCrewMembersSky()
        {
            var q = LoadOrCreate<QuestData>($"{DIR}/quest_crew_sky.asset");
            var so = new SerializedObject(q);
            so.FindProperty("questId").stringValue     = "quest_crew_sky";
            so.FindProperty("questTitle").stringValue  = "The Crew Member's Sky";
            so.FindProperty("hookText").stringValue    = "Femi goes quiet when you enter the StormRift. You've never seen her quiet.";
            so.FindProperty("giverFaction").enumValueIndex  = (int)FactionId.AmaraFreeholds;
            so.FindProperty("triggerBiome").enumValueIndex  = (int)SkyBiome.StormRift;
            so.FindProperty("minShipLevel").intValue        = 1;
            so.ApplyModifiedPropertiesWithoutUndo();

            var stages = new List<QuestStage>
            {
                new QuestStage
                {
                    stageId = "s1",
                    speakerName = "Femi",
                    bodyText = "I grew up in a StormRift settlement. Before the empire routed the freeholds through here and turned it into a warzone.\n\nMy mother's ship went down in this exact band of sky. I was twelve.\n\nI've been looking for the wreck for six years. I think I know where it is.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "\"Take us there.\"",
                            outcomeText = "You change course. No questions. The crew follows without being asked.",
                            nextStageId = "s2_search",
                            crewNarrativeLine = "The whole crew goes quiet, as if noise would be disrespectful."
                        },
                        new QuestChoice
                        {
                            label = "\"We can't right now.\"",
                            outcomeText = "Femi nods. She doesn't push. But she doesn't look at you the same way after.",
                            endsQuest = true,
                            factionDelta = -1,
                            affectedFaction = FactionId.AmaraFreeholds,
                            crewNarrativeLine = "Femi returns to her post. She works fine. She's just somewhere else now."
                        }
                    }
                },
                new QuestStage
                {
                    stageId = "s2_search",
                    speakerName = "Femi",
                    bodyText = "There.\n\nShe's right. You can see the hull markings from here — a freehold scout ship, pinned in a static-field pocket. Preserved. Wrong.\n\nFemi is already pulling on an EVA harness. She's going in alone if you let her.",
                    choices = new List<QuestChoice>
                    {
                        new QuestChoice
                        {
                            label = "Go with her",
                            outcomeText = "You suit up without saying anything. She looks at you once — that's enough.",
                            endsQuest = true,
                            factionDelta = 1,
                            affectedFaction = FactionId.AmaraFreeholds,
                            loreFragmentId = "lore_reconstruction_01",
                            crewNarrativeLine = "When you come back aboard, Femi's carrying a small navigation stone. She wears it from then on.",
                            coinReward = 0
                        },
                        new QuestChoice
                        {
                            label = "Let her go alone",
                            outcomeText = "You hold the ship steady while she's inside. It's the only thing she asks of you.",
                            endsQuest = true,
                            crewNarrativeLine = "Femi comes back an hour later. Doesn't say what she found. You don't ask.",
                            factionDelta = 1,
                            affectedFaction = FactionId.AmaraFreeholds
                        }
                    }
                }
            };

            WriteStages(q, stages);
            EditorUtility.SetDirty(q);
        }

        // ── Helpers ───────────────────────────────────────────────────────────

        static void WriteStages(QuestData q, List<QuestStage> stages)
        {
            var so        = new SerializedObject(q);
            var stagesProp = so.FindProperty("stages");
            stagesProp.arraySize = stages.Count;

            for (int i = 0; i < stages.Count; i++)
            {
                var stage = stages[i];
                var sp    = stagesProp.GetArrayElementAtIndex(i);
                sp.FindPropertyRelative("stageId").stringValue     = stage.stageId;
                sp.FindPropertyRelative("speakerName").stringValue = stage.speakerName;
                sp.FindPropertyRelative("bodyText").stringValue    = stage.bodyText;

                var choicesProp = sp.FindPropertyRelative("choices");
                choicesProp.arraySize = stage.choices?.Count ?? 0;
                for (int j = 0; j < (stage.choices?.Count ?? 0); j++)
                {
                    var c  = stage.choices[j];
                    var cp = choicesProp.GetArrayElementAtIndex(j);
                    cp.FindPropertyRelative("label").stringValue              = c.label;
                    cp.FindPropertyRelative("outcomeText").stringValue        = c.outcomeText;
                    cp.FindPropertyRelative("nextStageId").stringValue        = c.nextStageId ?? "";
                    cp.FindPropertyRelative("endsQuest").boolValue            = c.endsQuest;
                    cp.FindPropertyRelative("affectedFaction").enumValueIndex = (int)c.affectedFaction;
                    cp.FindPropertyRelative("factionDelta").intValue          = c.factionDelta;
                    cp.FindPropertyRelative("coinReward").intValue            = c.coinReward;
                    cp.FindPropertyRelative("loreFragmentId").stringValue     = c.loreFragmentId ?? "";
                    cp.FindPropertyRelative("crewNarrativeLine").stringValue  = c.crewNarrativeLine ?? "";
                }
            }
            so.ApplyModifiedPropertiesWithoutUndo();
        }

        static T LoadOrCreate<T>(string path) where T : ScriptableObject
        {
            var e = AssetDatabase.LoadAssetAtPath<T>(path);
            if (e != null) return e;
            var a = ScriptableObject.CreateInstance<T>();
            AssetDatabase.CreateAsset(a, path);
            return a;
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
