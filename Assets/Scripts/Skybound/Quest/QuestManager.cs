using System.Collections.Generic;
using UnityEngine;
using Skybound.NPC;
using Skybound.Economy;
using Skybound.Narrative;

namespace Skybound.Quest
{
    /// <summary>
    /// Tracks active and completed quests. Handles choice resolution: applies
    /// faction standing shifts, coin deltas, lore unlocks, and crew narrative
    /// broadcasts. Raises events so the CommandBar and feed can react.
    /// </summary>
    public class QuestManager : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private FactionStandingManager factionStandings;
        [SerializeField] private EconomyManager         economy;
        [SerializeField] private LoreArchive            loreArchive;
        [SerializeField] private Systems.UIManager      uiManager;

        public System.Action<QuestData>              OnQuestStarted;
        public System.Action<QuestData, QuestStage> OnStageChanged;
        public System.Action<QuestData>              OnQuestCompleted;

        private readonly Dictionary<string, QuestData>  _active    = new Dictionary<string, QuestData>();
        private readonly Dictionary<string, string>     _stageMap  = new Dictionary<string, string>(); // questId → current stageId
        private readonly HashSet<string>                _completed = new HashSet<string>();
        private readonly List<QuestData>                _available = new List<QuestData>();

        [Header("Quest Pool")]
        [SerializeField] private List<QuestData> allQuests;

        // ── Public API ────────────────────────────────────────────────────────

        public void RegisterAvailableQuests(List<QuestData> quests) =>
            _available.AddRange(quests);

        /// <summary>Returns quests that can start in the given biome at ship level.</summary>
        public List<QuestData> GetTriggerable(Skybound.World.SkyBiome biome, int shipLevel)
        {
            var result = new List<QuestData>();
            var pool   = allQuests != null && allQuests.Count > 0 ? allQuests : _available;
            foreach (var q in pool)
            {
                if (_completed.Contains(q.questId)) continue;
                if (_active.ContainsKey(q.questId)) continue;
                if (q.triggerBiome != biome)         continue;
                if (q.minShipLevel > shipLevel)      continue;
                result.Add(q);
            }
            return result;
        }

        public bool HasActiveQuest(string questId) => _active.ContainsKey(questId);
        public bool IsCompleted(string questId)    => _completed.Contains(questId);

        public QuestStage CurrentStage(string questId)
        {
            if (!_active.TryGetValue(questId, out var quest)) return null;
            if (!_stageMap.TryGetValue(questId, out string sid)) return quest.FirstStage;
            return quest.GetStage(sid);
        }

        public void StartQuest(QuestData quest)
        {
            if (quest == null || _active.ContainsKey(quest.questId)) return;
            _active[quest.questId] = quest;
            var first = quest.FirstStage;
            if (first != null) _stageMap[quest.questId] = first.stageId;

            Feed($"[Quest] {quest.questTitle}: {quest.hookText}");
            OnQuestStarted?.Invoke(quest);
            if (first != null) OnStageChanged?.Invoke(quest, first);
        }

        public void MakeChoice(string questId, QuestChoice choice)
        {
            if (!_active.TryGetValue(questId, out var quest)) return;

            // Apply consequences
            if (choice.factionDelta != 0 && factionStandings != null)
                factionStandings.ShiftStanding(choice.affectedFaction, choice.factionDelta);

            if (choice.coinReward != 0 && economy != null)
            {
                if (choice.coinReward > 0) economy.AddCoins(choice.coinReward);
                else economy.TrySpend(-choice.coinReward);
            }

            if (!string.IsNullOrEmpty(choice.loreFragmentId))
                loreArchive?.TryUnlock(choice.loreFragmentId);

            if (!string.IsNullOrEmpty(choice.crewNarrativeLine))
                Feed($"[Crew] {choice.crewNarrativeLine}");

            Feed($"[Quest] {choice.outcomeText}");

            // Advance or end
            if (choice.endsQuest || string.IsNullOrEmpty(choice.nextStageId))
            {
                CompleteQuest(quest);
            }
            else
            {
                var next = quest.GetStage(choice.nextStageId);
                if (next == null) { CompleteQuest(quest); return; }
                _stageMap[questId] = next.stageId;
                OnStageChanged?.Invoke(quest, next);
                Feed($"[Quest] {next.speakerName}: \"{next.bodyText}\"");
            }
        }

        private void CompleteQuest(QuestData quest)
        {
            _active.Remove(quest.questId);
            _stageMap.Remove(quest.questId);
            _completed.Add(quest.questId);
            Feed($"[Quest] \"{quest.questTitle}\" concluded.");
            OnQuestCompleted?.Invoke(quest);
        }

        private void Feed(string msg) => uiManager?.AppendFeed(msg);
    }
}
