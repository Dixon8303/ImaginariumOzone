using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.Quest;

namespace Skybound.UI
{
    /// <summary>
    /// Displays the current quest stage and spawns one button per choice.
    /// Hidden when no quest is active. Opened from the CommandBar "Talk" button.
    /// </summary>
    public class QuestPanel : MonoBehaviour
    {
        [Header("Dependencies")]
        [SerializeField] private QuestManager questManager;

        [Header("UI")]
        [SerializeField] private CanvasGroup      canvasGroup;
        [SerializeField] private TextMeshProUGUI  titleLabel;
        [SerializeField] private TextMeshProUGUI  speakerLabel;
        [SerializeField] private TextMeshProUGUI  bodyLabel;
        [SerializeField] private RectTransform    choiceContainer;
        [SerializeField] private GameObject       choiceButtonPrefab; // optional; we build from scratch if null

        private readonly List<GameObject> _choiceButtons = new List<GameObject>();
        private string _activeQuestId;

        private void Awake() => Hide();

        public void Show(QuestData quest)
        {
            if (quest == null) return;
            _activeQuestId = quest.questId;
            RefreshStage(quest);
            SetVisible(true);
        }

        public void Hide()
        {
            SetVisible(false);
            _activeQuestId = null;
        }

        public bool IsVisible => canvasGroup != null && canvasGroup.alpha > 0f;

        private void RefreshStage(QuestData quest)
        {
            var stage = questManager?.CurrentStage(quest.questId);
            if (stage == null) { Hide(); return; }

            if (titleLabel   != null) titleLabel.text   = quest.questTitle;
            if (speakerLabel != null) speakerLabel.text = stage.speakerName;
            if (bodyLabel    != null) bodyLabel.text    = stage.bodyText;

            // Clear old choice buttons
            foreach (var b in _choiceButtons) Destroy(b);
            _choiceButtons.Clear();

            if (stage.choices == null || stage.choices.Count == 0)
            {
                SpawnChoiceButton("Continue", new Color(0.25f, 0.55f, 0.85f),
                    () => { questManager?.MakeChoice(quest.questId,
                        new QuestChoice { endsQuest = true, outcomeText = "The encounter concludes." }); Hide(); });
                return;
            }

            foreach (var choice in stage.choices)
            {
                var captured = choice;
                SpawnChoiceButton(choice.label, ChoiceColor(choice.factionDelta),
                    () => { questManager?.MakeChoice(quest.questId, captured); Hide(); });
            }
        }

        private void SpawnChoiceButton(string label, Color color, System.Action onClick)
        {
            if (choiceContainer == null) return;

            var go  = new GameObject(label);
            go.transform.SetParent(choiceContainer, false);

            var rt  = go.AddComponent<RectTransform>();
            rt.sizeDelta = new Vector2(0, 48);

            var img = go.AddComponent<Image>();
            img.color = color;

            var btn = go.AddComponent<Button>();
            btn.targetGraphic = img;
            btn.onClick.AddListener(() => onClick?.Invoke());

            var lgo = new GameObject("Label");
            lgo.transform.SetParent(go.transform, false);
            var lrt = lgo.AddComponent<RectTransform>();
            lrt.anchorMin = Vector2.zero;
            lrt.anchorMax = Vector2.one;
            lrt.offsetMin = lrt.offsetMax = Vector2.zero;
            var tmp = lgo.AddComponent<TextMeshProUGUI>();
            tmp.text      = label;
            tmp.fontSize  = 14;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.color     = Color.white;

            _choiceButtons.Add(go);
        }

        private static Color ChoiceColor(int factionDelta) =>
            factionDelta > 0  ? new Color(0.20f, 0.55f, 0.30f) :  // cooperative — green tint
            factionDelta < 0  ? new Color(0.55f, 0.20f, 0.20f) :  // hostile — red tint
                                new Color(0.25f, 0.35f, 0.55f);    // neutral — slate blue

        private void SetVisible(bool v)
        {
            if (canvasGroup == null) return;
            canvasGroup.alpha          = v ? 1f : 0f;
            canvasGroup.interactable   = v;
            canvasGroup.blocksRaycasts = v;
        }
    }
}
