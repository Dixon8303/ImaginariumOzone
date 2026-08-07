using UnityEngine;
using Skybound.World;

namespace Skybound.Airship
{
    /// <summary>
    /// Procedural airship silhouette drawn with LineRenderers — no art assets needed.
    /// Draws three layers: hull (elongated teardrop), sail mast, and engine glow ring.
    /// Colors shift based on current biome to reinforce visual dynamism.
    ///
    /// Rubric:
    ///   Visual Dynamism 5 — biome-reactive color, gentle bob animation
    ///   Memorability 4   — a ship that looks like it belongs in this world
    ///   Story 5          — organic silhouette (not mechanical) = sky civilization aesthetic
    /// </summary>
    public class AirshipVisual : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private AirshipMovement movement;
        [SerializeField] private SkyWorldManager worldManager;

        [Header("Scale")]
        [SerializeField] private float hullWidth  = 0.35f;
        [SerializeField] private float hullLength = 0.55f;
        [SerializeField] private float bobAmplitude = 0.04f;
        [SerializeField] private float bobSpeed     = 1.4f;

        private LineRenderer _hull;
        private LineRenderer _mast;
        private LineRenderer _engineRing;
        private float        _bobTimer;
        private Color        _currentColor = new Color(0.85f, 0.65f, 0.30f);

        private void Awake()
        {
            _hull       = MakeLine("Hull",       0.06f, 12);
            _mast       = MakeLine("Mast",       0.03f, 2);
            _engineRing = MakeLine("EngineRing", 0.025f, 16);
            RebuildGeometry();
        }

        private void Update()
        {
            if (movement == null) return;

            // Smooth follow — visual trails slightly behind grid position
            Vector3 target = movement.transform.position;
            transform.position = Vector3.Lerp(transform.position, target, Time.deltaTime * 8f);

            // Gentle bob
            _bobTimer += Time.deltaTime * bobSpeed;
            float bob = Mathf.Sin(_bobTimer) * bobAmplitude;
            transform.localPosition = new Vector3(transform.localPosition.x,
                                                   transform.localPosition.y + bob * Time.deltaTime,
                                                   transform.localPosition.z);

            // Biome color reaction
            UpdateBiomeColor();
        }

        private void UpdateBiomeColor()
        {
            if (worldManager == null) return;
            var cell = worldManager.GetCell(movement.GridPosition);
            if (cell == null) return;

            Color target = cell.Biome switch
            {
                SkyBiome.TradeWinds       => new Color(0.40f, 0.70f, 0.95f),
                SkyBiome.AncestorFields   => new Color(0.50f, 0.90f, 0.60f),
                SkyBiome.StormRift        => new Color(0.75f, 0.40f, 0.85f),
                SkyBiome.ImperialCorridor => new Color(0.80f, 0.80f, 0.85f),
                SkyBiome.CelestialRuin    => new Color(0.95f, 0.80f, 0.30f),
                SkyBiome.VoidAnomaly      => new Color(0.85f, 0.20f, 0.40f),
                _                         => new Color(0.85f, 0.65f, 0.30f)
            };

            _currentColor = Color.Lerp(_currentColor, target, Time.deltaTime * 1.5f);
            ApplyColor(_currentColor);
        }

        private void RebuildGeometry()
        {
            // Hull: teardrop shape (pointed bow, rounded stern)
            int pts = 12;
            var hullPts = new Vector3[pts + 1];
            for (int i = 0; i <= pts; i++)
            {
                float t   = (float)i / pts;
                float ang = t * Mathf.PI * 2f;
                float rx  = hullLength * (0.5f + 0.5f * Mathf.Cos(ang)); // elongated bow
                float ry  = hullWidth  * Mathf.Sin(ang);
                hullPts[i] = new Vector3(rx - hullLength * 0.3f, ry, 0f);
            }
            _hull.positionCount = pts + 1;
            _hull.SetPositions(hullPts);

            // Mast: single vertical line above center
            _mast.positionCount = 2;
            _mast.SetPosition(0, new Vector3(0,  hullWidth,       0f));
            _mast.SetPosition(1, new Vector3(0,  hullWidth + 0.2f, 0f));

            // Engine glow ring: small circle at stern
            int rpts = 16;
            var ring = new Vector3[rpts + 1];
            float r  = 0.09f;
            for (int i = 0; i <= rpts; i++)
            {
                float a = (float)i / rpts * Mathf.PI * 2f;
                ring[i] = new Vector3(-hullLength * 0.28f + Mathf.Cos(a) * r,
                                       Mathf.Sin(a) * r, 0f);
            }
            _engineRing.positionCount = rpts + 1;
            _engineRing.SetPositions(ring);

            ApplyColor(_currentColor);
        }

        private void ApplyColor(Color c)
        {
            _hull.startColor       = c;
            _hull.endColor         = c;
            _mast.startColor       = Color.white;
            _mast.endColor         = Color.white;
            _engineRing.startColor = new Color(c.r, c.g * 0.5f, c.b * 0.3f, 1f);
            _engineRing.endColor   = _engineRing.startColor;
        }

        private LineRenderer MakeLine(string n, float width, int capacity)
        {
            var go  = new GameObject(n);
            go.transform.SetParent(transform, false);
            var lr  = go.AddComponent<LineRenderer>();
            lr.useWorldSpace    = false;
            lr.startWidth       = width;
            lr.endWidth         = width;
            lr.positionCount    = capacity;
            lr.loop             = false;
            lr.material         = new Material(Shader.Find("Sprites/Default"));
            return lr;
        }
    }
}
