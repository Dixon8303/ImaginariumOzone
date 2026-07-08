namespace Skybound.Core
{
    /// <summary>
    /// Contract the GameDirector and encounters query for ship + crew data.
    /// Decouples event logic from the concrete ShipManager / ShipCrewManager, so the
    /// multi-slot crew system can evolve independently of the event pipeline.
    /// </summary>
    public interface IShipManager
    {
        /// <summary>Current immutable snapshot used for event validation and weighting.</summary>
        ShipState GetState();

        /// <summary>Current biome/layer the ship occupies.</summary>
        SkyLayer CurrentLayer { get; }

        /// <summary>
        /// Summed crew bonus for a perk channel. Implementations iterate the active
        /// crew list and stack matching PerkTypes (e.g. dual-slot gunner accumulation).
        /// </summary>
        float GetCrewBonus(PerkType perk);
    }
}
