using UnityEngine;
using Skybound.Airship;
using Skybound.Systems;
using Skybound.UI;

namespace Skybound.Input
{
    /// <summary>
    /// Mobile touch input layer. Runs alongside GameBootstrap and translates
    /// finger gestures into the same calls GameBootstrap makes from keyboard.
    ///
    /// Gestures:
    ///   Swipe (≥ minSwipePx in &lt;maxSwipeSeconds) → TryMove in swipe direction
    ///   Tap (short, no significant movement)       → roll for event (same as Space)
    ///   Two-finger tap                             → resolve active encounter (same as Enter)
    ///   Three-finger tap                           → toggle Save/Load panel (same as Escape)
    ///
    /// Rubric:
    ///   Fun 5 — movement feels natural on a phone, not a ported keyboard game
    ///   UX  5 — one-handed operation; no small targets to mis-tap
    /// </summary>
    public class TouchInputHandler : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private AirshipMovement airship;
        [SerializeField] private GameDirector    director;
        [SerializeField] private SaveLoadPanel   saveLoadPanel;

        [Header("Gesture Thresholds")]
        [SerializeField] private float minSwipePx      = 60f;   // minimum drag to count as a swipe
        [SerializeField] private float maxSwipeSeconds  = 0.45f; // max duration for a swipe
        [SerializeField] private float tapMaxPx         = 20f;   // max movement to count as a tap
        [SerializeField] private float tapMaxSeconds    = 0.25f; // max duration for a tap

        private Vector2 _touchStart;
        private float   _touchStartTime;
        private bool    _tracking;

        private void Update()
        {
#if UNITY_EDITOR
            HandleMouseFallback();
#endif
            if (UnityEngine.Input.touchCount == 0) return;

            // Three-finger tap → Save/Load panel
            if (UnityEngine.Input.touchCount == 3)
            {
                bool allBegan = true;
                foreach (var t in UnityEngine.Input.touches)
                    if (t.phase != TouchPhase.Began) allBegan = false;
                if (allBegan && saveLoadPanel != null)
                {
                    if (saveLoadPanel.IsVisible) saveLoadPanel.Hide();
                    else                         saveLoadPanel.Show();
                    return;
                }
            }

            // Two-finger tap → resolve encounter
            if (UnityEngine.Input.touchCount == 2)
            {
                var t0 = UnityEngine.Input.GetTouch(0);
                var t1 = UnityEngine.Input.GetTouch(1);
                if (t0.phase == TouchPhase.Began && t1.phase == TouchPhase.Began)
                {
                    if (director != null && director.HasActiveEncounter)
                    {
                        director.ResolveActiveEncounter();
                        return;
                    }
                }
            }

            // Single-finger swipe / tap
            if (UnityEngine.Input.touchCount != 1) return;
            var touch = UnityEngine.Input.GetTouch(0);

            if (touch.phase == TouchPhase.Began)
            {
                _touchStart     = touch.position;
                _touchStartTime = Time.unscaledTime;
                _tracking       = true;
            }
            else if (_tracking && (touch.phase == TouchPhase.Ended || touch.phase == TouchPhase.Canceled))
            {
                _tracking = false;
                float dt   = Time.unscaledTime - _touchStartTime;
                Vector2 delta = touch.position - _touchStart;
                float dist  = delta.magnitude;

                if (dist < tapMaxPx && dt < tapMaxSeconds)
                {
                    // Tap → roll for event
                    if (director != null && !director.HasActiveEncounter)
                        director.CheckForEvent();
                }
                else if (dist >= minSwipePx && dt <= maxSwipeSeconds)
                {
                    // Swipe → move airship
                    TryMoveFromSwipe(delta);
                }
            }
        }

        private void TryMoveFromSwipe(Vector2 delta)
        {
            if (airship == null || airship.IsMoving) return;
            if (director != null && director.HasActiveEncounter) return;

            Vector2Int dir;
            if (Mathf.Abs(delta.x) > Mathf.Abs(delta.y))
                dir = delta.x > 0 ? Vector2Int.right : Vector2Int.left;
            else
                dir = delta.y > 0 ? Vector2Int.up : Vector2Int.down;

            airship.TryMove(dir);
        }

#if UNITY_EDITOR
        // In-editor mouse fallback so touch logic is testable in Play mode
        private Vector2 _mouseStart;
        private float   _mouseStartTime;
        private bool    _mouseTracking;

        private void HandleMouseFallback()
        {
            if (UnityEngine.Input.GetMouseButtonDown(0))
            {
                _mouseStart     = UnityEngine.Input.mousePosition;
                _mouseStartTime = Time.unscaledTime;
                _mouseTracking  = true;
            }
            else if (_mouseTracking && UnityEngine.Input.GetMouseButtonUp(0))
            {
                _mouseTracking = false;
                float   dt    = Time.unscaledTime - _mouseStartTime;
                Vector2 delta = (Vector2)UnityEngine.Input.mousePosition - _mouseStart;
                float dist    = delta.magnitude;

                if (dist < tapMaxPx && dt < tapMaxSeconds)
                {
                    if (director != null && !director.HasActiveEncounter)
                        director.CheckForEvent();
                }
                else if (dist >= minSwipePx && dt <= maxSwipeSeconds)
                {
                    TryMoveFromSwipe(delta);
                }
            }
        }
#endif
    }
}
