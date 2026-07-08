using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.Core;
using Skybound.Ship;
using Skybound.Systems;

namespace Skybound.UI
{
    /// <summary>
    /// Exploration HUD: hull bar, sky layer label, crew count, and a manual "Check for Event"
    /// button for testing. In production, CheckForEvent is called by your run-loop/tick system.
    /// Polls ShipManager each frame for hull + layer — cheap reads, no events needed.
    /// </summary>
    public class ExplorationHUD : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private ShipManager ship;
        [SerializeField] private GameDirector director;

        [Header("Widgets")]
        [SerializeField] private Slider hullSlider;
        [SerializeField] private TextMeshProUGUI layerLabel;
        [SerializeField] private TextMeshProUGUI crewCountLabel;
        [SerializeField] private Button checkEventButton;

        private ShipCrewManager _crew;

        private void Awake()
        {
            if (ship != null)
                _crew = ship.GetComponent<ShipCrewManager>();
        }

        private void OnEnable()
        {
            if (checkEventButton != null)
                checkEventButton.onClick.AddListener(OnCheckEventClicked);
        }

        private void OnDisable()
        {
            if (checkEventButton != null)
                checkEventButton.onClick.RemoveListener(OnCheckEventClicked);
        }

        private void Update()
        {
            if (ship == null) return;

            if (hullSlider != null)
                hullSlider.value = ship.HullIntegrity;

            if (layerLabel != null)
                layerLabel.text = ship.CurrentLayer.ToString();

            if (crewCountLabel != null && _crew != null)
                crewCountLabel.text = $"Crew {_crew.FilledSlots}/{_crew.MaxSlots}";
        }

        private void OnCheckEventClicked()
        {
            if (director != null && !director.HasActiveEncounter)
                director.CheckForEvent();
        }
    }
}
