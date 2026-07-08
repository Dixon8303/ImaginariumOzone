using System;
using System.IO;
using UnityEngine;
using Skybound.Ship;

namespace Skybound.Save
{
    /// <summary>
    /// Reads and writes ShipSaveData as JSON to Application.persistentDataPath.
    /// Call Save() on scene exit / significant events; Load() on bootstrap.
    /// Crew is persisted by ScriptableObject asset name and reloaded via Resources.Load.
    /// Place your CrewMember assets under Resources/Crew/ for this to work.
    /// </summary>
    public class SaveManager : MonoBehaviour
    {
        private const string FileName = "skybound_save.json";

        [Header("Dependencies")]
        [SerializeField] private ShipManager ship;
        [SerializeField] private ShipCrewManager crew;

        private string SavePath => Path.Combine(Application.persistentDataPath, FileName);

        public void Save()
        {
            if (ship == null) return;
            var data = new ShipSaveData
            {
                currentLayer = ship.CurrentLayer,
                hullIntegrity01 = ship.HullIntegrity,
                shipLevel = ship.ShipLevel,
                lastSavedUtc = DateTime.UtcNow.ToString("o")
            };

            if (crew != null)
                foreach (var member in crew.Roster)
                    data.crew.Add(new CrewSaveEntry { crewAssetName = member.name });

            string json = JsonUtility.ToJson(data, prettyPrint: true);
            File.WriteAllText(SavePath, json);
            Debug.Log($"[SaveManager] Saved to {SavePath}");
        }

        public ShipSaveData Load()
        {
            if (!File.Exists(SavePath))
            {
                Debug.Log("[SaveManager] No save found, returning default.");
                return ShipSaveData.Default();
            }

            try
            {
                string json = File.ReadAllText(SavePath);
                var data = JsonUtility.FromJson<ShipSaveData>(json);
                ApplyToShip(data);
                return data;
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[SaveManager] Load failed: {ex.Message}. Returning default.");
                return ShipSaveData.Default();
            }
        }

        public void DeleteSave()
        {
            if (File.Exists(SavePath))
                File.Delete(SavePath);
        }

        private void ApplyToShip(ShipSaveData data)
        {
            if (ship == null) return;
            ship.SetLayer(data.currentLayer);
            ship.RepairHull(data.hullIntegrity01 - ship.HullIntegrity);

            if (crew == null) return;
            foreach (var entry in data.crew)
            {
                var asset = Resources.Load<Skybound.Ship.CrewMember>($"Crew/{entry.crewAssetName}");
                if (asset != null) crew.TryAddCrew(asset);
                else Debug.LogWarning($"[SaveManager] Crew asset not found: Crew/{entry.crewAssetName}");
            }
        }
    }
}
