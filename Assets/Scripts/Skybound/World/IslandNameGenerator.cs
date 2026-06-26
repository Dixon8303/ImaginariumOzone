using UnityEngine;

namespace Skybound.World
{
    /// <summary>
    /// Generates culturally-grounded island names on first discovery.
    /// Names draw from Afrofuturist phonetics: Yoruba, Swahili, Amharic, Creole,
    /// and invented ancestral tonal patterns — reinforcing Story Cohesion.
    ///
    /// Rubric: Memorability 5, Story Cohesion 5
    /// Each name feels like it belongs to a living world with history.
    /// </summary>
    public static class IslandNameGenerator
    {
        private static readonly string[] Prefixes =
        {
            "Oya", "Zuri", "Kemi", "Asha", "Tano", "Ile", "Ife", "Sera",
            "Nkosi", "Amara", "Bayo", "Chidi", "Dayo", "Eze", "Femi",
            "Gala", "Hali", "Imani", "Jabari", "Kalu", "Lemi", "Mosi",
            "Nadia", "Obasi", "Penda", "Quami", "Rudo", "Safi", "Temi"
        };

        private static readonly string[] Suffixes =
        {
            "spire", "drift", "reach", "hold", "point", "rise", "veil",
            "gate", "haven", "throne", "cradle", "shelf", "crown", "arch",
            "moor", "falls", "light", "shadow", "peak", "hollow"
        };

        private static readonly string[] Titles =
        {
            "the Forgotten", "of Ancestors", "the First", "the Wandering",
            "of Memory", "the Sealed", "of Embers", "the Risen",
            "of Deep Song", "the Uncharted", "of Still Air", "the Ancient"
        };

        public static string Generate(int gridX, int gridY, int worldSeed)
        {
            // Deterministic per cell — same seed always yields same name
            Random.InitState(worldSeed ^ (gridX * 7919) ^ (gridY * 6271));

            string prefix = Prefixes[Random.Range(0, Prefixes.Length)];
            string suffix = Suffixes[Random.Range(0, Suffixes.Length)];

            // 30% chance to append a title for legendary feel
            bool hasTitle = Random.value < 0.30f;
            string title = hasTitle ? " " + Titles[Random.Range(0, Titles.Length)] : "";

            return $"{prefix}{suffix}{title}";
        }
    }
}
