using System.Collections.Generic;
using UnityEngine;

namespace Skybound.NPC
{
    /// <summary>
    /// Selects the correct dialogue line for a faction NPC given current standing
    /// and any active lore fragments. Keeps a seen-line registry so the same line
    /// isn't repeated back-to-back within a session.
    /// </summary>
    public class NPCDialogueEngine : MonoBehaviour
    {
        [SerializeField] private FactionStandingManager standingManager;

        private readonly Dictionary<FactionId, Queue<string>> _seenLines
            = new Dictionary<FactionId, Queue<string>>();

        private const int HISTORY_DEPTH = 3;

        public string GetLine(FactionId faction, string[] pool = null)
        {
            var standing = standingManager != null
                ? standingManager.GetStanding(faction)
                : FactionStanding.Neutral;

            string preferred = FactionProfiles.GetGreeting(faction, standing);

            if (pool != null && pool.Length > 0)
            {
                string candidate = PickFresh(faction, pool);
                if (candidate != null) return candidate;
            }

            return preferred;
        }

        private string PickFresh(FactionId faction, string[] pool)
        {
            if (!_seenLines.ContainsKey(faction))
                _seenLines[faction] = new Queue<string>();

            var seen = _seenLines[faction];
            foreach (var line in Shuffle(pool))
            {
                if (!seen.Contains(line))
                {
                    seen.Enqueue(line);
                    if (seen.Count > HISTORY_DEPTH) seen.Dequeue();
                    return line;
                }
            }
            return pool[Random.Range(0, pool.Length)];
        }

        private static string[] Shuffle(string[] arr)
        {
            var copy = (string[])arr.Clone();
            for (int i = copy.Length - 1; i > 0; i--)
            {
                int j   = Random.Range(0, i + 1);
                (copy[i], copy[j]) = (copy[j], copy[i]);
            }
            return copy;
        }
    }
}
