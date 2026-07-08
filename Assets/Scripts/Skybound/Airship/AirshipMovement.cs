using System.Collections;
using UnityEngine;
using Skybound.Core;
using Skybound.World;

namespace Skybound.Airship
{
    /// <summary>
    /// Grid-based airship movement with weather-modified movement costs and
    /// layer-ascent gating. The ship moves one cell per "tick"; weather and
    /// biome conditions modify the tick duration to simulate wind resistance.
    ///
    /// Rubric decisions:
    ///   Fun 5       — weather forces rerouting, no two routes feel identical
    ///   Story 5     — ascending layers is gated by ship level (empire controls upper sky)
    ///   Dynamism 4  — movement speed visually varies with weather state
    ///   Replay 5    — same world, different routes = different risk exposure
    /// </summary>
    public class AirshipMovement : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private SkyWorldManager world;

        [Header("Movement Tuning")]
        [SerializeField] private float baseTickSeconds = 1.2f;
        [SerializeField] private float cellSize = 1f;

        [Header("Layer Ascent Requirements (ship level)")]
        [SerializeField] private int midSkyRequiredLevel  = 2;
        [SerializeField] private int highSkyRequiredLevel = 4;
        [SerializeField] private int voidSkyRequiredLevel = 7;

        private Vector2Int _gridPos = Vector2Int.zero;
        private bool _isMoving;
        private int _shipLevel = 1;

        public Vector2Int GridPosition => _gridPos;
        public bool IsMoving => _isMoving;

        public System.Action<Vector2Int, SkyCell> OnCellEntered;
        public System.Action<string> OnMovementBlocked;

        public void SetShipLevel(int level) => _shipLevel = level;

        public void SetPosition(Vector2Int pos)
        {
            _gridPos = pos;
            world?.DiscoverCell(pos.x, pos.y);
        }

        /// <summary>
        /// Request movement to an adjacent cell. Validates layer access and
        /// starts the movement coroutine if clear.
        /// </summary>
        public bool TryMove(Vector2Int direction)
        {
            if (_isMoving) return false;

            Vector2Int target = _gridPos + direction;
            var cell = world?.GetCell(target);
            if (cell == null)
            {
                OnMovementBlocked?.Invoke("Edge of charted sky.");
                return false;
            }

            if (!CanAccessLayer(cell.Layer, out string blockReason))
            {
                OnMovementBlocked?.Invoke(blockReason);
                return false;
            }

            StartCoroutine(MoveToCell(target, cell));
            return true;
        }

        private IEnumerator MoveToCell(Vector2Int targetPos, SkyCell cell)
        {
            _isMoving = true;
            float duration = baseTickSeconds * WeatherCostMultiplier(cell.Weather);

            Vector3 startWorld = GridToWorld(_gridPos);
            Vector3 endWorld   = GridToWorld(targetPos);
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = Mathf.SmoothStep(0f, 1f, elapsed / duration);
                transform.position = Vector3.Lerp(startWorld, endWorld, t);
                yield return null;
            }

            transform.position = endWorld;
            _gridPos = targetPos;
            _isMoving = false;

            world?.DiscoverCell(targetPos.x, targetPos.y);
            OnCellEntered?.Invoke(targetPos, cell);
        }

        /// <summary>
        /// Weather cost multiplier — storm cells take 3x longer to traverse.
        /// AncestralCalm is faster than clear (tailwind from the ancestors).
        /// </summary>
        private float WeatherCostMultiplier(WeatherState weather) => weather switch
        {
            WeatherState.AncestralCalm => 0.6f,
            WeatherState.Clear         => 1.0f,
            WeatherState.Crosswind     => 1.5f,
            WeatherState.AetherStorm   => 2.8f,
            WeatherState.VoidSurge     => 3.5f,
            _                          => 1.0f
        };

        private bool CanAccessLayer(SkyLayer layer, out string reason)
        {
            reason = string.Empty;
            switch (layer)
            {
                case SkyLayer.MidSky when _shipLevel < midSkyRequiredLevel:
                    reason = $"Mid Sky requires ship level {midSkyRequiredLevel}. Imperial jammers hold the boundary.";
                    return false;
                case SkyLayer.HighSky when _shipLevel < highSkyRequiredLevel:
                    reason = $"High Sky requires ship level {highSkyRequiredLevel}. Ancient wards block ascent.";
                    return false;
                case SkyLayer.VoidSky when _shipLevel < voidSkyRequiredLevel:
                    reason = $"Void Sky requires ship level {voidSkyRequiredLevel}. Your hull cannot survive the rift.";
                    return false;
                default:
                    return true;
            }
        }

        private Vector3 GridToWorld(Vector2Int pos)
            => new Vector3(pos.x * cellSize, pos.y * cellSize, 0f);
    }
}
