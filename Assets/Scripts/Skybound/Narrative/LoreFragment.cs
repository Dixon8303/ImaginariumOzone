using UnityEngine;

namespace Skybound.Narrative
{
    /// <summary>
    /// One recoverable piece of sky history. Fragments are earned via Decode,
    /// NPC dialogue, or Mythic events, and slot into the LoreArchive's
    /// reconstruction timeline.
    /// </summary>
    [CreateAssetMenu(menuName = "Skybound/Narrative/Lore Fragment")]
    public class LoreFragment : ScriptableObject
    {
        [Header("Identity")]
        public string fragmentId;
        public string era;           // e.g. "Age of Unmooring", "Imperial Veil"
        public string speakerName;   // ancestor, oracle, or NPC who reveals this

        [Header("Content")]
        [TextArea(3, 8)]
        public string bodyText;
        [TextArea(1, 3)]
        public string playerHint;    // gameplay hint hidden inside the lore

        [Header("Unlock Condition")]
        public int    requiredDecodedCells;   // how many decoded cells needed before this unlocks
        public bool   requiresMythicEvent;    // must be revealed through a MythicEvent
    }
}
