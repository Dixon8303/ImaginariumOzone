using UnityEngine;
using Skybound.Ship;

namespace Skybound.Systems
{
    /// <summary>
    /// Minimal scene bootstrapper for testing the vertical slice. Wires the ship data source
    /// into the director, then lets you drive the loop from the keyboard:
    ///   - checkKey   : run one CheckForEvent pass (roll for an encounter)
    ///   - resolveKey : resolve the active encounter
    /// Remove or disable for production; replace with your real run-loop / tick scheduler.
    /// </summary>
    public class SkyboundBootstrap : MonoBehaviour
    {
        [SerializeField] private GameDirector director;
        [SerializeField] private ShipManager ship;

        [Header("Test Controls")]
        [SerializeField] private KeyCode checkKey = KeyCode.Space;
        [SerializeField] private KeyCode resolveKey = KeyCode.Return;

        private void Start()
        {
            if (director == null || ship == null)
            {
                Debug.LogError("[SkyboundBootstrap] Assign GameDirector and ShipManager in the inspector.");
                return;
            }
            director.Initialize(ship);
        }

        private void Update()
        {
            if (director == null) return;
            if (Input.GetKeyDown(checkKey)) director.CheckForEvent();
            if (Input.GetKeyDown(resolveKey)) director.ResolveActiveEncounter();
        }
    }
}
