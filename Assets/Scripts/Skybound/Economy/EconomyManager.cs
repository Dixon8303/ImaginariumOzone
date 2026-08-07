using UnityEngine;

namespace Skybound.Economy
{
    /// <summary>
    /// Tracks the player's sky-currency (Aether Coins) and manages buy/sell
    /// transactions. Prices are biome-weighted: TradeWinds gives best rates,
    /// ImperialCorridor levies a tariff, VoidAnomaly has no trade at all.
    /// </summary>
    public class EconomyManager : MonoBehaviour
    {
        [SerializeField] private int startingCoins = 100;

        public System.Action<int> OnCoinsChanged;

        private int _coins;
        public int Coins => _coins;

        private void Awake() { _coins = startingCoins; }

        public bool TrySpend(int amount)
        {
            if (_coins < amount) return false;
            _coins -= amount;
            OnCoinsChanged?.Invoke(_coins);
            return true;
        }

        public void AddCoins(int amount)
        {
            _coins += amount;
            OnCoinsChanged?.Invoke(_coins);
        }

        public int PriceWithBiomeTariff(int basePrice, Skybound.World.SkyBiome biome)
        {
            float multiplier = biome switch
            {
                Skybound.World.SkyBiome.TradeWinds      => 0.85f,  // trade hub discount
                Skybound.World.SkyBiome.ImperialCorridor=> 1.40f,  // imperial tariff
                Skybound.World.SkyBiome.VoidAnomaly     => 0f,     // no trade
                _                                       => 1.00f
            };
            return Mathf.RoundToInt(basePrice * multiplier);
        }
    }
}
