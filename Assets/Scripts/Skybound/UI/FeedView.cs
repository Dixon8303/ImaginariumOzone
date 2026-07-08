using UnityEngine;
using UnityEngine.UI;
using TMPro;
using Skybound.Systems;

namespace Skybound.UI
{
    /// <summary>
    /// Scrolling text log. Binds to UIManager.OnFeedEntryAdded and appends lines
    /// to a TMP text block inside a ScrollRect, auto-scrolling to the bottom.
    /// Assign feedText and scrollRect in the inspector; both are required.
    /// </summary>
    public class FeedView : MonoBehaviour
    {
        [SerializeField] private UIManager uiManager;
        [SerializeField] private TextMeshProUGUI feedText;
        [SerializeField] private ScrollRect scrollRect;

        private void OnEnable()
        {
            if (uiManager != null)
                uiManager.OnFeedEntryAdded += AppendLine;

            RebuildFromFeed();
        }

        private void OnDisable()
        {
            if (uiManager != null)
                uiManager.OnFeedEntryAdded -= AppendLine;
        }

        private void AppendLine(string line)
        {
            if (feedText == null) return;
            feedText.text += (feedText.text.Length > 0 ? "\n" : "") + line;

            // Force TMP to recalculate, then resize content rect to fit text height
            // so ScrollRect has something to scroll against
            Canvas.ForceUpdateCanvases();
            feedText.ForceMeshUpdate();

            var contentRect = feedText.GetComponent<RectTransform>();
            if (contentRect != null)
                contentRect.sizeDelta = new Vector2(
                    contentRect.sizeDelta.x,
                    feedText.preferredHeight + 10f);

            if (scrollRect != null)
                scrollRect.verticalNormalizedPosition = 0f;
        }

        private void RebuildFromFeed()
        {
            if (feedText == null || uiManager == null) return;
            feedText.text = string.Join("\n", uiManager.Feed);
        }
    }
}
