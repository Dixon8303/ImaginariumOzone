import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

// ─── Data ────────────────────────────────────────────────────────────────────

const STATUSES = [
  "Development",
  "First Draft",
  "Revision",
  "Polish",
  "On Submission",
  "Optioned",
  "Produced",
];

const STATUS_META = {
  "Development":   { color: "#F59E0B", bg: "rgba(245,158,11,0.1)"  },
  "First Draft":   { color: "#60A5FA", bg: "rgba(96,165,250,0.1)"  },
  "Revision":      { color: "#A78BFA", bg: "rgba(167,139,250,0.1)" },
  "Polish":        { color: "#34D399", bg: "rgba(52,211,153,0.1)"  },
  "On Submission": { color: "#FB923C", bg: "rgba(251,146,60,0.1)"  },
  "Optioned":      { color: "#FBBF24", bg: "rgba(251,191,36,0.1)"  },
  "Produced":      { color: "#F9FAFB", bg: "rgba(249,250,251,0.1)" },
};

const initialScreenplays = [
  {
    id: "faculty",
    title: "FACULTY",
    status: "Development",
    draftVersion: "v0.1",
    genre: "Drama",
    logline:
      "A group of students discover their professors have been running a decades-long moral experiment — and they are the subjects.",
    festivalHistory: [],
    nextAction: "Complete outline and beat sheet",
  },
  {
    id: "olympus-modern",
    title: "OLYMPUS MODERN",
    status: "Revision",
    draftVersion: "v2.1",
    genre: "Myth / Drama",
    logline:
      "The gods of Olympus relocate to a contemporary city and must navigate modern power structures without losing themselves.",
    festivalHistory: [
      { name: "Sundance Labs", year: 2024, result: "Quarterfinalist" },
    ],
    nextAction: "Address Act II pacing notes from coverage",
  },
  {
    id: "the-cascade",
    title: "The Cascade",
    status: "First Draft",
    draftVersion: "v1.0",
    genre: "Thriller",
    logline:
      "When a climate scientist's data predicts a civilisation-ending event, she must decide who gets to know — and who gets to survive.",
    festivalHistory: [],
    nextAction: "Full table read with writers' room",
  },
  {
    id: "compliant",
    title: "Compliant",
    status: "Polish",
    draftVersion: "v3.2",
    genre: "Corporate Drama",
    logline:
      "An ethics compliance officer at a pharmaceutical company unravels the hierarchy of silence protecting a drug that shouldn't exist.",
    festivalHistory: [
      { name: "Austin Film Festival", year: 2023, result: "Second Rounder" },
      { name: "PAGE Awards", year: 2024, result: "Finalist" },
    ],
    nextAction: "Send to two production companies by April 15",
  },
];

