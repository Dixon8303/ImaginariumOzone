using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using Skybound.World;

namespace Skybound.Navigation
{
    /// <summary>
    /// Auto-navigates the airship along a computed A* path one cell at a time.
    /// The player sets a destination (grid position) and the navigator drives
    /// AirshipMovement through each step, pausing if an encounter interrupts.
    ///
    /// Usage: call SetDestination(pos) from the minimap click or command bar.
    /// Navigation pauses when GameDirector raises an encounter and resumes after.
    /// </summary>
    public class AutoNavigator : MonoBehaviour
    {
        [SerializeField] private AirshipMovement  airship;
        [SerializeField] private SkyWorldManager  worldManager;
        [SerializeField] private Skybound.Systems.GameDirector director;

        private List<Vector2Int> _path;
        private int              _pathIndex;
        private bool             _navigating;

        public bool   IsNavigating  => _navigating;
        public Vector2Int? Destination => _path != null && _path.Count > 0
            ? _path[_path.Count - 1] : (Vector2Int?)null;

        public System.Action<Vector2Int>  OnDestinationReached;
        public System.Action<string>      OnNavigationBlocked;
        public System.Action<List<Vector2Int>> OnPathComputed;

        public void SetDestination(Vector2Int goal)
        {
            if (airship == null || worldManager == null) return;
            StopNavigation();

            var path = SkyPathfinder.FindPath(
                worldManager, airship.GridPosition, goal, GetShipLevel());

            if (path == null || path.Count == 0)
            {
                OnNavigationBlocked?.Invoke("No route found to that position.");
                return;
            }

            _path      = path;
            _pathIndex = 0;
            _navigating = true;
            OnPathComputed?.Invoke(_path);
            StartCoroutine(NavigateCoroutine());
        }

        public void StopNavigation()
        {
            _navigating = false;
            StopAllCoroutines();
            _path = null;
        }

        private IEnumerator NavigateCoroutine()
        {
            while (_navigating && _path != null && _pathIndex < _path.Count)
            {
                // Pause if encounter is active — resume after it resolves
                while (director != null && director.HasActiveEncounter)
                    yield return new WaitForSeconds(0.2f);

                if (!_navigating) yield break;

                // Wait for airship to finish current move
                while (airship.IsMoving)
                    yield return null;

                Vector2Int nextStep = _path[_pathIndex];
                Vector2Int delta    = nextStep - airship.GridPosition;

                bool moved = airship.TryMove(delta);
                if (!moved)
                {
                    OnNavigationBlocked?.Invoke("Route blocked — recalculating.");
                    SetDestination(_path[_path.Count - 1]); // recalculate from current pos
                    yield break;
                }

                _pathIndex++;
                yield return null;
            }

            if (_navigating)
            {
                _navigating = false;
                OnDestinationReached?.Invoke(airship.GridPosition);
            }
        }

        private int GetShipLevel()
        {
            var ship = FindObjectOfType<Skybound.Ship.ShipManager>();
            return ship != null ? ship.ShipLevel : 1;
        }
    }
}
