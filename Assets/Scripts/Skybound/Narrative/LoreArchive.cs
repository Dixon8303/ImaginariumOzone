using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Skybound.Narrative
{
    /// <summary>
    /// The player's accumulating sky-history reconstruction.
    /// Fragments slot into chronological eras; when an era is complete the
    /// archive emits OnEraCompleted so the UIManager can surface a revelation.
    /// </summary>
    public class LoreArchive : MonoBehaviour
    {
        [SerializeField] private LoreFragment[] allFragments;

        public System.Action<LoreFragment> OnFragmentUnlocked;
        public System.Action<string>       OnEraCompleted;

        private readonly HashSet<string>          _unlocked = new HashSet<string>();
        private readonly Dictionary<string, int>  _eraTotal = new Dictionary<string, int>();
        private readonly Dictionary<string, int>  _eraFound = new Dictionary<string, int>();

        private void Awake()
        {
            if (allFragments == null) return;
            foreach (var f in allFragments)
            {
                if (!_eraTotal.ContainsKey(f.era)) { _eraTotal[f.era] = 0; _eraFound[f.era] = 0; }
                _eraTotal[f.era]++;
            }
        }

        public bool TryUnlock(string fragmentId)
        {
            if (_unlocked.Contains(fragmentId)) return false;

            var frag = allFragments?.FirstOrDefault(f => f.fragmentId == fragmentId);
            if (frag == null) return false;

            _unlocked.Add(fragmentId);
            _eraFound[frag.era] = _eraFound.GetValueOrDefault(frag.era, 0) + 1;

            OnFragmentUnlocked?.Invoke(frag);

            if (_eraFound[frag.era] >= _eraTotal.GetValueOrDefault(frag.era, int.MaxValue))
                OnEraCompleted?.Invoke(frag.era);

            return true;
        }

        public int UnlockedCount => _unlocked.Count;
        public int TotalCount    => allFragments?.Length ?? 0;

        public IEnumerable<LoreFragment> GetUnlocked()
            => allFragments?.Where(f => _unlocked.Contains(f.fragmentId))
               ?? System.Array.Empty<LoreFragment>();

        public float ReconstructionProgress =>
            TotalCount == 0 ? 0f : (float)UnlockedCount / TotalCount;
    }
}
