using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.Save;

namespace Skybound.UI
{
    /// <summary>
    /// Pause-screen Save/Load panel. Three fixed slots; each shows timestamp
    /// and ship level when occupied. Save overwrites the slot; Load restores it.
    /// Toggled by the GameBootstrap on Escape key.
    /// </summary>
    public class SaveLoadPanel : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private SaveManager saveManager;

        [Header("Slot UI — wire three of each in Inspector")]
        [SerializeField] private TextMeshProUGUI[] slotLabels;   // length 3
        [SerializeField] private Button[]          saveButtons;   // length 3
        [SerializeField] private Button[]          loadButtons;   // length 3
        [SerializeField] private Button            closeButton;

        private CanvasGroup _group;

        private void Awake()
        {
            _group = GetComponent<CanvasGroup>();
            Hide();

            for (int i = 0; i < 3; i++)
            {
                int slot = i;
                if (saveButtons != null && slot < saveButtons.Length && saveButtons[slot] != null)
                    saveButtons[slot].onClick.AddListener(() => OnSave(slot));
                if (loadButtons != null && slot < loadButtons.Length && loadButtons[slot] != null)
                    loadButtons[slot].onClick.AddListener(() => OnLoad(slot));
            }

            if (closeButton != null)
                closeButton.onClick.AddListener(Hide);
        }

        public void Show()
        {
            if (_group == null) return;
            _group.alpha          = 1f;
            _group.interactable   = true;
            _group.blocksRaycasts = true;
            RefreshSlots();
        }

        public void Hide()
        {
            if (_group == null) return;
            _group.alpha          = 0f;
            _group.interactable   = false;
            _group.blocksRaycasts = false;
        }

        public bool IsVisible => _group != null && _group.alpha > 0f;

        private void OnSave(int slot)
        {
            saveManager?.Save(slot);
            RefreshSlots();
        }

        private void OnLoad(int slot)
        {
            saveManager?.Load(slot);
            Hide();
        }

        private void RefreshSlots()
        {
            if (slotLabels == null) return;
            for (int i = 0; i < slotLabels.Length && i < 3; i++)
            {
                if (slotLabels[i] == null) continue;
                var info = saveManager?.GetSlotInfo(i);
                slotLabels[i].text = info != null
                    ? $"Slot {i + 1}  —  {info}"
                    : $"Slot {i + 1}  —  Empty";
            }
        }
    }
}