function newBlankScreenplay() {
  return {
    id: crypto.randomUUID(),
    title: "",
    status: "Development",
    draftVersion: "v0.1",
    genre: "",
    logline: "",
    festivalHistory: [],
    nextAction: "",
  };
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function ScreenplayTracker({ onClose }) {
  const [screenplays, setScreenplays] = useState(initialScreenplays);
  const [selectedId, setSelectedId] = useState(null);
  const [isAdding, setIsAdding] = useState(false);

  const selectedScreenplay = screenplays.find((s) => s.id === selectedId) ?? null;
  const modalScreenplay = isAdding ? newBlankScreenplay() : selectedScreenplay;
  const showModal = isAdding || selectedId !== null;

  const handleSave = (updated) => {
    setScreenplays((prev) => {
      const exists = prev.find((s) => s.id === updated.id);
      if (exists) return prev.map((s) => (s.id === updated.id ? updated : s));
      return [...prev, updated];
    });
    setSelectedId(null);
    setIsAdding(false);
  };

  const handleDelete = (id) => {
    setScreenplays((prev) => prev.filter((s) => s.id !== id));
    setSelectedId(null);
  };

  const handleCloseModal = () => {
    setSelectedId(null);
    setIsAdding(false);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      className="w-full min-h-screen text-white overflow-hidden"
      style={{ background: "#0a0a0a" }}
    >
      {/* Grain overlay */}
      <div
        className="fixed inset-0 pointer-events-none"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.04'/%3E%3C/svg%3E\")",
          opacity: 0.4,
        }}
      />

      {/* Top bar */}
      <div className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-white/5">
        <div className="flex items-center gap-4">
          <button
            onClick={onClose}
            className="flex items-center gap-2 text-xs text-white/40 hover:text-white/80 transition-colors"
          >
            <span>←</span>
            <span>Circle</span>
          </button>
          <div className="w-px h-4 bg-white/10" />
          <div>
            <h1 className="text-sm font-semibold tracking-[0.2em] uppercase text-white/90">
              Development Room
            </h1>
            <p className="text-xs text-white/30 tracking-widest mt-0.5">
              Imaginarium Ozone
            </p>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          onClick={() => setIsAdding(true)}
          className="flex items-center gap-2 px-4 py-2 text-xs font-medium rounded border border-white/10 text-white/70 hover:border-white/30 hover:text-white transition-all"
          style={{ background: "rgba(255,255,255,0.03)" }}
        >
          <span className="text-base leading-none">+</span>
          <span>New Screenplay</span>
        </motion.button>
      </div>

      {/* Kanban board */}
      <div className="relative z-10 flex gap-5 overflow-x-auto px-8 py-6 pb-10" style={{ minHeight: "calc(100vh - 80px)" }}>
        {STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            screenplays={screenplays.filter((s) => s.status === status)}
            onSelect={setSelectedId}
          />
        ))}
      </div>

      {/* Modal */}
      <AnimatePresence>
        {showModal && modalScreenplay && (
          <ScreenplayModal
            key={modalScreenplay.id}
            screenplay={isAdding ? { ...newBlankScreenplay() } : selectedScreenplay}
            isNew={isAdding}
            onSave={handleSave}
            onDelete={handleDelete}
            onClose={handleCloseModal}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ─── KanbanColumn ─────────────────────────────────────────────────────────────

function KanbanColumn({ status, screenplays, onSelect }) {
  const meta = STATUS_META[status];

  return (
    <div className="flex-shrink-0 w-64 flex flex-col">
      {/* Column header */}
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full"
            style={{ background: meta.color }}
          />
          <span
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: meta.color }}
          >
            {status}
          </span>
        </div>
        {screenplays.length > 0 && (
          <span
            className="text-xs px-1.5 py-0.5 rounded font-mono"
            style={{ color: meta.color, background: meta.bg }}
          >
            {screenplays.length}
          </span>
        )}
      </div>

      {/* Column divider */}
      <div className="h-px mb-4" style={{ background: meta.color, opacity: 0.2 }} />

      {/* Cards */}
      <motion.div
        className="flex flex-col gap-3"
        variants={{ visible: { transition: { staggerChildren: 0.05 } } }}
        initial="hidden"
        animate="visible"
      >
        {screenplays.map((s) => (
          <ScreenplayCard key={s.id} screenplay={s} onSelect={onSelect} />
        ))}
      </motion.div>
    </div>
  );
}

// ─── ScreenplayCard ───────────────────────────────────────────────────────────

function ScreenplayCard({ screenplay, onSelect }) {
  const meta = STATUS_META[screenplay.status];

  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 16 },
        visible: { opacity: 1, y: 0 },
      }}
      whileHover={{
        scale: 1.02,
        boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
      }}
      onClick={() => onSelect(screenplay.id)}
      className="rounded-xl p-4 cursor-pointer border border-white/5 hover:border-white/10 transition-colors"
      style={{ background: "rgba(255,255,255,0.03)" }}
    >
      {/* Title + version */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h3 className="text-sm font-bold tracking-wide leading-tight text-white/90">
          {screenplay.title}
        </h3>
        <span className="text-xs font-mono text-white/30 flex-shrink-0 mt-0.5">
          {screenplay.draftVersion}
        </span>
      </div>

      {/* Genre */}
      {screenplay.genre && (
        <p className="text-xs text-white/30 uppercase tracking-widest mb-2">
          {screenplay.genre}
        </p>
      )}

      {/* Logline */}
      {screenplay.logline && (
        <p className="text-xs text-white/50 leading-relaxed mb-3 line-clamp-2">
          {screenplay.logline}
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center gap-2 flex-wrap">
        {screenplay.festivalHistory.length > 0 && (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{ color: meta.color, background: meta.bg }}
          >
            {screenplay.festivalHistory.length} festival{screenplay.festivalHistory.length > 1 ? "s" : ""}
          </span>
        )}
        {screenplay.nextAction && (
          <span className="text-xs text-white/25 truncate">
            → {screenplay.nextAction}
          </span>
        )}
      </div>
    </motion.div>
  );
}

