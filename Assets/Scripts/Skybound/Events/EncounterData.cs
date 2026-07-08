using UnityEngine;
using Skybound.Core;

namespace Skybound.Events
{
    /// <summary>
    /// Abstract data + behaviour container for a single encounter.
    /// Concrete encounters (Combat, Discovery, Environmental, future Mythic) derive
    /// and override Resolve(). Because resolution is polymorphic, new encounter types
    /// require zero changes to the GameDirector or UIManager.
    /// </summary>
    public abstract class EncounterData : ScriptableObject
    {
        [SerializeField] private string encounterTitle;
        [SerializeField, TextArea] private string introText;

        public string Title => encounterTitle;
        public string IntroText => introText;

        /// <summary>
        /// Resolve this encounter against current ship/crew state and return a loggable outcome.
        /// Implementations should be deterministic given their inputs where possible, to keep
        /// the seeded-procedural design reproducible.
        /// </summary>
        public abstract EventOutcome Resolve(IShipManager ship);
    }
}
