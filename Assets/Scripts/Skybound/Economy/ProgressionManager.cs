using UnityEngine;
using Skybound.Ship;

namespace Skybound.Economy
{
    /// <summary>
    /// Ship upgrade shop. Spending Aether Coins here raises ShipLevel
    /// (unlocking new sky layers) and permanently increases hull capacity.
    /// Upgrade costs scale with current ShipLevel so later tiers require
    /// more exploration-derived income.
    /// </summary>
    public class ProgressionManager : MonoBehaviour
    {
        [SerializeField] private ShipManager    ship;
        [SerializeField] private EconomyManager economy;

        [Header("Upgrade Costs (base × level)")]
        [SerializeField] private int hullUpgradeCost  = 50;
        [SerializeField] private int levelUpgradeCost = 120;

        public System.Action<string> OnUpgradeLog;

        public bool TryUpgradeHull()
        {
            if (ship == null || economy == null) return false;
            int cost = hullUpgradeCost * ship.ShipLevel;
            if (!economy.TrySpend(cost))
            {
                OnUpgradeLog?.Invoke($"[Upgrade] Need {cost} coins. You have {economy.Coins}.");
                return false;
            }
            ship.RepairHull(0.25f);
            OnUpgradeLog?.Invoke($"[Upgrade] Hull reinforced (+25%). Spent {cost} coins.");
            return true;
        }

        public bool TryUpgradeLevel()
        {
            if (ship == null || economy == null) return false;
            int cost = levelUpgradeCost * ship.ShipLevel;
            if (!economy.TrySpend(cost))
            {
                OnUpgradeLog?.Invoke($"[Upgrade] Need {cost} coins for tier advance. Have {economy.Coins}.");
                return false;
            }
            ship.AdvanceShipLevel();
            OnUpgradeLog?.Invoke($"[Upgrade] Ship tier advanced to {ship.ShipLevel}. New sky layers unlocked.");
            return true;
        }
    }
}
