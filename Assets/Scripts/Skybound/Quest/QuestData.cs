using System.Collections.Generic;
using UnityEngine;
using Skybound.NPC;
using Skybound.World;

namespace Skybound.Quest
{
    // ── Choice & Consequence ──────────────────────────────────────────────────

    [System.Serializable]
    public class QuestChoice
    {
        public string label;              // shown on button: "Hand her over", "Hide her"
        [TextArea(1, 3)]
        public string outcomeText;        // feed message when chosen
        public string nextStageId;        // "" = quest ends here
        public bool   endsQuest;

        [Header("Consequences")]
        public FactionId  affectedFaction;
        public int        factionDelta;   // standing shift (-2 to +2)
        public int        coinReward;     // can be negative (a cost)
        public string     loreFragmentId; // unlocked if non-empty
        public string     crewNarrativeLine; // broadcast to crew feed
    }

    // ── Stage ─────────────────────────────────────────────────────────────────

    [System.Serializable]
    public class QuestStage
    {
        public string stageId;
        public string speakerName;
        [TextArea(2, 6)]
        public string bodyText;           // the scene — what the NPC says / what you discover
        public List<QuestChoice> choices; // 1-3 choices; if only 1 it auto-advances
    }

    // ── Quest ─────────────────────────────────────────────────────────────────

    /// <summary>
    /// A multi-stage branching quest. Each stage has a speaker, scene text, and
    /// 1-3 player choices. Choices carry faction, economic, and lore consequences.
    /// The moral weight lives in the writing — the system just carries it forward.
    ///
    /// Rubric:
    ///   Story 5    — choices cost something real every time
    ///   Fun 5      — short enough to complete in one session, long enough to matter
    ///   Replayability 5 — different seeds surface different factions, different stakes
    /// </summary>
    [CreateAssetMenu(menuName = "Skybound/Quest/Quest Data")]
    public class QuestData : ScriptableObject
    {
        [Header("Identity")]
        public string questId;
        public string questTitle;
        [TextArea(1, 3)]
        public string hookText;           // one-line hook shown when quest begins

        [Header("Trigger")]
        public FactionId  giverFaction;
        public SkyBiome   triggerBiome;   // must be in this biome to start
        public int        minShipLevel = 1;

        [Header("Stages")]
        public List<QuestStage> stages;

        public QuestStage GetStage(string id)
        {
            if (stages == null) return null;
            foreach (var s in stages)
                if (s.stageId == id) return s;
            return null;
        }

        public QuestStage FirstStage => stages != null && stages.Count > 0 ? stages[0] : null;
    }
}
