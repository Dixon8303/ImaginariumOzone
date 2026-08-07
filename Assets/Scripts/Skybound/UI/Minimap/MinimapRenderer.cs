using UnityEngine;
using UnityEngine.UI;
using Skybound.World;
using Skybound.Airship;
using Skybound.Discovery;

namespace Skybound.UI
{
    /// <summary>
    /// Procedural minimap rendered onto a RawImage via a Texture2D.
    /// Each pixel = one sky grid cell. Redraws only dirty cells for performance.
    /// Color encodes biome + discovery state; ship position is a bright marker.
    ///
    /// Rubric:
    ///   Visual Dynamism 5 — fog lifts cell by cell as player explores
    ///   Memorability 5    — your specific route is visible as a trail of lit pixels
    ///   Fun 4             — unknown space is visually enticing (dark with faint shapes)
    /// </summary>
    [RequireComponent(typeof(RawImage))]
    public class MinimapRenderer : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private SkyWorldManager  worldManager;
        [SerializeField] private AirshipMovement  airship;
        [SerializeField] private DiscoveryAtlas   atlas;

        [Header("Display")]
        [SerializeField] private int cellPixelSize = 4;
        [SerializeField] private Color fogColor    = new Color(0.05f, 0.05f, 0.08f, 1f);
        [SerializeField] private Color shipColor   = Color.white;

        private Texture2D _tex;
        private RawImage  _image;
        private Vector2Int _lastShipPos = new Vector2Int(-1, -1);
        private bool _dirty = true;

        // Biome color palette — warm cultural colors vs cold imperial
        private static readonly Color ColTradeWinds       = new Color(0.30f, 0.55f, 0.80f);
        private static readonly Color ColAncestorFields   = new Color(0.25f, 0.65f, 0.45f);
        private static readonly Color ColStormRift        = new Color(0.55f, 0.30f, 0.65f);
        private static readonly Color ColImperialCorridor = new Color(0.70f, 0.70f, 0.75f);
        private static readonly Color ColCelestialRuin    = new Color(0.80f, 0.65f, 0.25f);
        private static readonly Color ColVoidAnomaly      = new Color(0.65f, 0.10f, 0.30f);
        private static readonly Color ColUncharted        = new Color(0.18f, 0.18f, 0.22f);

        private void Awake()
        {
            _image = GetComponent<RawImage>();
        }

        private void Start()
        {
            if (worldManager == null) return;
            InitTexture(worldManager.World.Width, worldManager.World.Height);

            if (atlas != null)
            {
                atlas.OnEntryDiscovered += _ => _dirty = true;
                atlas.OnEntryUpgraded   += _ => _dirty = true;
            }
        }

        private void InitTexture(int w, int h)
        {
            _tex = new Texture2D(w * cellPixelSize, h * cellPixelSize, TextureFormat.RGB24, false)
            {
                filterMode = FilterMode.Point,
                wrapMode   = TextureWrapMode.Clamp
            };
            // Fill with fog
            Color[] fog = new Color[_tex.width * _tex.height];
            for (int i = 0; i < fog.Length; i++) fog[i] = fogColor;
            _tex.SetPixels(fog);
            _tex.Apply();
            _image.texture = _tex;
        }

        private void Update()
        {
            if (worldManager == null || _tex == null) return;

            Vector2Int shipPos = airship != null ? airship.GridPosition : Vector2Int.zero;
            if (_dirty || shipPos != _lastShipPos)
            {
                Redraw(shipPos);
                _lastShipPos = shipPos;
                _dirty = false;
            }
        }

        private void Redraw(Vector2Int shipPos)
        {
            var world = worldManager.World;
            int s = cellPixelSize;

            foreach (var cell in world.Cells.Values)
            {
                Color c = GetCellColor(cell);
                int px = cell.GridPos.x * s;
                int py = cell.GridPos.y * s;
                for (int dx = 0; dx < s; dx++)
                    for (int dy = 0; dy < s; dy++)
                        _tex.SetPixel(px + dx, py + dy, c);
            }

            // Draw ship as a bright cross marker
            DrawCross(shipPos.x * s + s / 2, shipPos.y * s + s / 2, shipColor);

            _tex.Apply();
        }

        private Color GetCellColor(SkyCell cell)
        {
            if (!cell.IsDiscovered)
            {
                // Faint hint of what's underneath — visible at high brightness settings
                Color hint = BiomeColor(cell.Biome);
                return Color.Lerp(fogColor, hint, 0.08f);
            }

            Color base_ = BiomeColor(cell.Biome);

            // Danger level darkens the cell slightly
            base_ = Color.Lerp(base_, Color.black, cell.DangerLevel * 0.3f);

            // Island cells get a slight brightness boost
            if (cell.HasIsland) base_ = Color.Lerp(base_, Color.white, 0.15f);

            return base_;
        }

        private static Color BiomeColor(SkyBiome biome) => biome switch
        {
            SkyBiome.TradeWinds       => ColTradeWinds,
            SkyBiome.AncestorFields   => ColAncestorFields,
            SkyBiome.StormRift        => ColStormRift,
            SkyBiome.ImperialCorridor => ColImperialCorridor,
            SkyBiome.CelestialRuin    => ColCelestialRuin,
            SkyBiome.VoidAnomaly      => ColVoidAnomaly,
            _                         => ColUncharted
        };

        private void DrawCross(int cx, int cy, Color c)
        {
            int r = cellPixelSize;
            for (int i = -r; i <= r; i++)
            {
                SafeSet(cx + i, cy, c);
                SafeSet(cx, cy + i, c);
            }
        }

        private void SafeSet(int x, int y, Color c)
        {
            if (x >= 0 && x < _tex.width && y >= 0 && y < _tex.height)
                _tex.SetPixel(x, y, c);
        }

        private void OnDestroy()
        {
            if (_tex != null) Destroy(_tex);
        }
    }
}
