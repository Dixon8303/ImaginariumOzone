using UnityEngine;
using TMPro;
using Skybound.Economy;
using Skybound.Guild;
using Skybound.NPC;

namespace Skybound.UI
{
    /// <summary>
    /// Top-of-screen status bar. Displays Aether Coins, Guild tier, and the
    /// player's standing with every active faction in a compact strip.
    /// Refreshes whenever any tracked value changes.
    /// </summary>
    public class StatusBarController : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private EconomyManager       economy;
        [SerializeField] private GuildManager         guild;
        [SerializeField] private FactionStandingManager factionStandings;

        [Header("Labels")]
        [SerializeField] private TextMeshProUGUI coinsLabel;
        [SerializeField] private TextMeshProUGUI guildLabel;
        [SerializeField] private TextMeshProUGUI factionLabel;

        private void OnEnable()
        {
            if (economy  != null) economy.OnCoinsChanged          += _ => RefreshCoins();
            if (guild    != null) guild.OnGuildUpdated             += _ => RefreshGuild();
            if (factionStandings != null)
                factionStandings.OnStandingChanged += (_, __) => RefreshFactions();
        }

        private void OnDisable()
        {
            if (economy  != null) economy.OnCoinsChanged          -= _ => RefreshCoins();
            if (guild    != null) guild.OnGuildUpdated             -= _ => RefreshGuild();
            if (factionStandings != null)
                factionStandings.OnStandingChanged -= (_, __) => RefreshFactions();
        }

        private void Start()
        {
            RefreshAll();
        }

        private void RefreshAll()
        {
            RefreshCoins();
            RefreshGuild();
            RefreshFactions();
        }

        private void RefreshCoins()
        {
            if (coinsLabel == null || economy == null) return;
            coinsLabel.text = $"◈ {economy.Coins}";
        }

        private void RefreshGuild()
        {
            if (guildLabel == null || guild == null) return;
            var g = guild.Guild;
            guildLabel.text = g != null
                ? $"Guild: {g.tier}  ·  {g.reputation} rep"
                : "Guild: —";
        }

        private void RefreshFactions()
        {
            if (factionLabel == null || factionStandings == null) return;

            var sb = new System.Text.StringBuilder();
            foreach (FactionId f in System.Enum.GetValues(typeof(FactionId)))
            {
                var standing = factionStandings.GetStanding(f);
                string icon  = StandingIcon(standing);
                sb.Append($"{ShortName(f)}{icon}  ");
            }
            factionLabel.text = sb.ToString().TrimEnd();
        }

        private static string StandingIcon(FactionStanding s) => s switch
        {
            FactionStanding.Allied   => "★",
            FactionStanding.Friendly => "▲",
            FactionStanding.Neutral  => "●",
            FactionStanding.Wary     => "▼",
            FactionStanding.Hostile  => "✕",
            _                        => "●"
        };

        private static string ShortName(FactionId f) => f switch
        {
            FactionId.OyaCoalition      => "OYA",
            FactionId.KemiNavigators    => "KEM",
            FactionId.AmaraFreeholds    => "AMR",
            FactionId.ImperialSyndicate => "IMP",
            FactionId.VoidWalkers       => "VWK",
            _                           => "???"
        };
    }
}
