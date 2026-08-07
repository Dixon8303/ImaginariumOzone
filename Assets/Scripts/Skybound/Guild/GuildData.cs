using System.Collections.Generic;
using UnityEngine;

namespace Skybound.Guild
{
    public enum GuildTier { Scout, Pathfinder, Cartographer, SkyMaster }

    /// <summary>
    /// Serialisable snapshot of the player's guild rank and shared discoveries.
    /// Written to the save slot and read back on load so guild progress persists.
    /// </summary>
    [System.Serializable]
    public class GuildData
    {
        public string              guildName      = "Unnamed Guild";
        public GuildTier           tier           = GuildTier.Scout;
        public int                 reputation     = 0;   // accumulated reputation points
        public List<string>        sharedCells    = new List<string>(); // "x,y" keys
        public List<string>        contributorLog = new List<string>();

        // Reputation thresholds per tier
        public static int ThresholdFor(GuildTier t) => t switch
        {
            GuildTier.Scout        =>    0,
            GuildTier.Pathfinder   =>  150,
            GuildTier.Cartographer =>  500,
            GuildTier.SkyMaster    => 1200,
            _                      =>    0
        };

        public GuildTier CurrentTier()
        {
            if (reputation >= ThresholdFor(GuildTier.SkyMaster))   return GuildTier.SkyMaster;
            if (reputation >= ThresholdFor(GuildTier.Cartographer)) return GuildTier.Cartographer;
            if (reputation >= ThresholdFor(GuildTier.Pathfinder))   return GuildTier.Pathfinder;
            return GuildTier.Scout;
        }
    }
}
