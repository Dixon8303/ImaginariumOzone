using System;
using System.Collections.Generic;
using Skybound.Core;

namespace Skybound.Save
{
    [Serializable]
    public class CrewSaveEntry
    {
        public string crewAssetName;  // ScriptableObject name, used to reload via Resources
    }

    [Serializable]
    public class ShipSaveData
    {
        public int schemaVersion = 1;
        public SkyLayer currentLayer;
        public float hullIntegrity01;
        public int shipLevel;
        public int gold;
        public List<CrewSaveEntry> crew = new List<CrewSaveEntry>();
        public string lastSavedUtc;

        public static ShipSaveData Default() => new ShipSaveData
        {
            currentLayer = SkyLayer.LowSky,
            hullIntegrity01 = 1f,
            shipLevel = 1,
            gold = 0,
            lastSavedUtc = DateTime.UtcNow.ToString("o")
        };
    }
}