// ─── ScreenplayModal ──────────────────────────────────────────────────────────

const EMPTY_FESTIVAL = { name: "", year: new Date().getFullYear(), result: "" };

function ScreenplayModal({ screenplay, isNew, onSave, onDelete, onClose }) {
  const [editing, setEditing] = useState(isNew);
  const [form, setForm] = useState({ ...screenplay });
  const [newFestival, setNewFestival] = useState({ ...EMPTY_FESTIVAL });

  const meta = STATUS_META[form.status] ?? STATUS_META["Development"];

  const setField = (field, value) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const addFestival = () => {
    if (!newFestival.name.trim()) return;
    setField("festivalHistory", [...form.festivalHistory, { ...newFestival }]);
    setNewFestival({ ...EMPTY_FESTIVAL });
  };

  const removeFestival = (i) =>
    setField(
      "festivalHistory",
      form.festivalHistory.filter((_, idx) => idx !== i)
    );

  const handleSave = () => {
    if (!form.title.trim()) return;
    onSave(form);
  };

  return (
    <>
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="fixed inset-0 z-20"
        style={{ background: "rgba(0,0,0,0.75)", backdropFilter: "blur(4px)" }}
      />

      {/* Panel */}
      <motion.div
        initial={{ y: 80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        exit={{ y: 80, opacity: 0 }}
        transition={{ type: "spring", damping: 26, stiffness: 300 }}
        className="fixed left-1/2 top-1/2 z-30 w-full max-w-2xl rounded-2xl border border-white/10 overflow-hidden"
        style={{
          translateX: "-50%",
          translateY: "-50%",
          background: "#111111",
          maxHeight: "90vh",
          overflowY: "auto",
        }}
      >
        {/* Modal header */}
        <div
          className="flex items-center justify-between px-7 py-5 border-b border-white/5"
          style={{ background: meta.bg }}
        >
          <div className="flex items-center gap-3">
            <div
              className="w-2.5 h-2.5 rounded-full"
              style={{ background: meta.color }}
            />
            {editing ? (
              <input
                value={form.title}
                onChange={(e) => setField("title", e.target.value)}
                placeholder="SCREENPLAY TITLE"
                className="bg-transparent text-lg font-bold tracking-wide text-white/90 outline-none placeholder:text-white/20 uppercase w-72"
              />
            ) : (
              <h2 className="text-lg font-bold tracking-wide text-white/90">
                {form.title}
              </h2>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-white/30 hover:text-white/70 transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="px-7 py-6 space-y-6">
          {/* Status + version + genre row */}
          <div className="flex flex-wrap gap-4">
            <Field label="Status">
              {editing ? (
                <select
                  value={form.status}
                  onChange={(e) => setField("status", e.target.value)}
                  className="bg-black/40 border border-white/10 rounded px-3 py-1.5 text-sm text-white/80 outline-none"
                >
                  {STATUSES.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              ) : (
                <span
                  className="inline-flex items-center px-2.5 py-1 rounded text-xs font-semibold"
                  style={{ color: meta.color, background: meta.bg }}
                >
                  {form.status}
                </span>
              )}
            </Field>

            <Field label="Draft Version">
              {editing ? (
                <TextInput
                  value={form.draftVersion}
                  onChange={(v) => setField("draftVersion", v)}
                  placeholder="v1.0"
                  mono
                />
              ) : (
                <span className="text-sm font-mono text-white/60">{form.draftVersion}</span>
              )}
            </Field>

            <Field label="Genre">
              {editing ? (
                <TextInput
                  value={form.genre}
                  onChange={(v) => setField("genre", v)}
                  placeholder="Drama, Thriller…"
                />
              ) : (
                <span className="text-sm text-white/60">{form.genre || "—"}</span>
              )}
            </Field>
          </div>

          {/* Logline */}
          <Field label="Logline">
            {editing ? (
              <textarea
                value={form.logline}
                onChange={(e) => setField("logline", e.target.value)}
                placeholder="The story of…"
                rows={3}
                className="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm text-white/80 outline-none placeholder:text-white/20 resize-none leading-relaxed"
              />
            ) : (
              <p className="text-sm text-white/60 leading-relaxed">
                {form.logline || <span className="text-white/20">No logline yet.</span>}
              </p>
            )}
          </Field>

          {/* Next action */}
          <Field label="Next Action">
            {editing ? (
              <TextInput
                value={form.nextAction}
                onChange={(v) => setField("nextAction", v)}
                placeholder="The single most important next step…"
                wide
              />
            ) : (
              <p className="text-sm text-white/70">
                {form.nextAction
                  ? <><span className="text-white/30">→ </span>{form.nextAction}</>
                  : <span className="text-white/20">No next action set.</span>}
              </p>
            )}
          </Field>

          {/* Festival history */}
          <Field label="Festival History">
            <div className="space-y-2">
              {form.festivalHistory.length === 0 && !editing && (
                <p className="text-sm text-white/20">No submissions yet.</p>
              )}
              {form.festivalHistory.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 px-3 py-2 rounded-lg border border-white/5"
                  style={{ background: "rgba(255,255,255,0.02)" }}
                >
                  <span className="text-sm text-white/70 font-medium">{f.name}</span>
                  <span className="text-xs text-white/30 font-mono">{f.year}</span>
                  <span
                    className="text-xs px-2 py-0.5 rounded-full ml-auto"
                    style={{ color: meta.color, background: meta.bg }}
                  >
                    {f.result}
                  </span>
                  {editing && (
                    <button
                      onClick={() => removeFestival(i)}
                      className="text-white/20 hover:text-red-400 transition-colors text-sm leading-none ml-1"
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}

              {editing && (
                <div className="flex gap-2 mt-2">
                  <input
                    value={newFestival.name}
                    onChange={(e) => setNewFestival((p) => ({ ...p, name: e.target.value }))}
                    placeholder="Festival name"
                    className="flex-1 bg-black/40 border border-white/10 rounded px-3 py-1.5 text-xs text-white/70 outline-none placeholder:text-white/20"
                  />
                  <input
                    type="number"
                    value={newFestival.year}
                    onChange={(e) => setNewFestival((p) => ({ ...p, year: Number(e.target.value) }))}
                    className="w-20 bg-black/40 border border-white/10 rounded px-3 py-1.5 text-xs text-white/70 font-mono outline-none"
                  />
                  <input
                    value={newFestival.result}
                    onChange={(e) => setNewFestival((p) => ({ ...p, result: e.target.value }))}
                    placeholder="Result"
                    className="w-28 bg-black/40 border border-white/10 rounded px-3 py-1.5 text-xs text-white/70 outline-none placeholder:text-white/20"
                  />
                  <button
                    onClick={addFestival}
                    className="px-3 py-1.5 text-xs rounded border border-white/10 text-white/50 hover:text-white hover:border-white/30 transition-all"
                  >
                    Add
                  </button>
                </div>
              )}
            </div>
          </Field>
        </div>

        {/* Footer actions */}
        <div className="flex items-center justify-between px-7 py-4 border-t border-white/5">
          <div>
            {!isNew && !editing && (
              <button
                onClick={() => onDelete(form.id)}
                className="text-xs text-white/20 hover:text-red-400 transition-colors"
              >
                Delete screenplay
              </button>
            )}
          </div>

          <div className="flex gap-3">
            {editing ? (
              <>
                {!isNew && (
                  <button
                    onClick={() => { setEditing(false); setForm({ ...screenplay }); }}
                    className="px-4 py-2 text-xs text-white/40 hover:text-white/70 transition-colors"
                  >
                    Cancel
                  </button>
                )}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  onClick={handleSave}
                  disabled={!form.title.trim()}
                  className="px-5 py-2 text-xs font-semibold rounded-lg text-black transition-opacity disabled:opacity-30"
                  style={{ background: meta.color }}
                >
                  {isNew ? "Add to Slate" : "Save Changes"}
                </motion.button>
              </>
            ) : (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => setEditing(true)}
                className="px-5 py-2 text-xs font-semibold rounded-lg border border-white/10 text-white/70 hover:border-white/30 hover:text-white transition-all"
              >
                Edit
              </motion.button>
            )}
          </div>
        </div>
      </motion.div>
    </>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function Field({ label, children }) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs text-white/25 uppercase tracking-widest">{label}</p>
      {children}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, mono, wide }) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`bg-black/40 border border-white/10 rounded px-3 py-1.5 text-sm text-white/80 outline-none placeholder:text-white/20 ${mono ? "font-mono" : ""} ${wide ? "w-full" : ""}`}
    />
  );
}
