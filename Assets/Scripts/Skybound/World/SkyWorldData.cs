using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;

namespace Skybound.World
{
    /// <summary>
    /// Biome identity. Named culturally to reinforce the Afrofuturist world.
    /// Each biome carries risk, reward, and event-flavor multipliers.
    /// </summary>
    public enum SkyBiome
    {
        TradeWinds,       // Low Sky — busy routes, moderate safety, merchant culture
        AncestorFields,   // Low Sky — calm, discovery-rich, ancient memory sites
        StormRift,        // Mid Sky — dangerous weather, high salvage
        ImperialCorridor, // Mid Sky — enemy patrols, locked navigation nodes
        CelestialRuin,    // High Sky — ancient infrastructure, relic drops
        VoidAnomaly,      // Void Sky — extreme danger, mythic discovery tier
        Uncharted          // Any layer — blank space, first-discovery bonus
    }

    /// <summary>Weather conditions that modify movement cost and event probability.</summary>
    public enum WeatherState
    {
        Clear,
        Crosswind,
        AetherStorm,
        VoidSurge,
        AncestralCalm  // rare — boosts discovery, suppresses combat
    }

    /// <summary>A single cell in the sky grid.</summary>
    public class SkyCell
    {
        public Vector2Int GridPos;
        public SkyLayer Layer;
        public SkyBiome Biome;
        public WeatherState Weather;
        public float IslandDensity;   // 0..1 from noise
        public float DangerLevel;     // 0..1 from corruption noise
        public bool IsDiscovered;
        public bool HasIsland;
        public string IslandName;     // assigned on first discovery

        public SkyCell(Vector2Int pos, SkyLayer layer, SkyBiome biome,
            float density, float danger)
        {
            GridPos = pos;
            Layer = layer;
            Biome = biome;
            IslandDensity = density;
            DangerLevel = danger;
            HasIsland = density > 0.55f;
            Weather = WeatherState.Clear;
            IsDiscovered = false;
        }
    }

    /// <summary>Full world snapshot produced by SkyGridGenerator.</summary>
    public class SkyWorldData
    {
        public int Seed;
        public int Width;
        public int Height;
        public Dictionary<Vector2Int, SkyCell> Cells = new Dictionary<Vector2Int, SkyCell>();

        public SkyCell GetCell(int x, int y)
        {
            Cells.TryGetValue(new Vector2Int(x, y), out var cell);
            return cell;
        }
    }
}
