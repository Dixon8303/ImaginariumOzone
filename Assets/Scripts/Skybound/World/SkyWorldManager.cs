using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.World
{
    /// <summary>
    /// Runtime manager for the sky world. Holds the generated world data,
    /// handles cell discovery, and exposes queries used by the GameDirector,
    /// airship movement, and minimap systems.
    /// </summary>
    public class SkyWorldManager : MonoBehaviour
    {
        [Header("Generation")]
        [SerializeField] private int seed = 2026;
        [SerializeField] private int gridWidth = 32;
        [SerializeField] private int gridHeight = 32;
        [SerializeField] private bool autoGenerateOnStart = true;

        private SkyWorldData _world;

        public SkyWorldData World => _world;
        public int Seed => seed;

        // Raised when a cell is discovered for the first time
        public System.Action<SkyCell> OnCellDiscovered;

        private void Start()
        {
            if (autoGenerateOnStart)
                GenerateWorld(seed);
        }

        public void GenerateWorld(int newSeed)
        {
            seed = newSeed;
            _world = SkyGridGenerator.Generate(seed, gridWidth, gridHeight);

            // Name all islands at generation time (names are deterministic anyway)
            foreach (var cell in _world.Cells.Values)
                if (cell.HasIsland)
                    cell.IslandName = IslandNameGenerator.Generate(
                        cell.GridPos.x, cell.GridPos.y, seed);

            Debug.Log($"[SkyWorldManager] World generated — seed {seed}, " +
                      $"{gridWidth}x{gridHeight}, " +
                      $"{CountIslands()} islands across {_world.Cells.Count} cells.");
        }

        /// <summary>
        /// Mark a cell as discovered. Fires OnCellDiscovered the first time.
        /// Called by the airship movement system as the player enters each cell.
        /// </summary>
        public bool DiscoverCell(int x, int y)
        {
            var cell = _world?.GetCell(x, y);
            if (cell == null || cell.IsDiscovered) return false;
            cell.IsDiscovered = true;
            OnCellDiscovered?.Invoke(cell);
            return true;
        }

        public SkyCell GetCell(int x, int y) => _world?.GetCell(x, y);

        public SkyCell GetCell(Vector2Int pos) => _world?.GetCell(pos.x, pos.y);

        /// <summary>Returns all cells in a given biome — used by the event system.</summary>
        public List<SkyCell> GetCellsByBiome(SkyBiome biome)
        {
            var result = new List<SkyCell>();
            if (_world == null) return result;
            foreach (var cell in _world.Cells.Values)
                if (cell.Biome == biome) result.Add(cell);
            return result;
        }

        /// <summary>Returns neighbour cells (4-directional) for pathfinding.</summary>
        public List<SkyCell> GetNeighbours(Vector2Int pos)
        {
            var neighbours = new List<SkyCell>();
            Vector2Int[] dirs = { Vector2Int.up, Vector2Int.down, Vector2Int.left, Vector2Int.right };
            foreach (var d in dirs)
            {
                var cell = GetCell(pos + d);
                if (cell != null) neighbours.Add(cell);
            }
            return neighbours;
        }

        public int CountDiscovered()
        {
            int n = 0;
            foreach (var c in _world.Cells.Values) if (c.IsDiscovered) n++;
            return n;
        }

        private int CountIslands()
        {
            int n = 0;
            foreach (var c in _world.Cells.Values) if (c.HasIsland) n++;
            return n;
        }
    }
}
