using UnityEngine;
using Skybound.Core;

namespace Skybound.Ship
{
    /// <summary>
    /// Production IShipManager. Owns ship-level state and delegates crew queries to
    /// ShipCrewManager. Wire both components onto the same GameObject in the scene.
    /// </summary>
    [RequireComponent(typeof(ShipCrewManager))]
    public class ShipManager : MonoBehaviour, IShipManager
    {
        [Header("Ship State")]
        [SerializeField] private SkyLayer currentLayer = SkyLayer.LowSky;
        [SerializeField, Range(0f, 1f)] private float hullIntegrity01 = 1f;
        [SerializeField] private int shipLevel = 1;

        private ShipCrewManager _crew;
        private bool _inCombat;

        public SkyLayer CurrentLayer => currentLayer;

        private void Awake()
        {
            _crew = GetComponent<ShipCrewManager>();
        }

        public ShipState GetState()
            => new ShipState(currentLayer, hullIntegrity01, _crew.GetCrewCount(), shipLevel, _inCombat);

        public float GetCrewBonus(PerkType perk)
            => _crew.GetTotalBonus(perk);

        public void SetLayer(SkyLayer layer) => currentLayer = layer;

        public void ApplyHullDamage(float amount)
        {
            hullIntegrity01 = Mathf.Clamp01(hullIntegrity01 - amount);
        }

        public void RepairHull(float amount)
        {
            hullIntegrity01 = Mathf.Clamp01(hullIntegrity01 + amount);
        }

        public void SetCombat(bool inCombat) => _inCombat = inCombat;

        public float HullIntegrity => hullIntegrity01;
        public int ShipLevel => shipLevel;

        public void AdvanceShipLevel() => shipLevel++;
    }
}
