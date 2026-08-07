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
        private string SlotPath(int slot) =>
            Path.Combine(Application.persistentDataPath, $"skybound_save_slot{slot}.json");

        // --- Slot-based API (used by SaveLoadPanel) ---

        public void Save(int slot)
        {
            if (ship == null) return;
            var data = BuildSaveData();
            File.WriteAllText(SlotPath(slot), JsonUtility.ToJson(data, prettyPrint: true));
            Debug.Log($"[SaveManager] Slot {slot} saved.");
        }

        public void Load(int slot)
        {
            string path = SlotPath(slot);
            if (!File.Exists(path)) return;
            try
            {
                ApplyToShip(JsonUtility.FromJson<ShipSaveData>(File.ReadAllText(path)));
                Debug.Log($"[SaveManager] Slot {slot} loaded.");
            }
            catch (Exception ex) { Debug.LogWarning($"[SaveManager] Slot {slot} load failed: {ex.Message}"); }
        }

        public string GetSlotInfo(int slot)
        {
            string path = SlotPath(slot);
            if (!File.Exists(path)) return null;
            try
            {
                var data = JsonUtility.FromJson<ShipSaveData>(File.ReadAllText(path));
                return $"Tier {data.shipLevel}  ·  {data.lastSavedUtc}";
            }
            catch { return "Corrupt"; }
        }

        // --- Legacy single-file API ---

        private ShipSaveData BuildSaveData()
        {
            var data = new ShipSaveData
            {
                currentLayer    = ship.CurrentLayer,
                hullIntegrity01 = ship.HullIntegrity,
                shipLevel       = ship.ShipLevel,
                lastSavedUtc    = DateTime.UtcNow.ToString("o")
            };
            if (crew != null)
                foreach (var member in crew.Roster)
                    data.crew.Add(new CrewSaveEntry { crewAssetName = member.name });
            return data;
        }

        public void Save()
        {
            if (ship == null) return;
            var data = BuildSaveData();
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
