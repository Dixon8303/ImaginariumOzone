using System;
using System.Collections.Generic;
using UnityEngine;
using Skybound.Core;
using Skybound.Events;

namespace Skybound.Systems
{
    /// <summary>
    /// Drives UI presentation via a two-state machine (Exploration / Encounter).
    /// Subscribes to the GameDirector and toggles UI layers on transition. It assumes no
    /// specific widget toolkit: layers are CanvasGroups (null-safe) and the discovery feed
    /// is exposed as data plus events any view (TMP, uGUI, UI Toolkit) can bind to.
    /// </summary>
    public class UIManager : MonoBehaviour
    {
        public enum UIState { Exploration, Encounter }

        [Header("Dependencies")]
        [SerializeField] private GameDirector director;

        [Header("UI Layers (optional — toggling is null-safe)")]
        [Tooltip("Exploration HUD: minimap, navigation command bar.")]
        [SerializeField] private CanvasGroup explorationHud;
        [Tooltip("Encounter overlay: combat / event panel.")]
        [SerializeField] private CanvasGroup encounterOverlay;

        [Header("Feed")]
        [Tooltip("Max retained lines in the discovery/combat feed.")]
        [SerializeField] private int maxFeedEntries = 50;

        private readonly List<string> _feed = new List<string>();
        private UIState _state = UIState.Exploration;

        public UIState State => _state;
        public IReadOnlyList<string> Feed => _feed;

        /// <summary>Raised whenever a line is appended to the feed. Bind your text view here.</summary>
        public event Action<string> OnFeedEntryAdded;

        /// <summary>Raised on every state transition. Views can animate layer fades here.</summary>
        public event Action<UIState> OnStateChanged;

        private void OnEnable()
        {
            if (director != null)
            {
                director.OnEncounterStarted += HandleEncounterStarted;
                director.OnEncounterResolved += HandleEncounterResolved;
            }
            ApplyState(UIState.Exploration);
        }

        private void OnDisable()
        {
            if (director != null)
            {
                director.OnEncounterStarted -= HandleEncounterStarted;
                director.OnEncounterResolved -= HandleEncounterResolved;
            }
        }

        private void HandleEncounterStarted(SkyEvent evt)
        {
            SetState(UIState.Encounter);
            string title = evt.Encounter != null ? evt.Encounter.Title : evt.EventId;
            AppendFeed($"[Encounter] {title}");
        }

        private void HandleEncounterResolved(SkyEvent evt, EventOutcome outcome)
        {
            AppendFeed(outcome.LogText);
            SetState(UIState.Exploration);
        }

        /// <summary>Transition the state machine. Idempotent — re-entering the same state is a no-op.</summary>
        public void SetState(UIState next)
        {
            if (_state == next) return;
            ApplyState(next);
        }

        private void ApplyState(UIState next)
        {
            _state = next;
            bool exploring = next == UIState.Exploration;
            ToggleLayer(explorationHud, exploring);
            ToggleLayer(encounterOverlay, !exploring);
            OnStateChanged?.Invoke(next);
        }

        /// <summary>Show/hide a CanvasGroup layer. Safe when the reference is unassigned.</summary>
        private static void ToggleLayer(CanvasGroup group, bool visible)
        {
            if (group == null) return;
            group.alpha = visible ? 1f : 0f;
            group.interactable = visible;
            group.blocksRaycasts = visible;
        }

        /// <summary>Append a line to the feed, trim to capacity, and notify listeners.</summary>
        public void AppendFeed(string line)
        {
            if (string.IsNullOrEmpty(line)) return;
            _feed.Add(line);
            if (_feed.Count > maxFeedEntries)
                _feed.RemoveAt(0);
            OnFeedEntryAdded?.Invoke(line);
        }
    }
}
