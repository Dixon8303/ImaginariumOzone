using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.Core;
using Skybound.Events;
using Skybound.Systems;

namespace Skybound.UI
{
    /// <summary>
    /// Encounter overlay panel. Shows the event title and intro text when an encounter
    /// starts, and exposes a Resolve button the player taps to trigger resolution.
    /// Subscribes to GameDirector directly so it can display encounter data before
    /// UIManager updates the canvas group visibility.
    /// </summary>
    public class EncounterPanel : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private GameDirector director;

        [Header("Widgets")]
        [SerializeField] private TextMeshProUGUI titleLabel;
        [SerializeField] private TextMeshProUGUI introLabel;
        [SerializeField] private TextMeshProUGUI outcomeLabel;
        [SerializeField] private Button resolveButton;
        [SerializeField] private TextMeshProUGUI resolveButtonLabel;

        private void OnEnable()
        {
            if (director != null)
            {
                director.OnEncounterStarted += HandleEncounterStarted;
                director.OnEncounterResolved += HandleEncounterResolved;
            }
            if (resolveButton != null)
                resolveButton.onClick.AddListener(OnResolveClicked);

            SetResolveInteractable(false);
        }

        private void OnDisable()
        {
            if (director != null)
            {
                director.OnEncounterStarted -= HandleEncounterStarted;
                director.OnEncounterResolved -= HandleEncounterResolved;
            }
            if (resolveButton != null)
                resolveButton.onClick.RemoveListener(OnResolveClicked);
        }

        private void HandleEncounterStarted(SkyEvent evt)
        {
            if (titleLabel != null)
                titleLabel.text = evt.Encounter != null ? evt.Encounter.Title : evt.EventId;
            if (introLabel != null)
                introLabel.text = evt.Encounter != null ? evt.Encounter.IntroText : string.Empty;
            if (outcomeLabel != null)
                outcomeLabel.text = string.Empty;
            if (resolveButtonLabel != null)
                resolveButtonLabel.text = "Engage";
            SetResolveInteractable(true);
        }

        private void HandleEncounterResolved(SkyEvent evt, EventOutcome outcome)
        {
            if (outcomeLabel != null)
                outcomeLabel.text = outcome.LogText;
            SetResolveInteractable(false);
        }

        private void OnResolveClicked()
        {
            if (director != null && director.HasActiveEncounter)
                director.ResolveActiveEncounter();
        }

        private void SetResolveInteractable(bool value)
        {
            if (resolveButton != null)
                resolveButton.interactable = value;
        }
    }
}
