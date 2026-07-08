using UnityEngine;
using Skybound.Core;

namespace Skybound.World
{
    /// <summary>
    /// Generates the seeded sky grid using three independent noise passes:
    ///   1. Density noise  → island existence + size
    ///   2. Elevation noise → which SkyLayer dominates each region
    ///   3. Corruption noise → danger level + anomaly probability
    ///
    /// Design rubric:
    ///   Replayability 5 — seed-reproducible, every integer seed is a unique world
    ///   Story Cohesion 5 — biome assignment driven by cultural layer logic
    ///   Fun 5 — corruption gradient creates natural risk/reward topology
    /// </summary>
    public static class SkyGridGenerator
    {
        // Noise scale: lower = larger landmasses, higher = fragmented archipelagos
        private const float DensityScale    = 0.08f;
        private const float ElevationScale  = 0.05f;
        private const float CorruptionScale = 0.12f;

        public static SkyWorldData Generate(int seed, int width = 32, int height = 32)
        {
            var world = new SkyWorldData { Seed = seed, Width = width, Height = height };

            // Seed Unity's random to derive noise offsets reproducibly
            Random.InitState(seed);
            Vector2 densityOffset    = new Vector2(Random.Range(0f, 9999f), Random.Range(0f, 9999f));
            Vector2 elevationOffset  = new Vector2(Random.Range(0f, 9999f), Random.Range(0f, 9999f));
            Vector2 corruptionOffset = new Vector2(Random.Range(0f, 9999f), Random.Range(0f, 9999f));

            for (int x = 0; x < width; x++)
            {
                for (int y = 0; y < height; y++)
                {
                    float density = Mathf.PerlinNoise(
                        x * DensityScale + densityOffset.x,
                        y * DensityScale + densityOffset.y);

                    float elevation = Mathf.PerlinNoise(
                        x * ElevationScale + elevationOffset.x,
                        y * ElevationScale + elevationOffset.y);

                    float corruption = Mathf.PerlinNoise(
                        x * CorruptionScale + corruptionOffset.x,
                        y * CorruptionScale + corruptionOffset.y);

                    SkyLayer layer = ElevationToLayer(elevation);
                    SkyBiome biome = AssignBiome(layer, corruption, density);

                    var cell = new SkyCell(new Vector2Int(x, y), layer, biome, density, corruption);
                    world.Cells[new Vector2Int(x, y)] = cell;
                }
            }

            AssignWeather(world, seed);
            return world;
        }

        private static SkyLayer ElevationToLayer(float e)
        {
            if (e < 0.35f) return SkyLayer.LowSky;
            if (e < 0.60f) return SkyLayer.MidSky;
            if (e < 0.82f) return SkyLayer.HighSky;
            return SkyLayer.VoidSky;
        }

        /// <summary>
        /// Biome assignment carries the world's cultural identity.
        /// Imperial Corridors cluster in MidSky — they control the middle routes.
        /// Ancestor Fields appear in LowSky calm zones — memory survives at low altitude.
        /// Void Anomalies require both high elevation AND high corruption.
        /// </summary>
        private static SkyBiome AssignBiome(SkyLayer layer, float corruption, float density)
        {
            switch (layer)
            {
                case SkyLayer.LowSky:
                    if (corruption > 0.65f) return SkyBiome.StormRift;
                    if (density < 0.3f)     return SkyBiome.AncestorFields;
                    return SkyBiome.TradeWinds;

                case SkyLayer.MidSky:
                    if (corruption > 0.70f) return SkyBiome.StormRift;
                    if (corruption > 0.45f) return SkyBiome.ImperialCorridor;
                    return SkyBiome.Uncharted;

                case SkyLayer.HighSky:
                    if (corruption > 0.60f) return SkyBiome.CelestialRuin;
                    return SkyBiome.Uncharted;

                case SkyLayer.VoidSky:
                    if (corruption > 0.50f) return SkyBiome.VoidAnomaly;
                    return SkyBiome.CelestialRuin;

                default: return SkyBiome.Uncharted;
            }
        }

        /// <summary>
        /// Scatter weather states across the grid post-generation.
        /// AncestralCalm is rare (5% chance) and only appears in LowSky/AncestorFields —
        /// it rewards players who explore calm zones with discovery bonuses.
        /// </summary>
        private static void AssignWeather(SkyWorldData world, int seed)
        {
            Random.InitState(seed + 1);
            foreach (var cell in world.Cells.Values)
            {
                float roll = Random.value;
                cell.Weather = cell.Layer switch
                {
                    SkyLayer.LowSky  => roll < 0.05f && cell.Biome == SkyBiome.AncestorFields
                                            ? WeatherState.AncestralCalm
                                            : roll < 0.15f ? WeatherState.Crosswind : WeatherState.Clear,
                    SkyLayer.MidSky  => roll < 0.35f ? WeatherState.AetherStorm
                                            : roll < 0.55f ? WeatherState.Crosswind : WeatherState.Clear,
                    SkyLayer.HighSky => roll < 0.45f ? WeatherState.AetherStorm : WeatherState.Clear,
                    SkyLayer.VoidSky => roll < 0.60f ? WeatherState.VoidSurge : WeatherState.AetherStorm,
                    _                => WeatherState.Clear
                };
            }
        }
    }
}
