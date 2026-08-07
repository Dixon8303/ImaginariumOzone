using UnityEngine;
using Skybound.Discovery;
using Skybound.World;

namespace Skybound.Guild
{
    /// <summary>
    /// Manages the player's guild membership and the shared discovery ledger.
    /// Every cell that reaches DiscoveryTier.Decoded is contributed to the
    /// guild's shared map; the guild rewards reputation per unique contribution.
    /// Tier-up events are surfaced via OnTierAdvanced.
    /// </summary>
    public class GuildManager : MonoBehaviour
    {
        [SerializeField] private DiscoveryAtlas    atlas;
        [SerializeField] private SkyWorldManager   worldManager;
        [SerializeField] private Systems.UIManager uiManager;

        [Header("Guild Config")]
        [SerializeField] private string defaultGuildName = "Kemi Cartographers' Alliance";
        [SerializeField] private int    reputationPerCell = 10;

        public System.Action<GuildTier>  OnTierAdvanced;
        public System.Action<GuildData>  OnGuildUpdated;

        private GuildData _guild;
        public GuildData Guild => _guild;

        private void Awake()
        {
            _guild = new GuildData { guildName = defaultGuildName };
        }

        private void OnEnable()
        {
            if (atlas != null) atlas.OnEntryUpgraded += HandleEntryUpgraded;
        }

        private void OnDisable()
        {
            if (atlas != null) atlas.OnEntryUpgraded -= HandleEntryUpgraded;
        }

        private void HandleEntryUpgraded(Discovery.AtlasEntry entry)
        {
            if (entry.Tier != DiscoveryTier.Decoded) return;

            var    pos = entry.GridPos;
            string key = $"{pos.x},{pos.y}";
            if (_guild.sharedCells.Contains(key)) return;

            _guild.sharedCells.Add(key);
            _guild.contributorLog.Add($"Decoded ({pos.x},{pos.y}) on {System.DateTime.UtcNow:yyyy-MM-dd}");

            GuildTier before = _guild.tier;
            _guild.reputation += reputationPerCell;
            _guild.tier        = _guild.CurrentTier();

            uiManager?.AppendFeed($"[Guild] Decoded cell shared with {_guild.guildName}. +{reputationPerCell} rep ({_guild.reputation} total).");

            if (_guild.tier != before)
            {
                uiManager?.AppendFeed($"[Guild] Tier advanced: {_guild.tier}!");
                OnTierAdvanced?.Invoke(_guild.tier);
            }

            OnGuildUpdated?.Invoke(_guild);
        }

        public void LoadFromData(GuildData saved)
        {
            _guild = saved ?? new GuildData { guildName = defaultGuildName };
        }

        public GuildData Snapshot() => _guild;
    }
}
