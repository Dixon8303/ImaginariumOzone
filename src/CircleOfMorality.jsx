import React, { useState, useEffect, useRef } from "react";
import { motion, useMotionValue, useTransform, animate } from "framer-motion";

const segments = [
  { id: "love", virtue: "Love", shadow: "Attachment", opposite: "Control" },
  { id: "discipline", virtue: "Discipline", shadow: "Rigidity", opposite: "Rebellion" },
  { id: "faith", virtue: "Faith", shadow: "Blindness", opposite: "Nihilism" },
  { id: "justice", virtue: "Justice", shadow: "Vengeance", opposite: "Tyranny" },
  { id: "humility", virtue: "Humility", shadow: "Self-Erasure", opposite: "Pride" },
  { id: "freedom", virtue: "Freedom", shadow: "Chaos", opposite: "Bondage" },
  { id: "wisdom", virtue: "Wisdom", shadow: "Overthinking", opposite: "Ignorance" },
  { id: "courage", virtue: "Courage", shadow: "Recklessness", opposite: "Fear" }
];

const normalize = (deg) => ((deg % 360) + 360) % 360;

function getState(angle, index, total) {
  const segAngle = 360 / total;
  const center = index * segAngle;
  const diff = normalize(angle - center);

  if (diff < segAngle * 0.33) return "virtue";
  if (diff < segAngle * 0.66) return "shadow";
  return "opposite";
}

function useSoundEngine(rotation) {
  const audioRef = useRef(null);
  const oscRef = useRef(null);

  useEffect(() => {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = "sine";
    osc.frequency.value = 120;
    gain.gain.value = 0.02;

    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();

    audioRef.current = ctx;
    oscRef.current = { osc, gain };

    return () => {
      osc.stop();
      ctx.close();
    };
  }, []);

  useEffect(() => {
    return rotation.on("change", (v) => {
      if (!oscRef.current) return;
      const norm = normalize(v);
      const freq = 120 + norm * 0.8;
      oscRef.current.osc.frequency.setValueAtTime(freq, audioRef.current.currentTime);

      if (norm > 250 && norm < 290) {
        oscRef.current.gain.gain.setValueAtTime(0.08, audioRef.current.currentTime);
      } else {
        oscRef.current.gain.gain.setValueAtTime(0.02, audioRef.current.currentTime);
      }
    });
  }, [rotation]);
}

export default function CircleOfMorality({ onOpenTracker }) {
  const [active, setActive] = useState(null);
  const [mode, setMode] = useState("explore");
  const [profile, setProfile] = useState({});

  const rotation = useMotionValue(0);
  const bg = useTransform(rotation, [-360, 0, 360], ["#220000", "#000000", "#002222"]);
  const currentAngle = useTransform(rotation, (v) => normalize(v));

  useSoundEngine(rotation);

  useEffect(() => {
    const unsub = rotation.on("change", (v) => {
      const angle = normalize(v);
      const index = Math.floor((angle / 360) * segments.length);
      const key = segments[index].id;

      setProfile((prev) => ({
        ...prev,
        [key]: (prev[key] || 0) + 1
      }));
    });
    return () => unsub();
  }, [rotation]);

  const handleGuide = () => {
    setMode("guide");
    animate(rotation, rotation.get() + 720, { duration: 10, ease: "easeInOut" });
  };

  const handleScenario = () => {
    setMode("scenario");
    animate(rotation, rotation.get() + 360, { duration: 6 });
  };

  const generateProfile = () => {
    const sorted = Object.entries(profile).sort((a, b) => b[1] - a[1]);
    return sorted.slice(0, 3).map(([k]) => k).join(", ");
  };

  return (
    <motion.div style={{ background: bg }} className="w-full h-screen flex items-center justify-center text-white overflow-hidden">

      <div className="absolute top-6 left-6 flex gap-3">
        <button onClick={handleGuide} className="px-4 py-2 bg-white text-black rounded">Guide Me</button>
        <button onClick={handleScenario} className="px-4 py-2 bg-white/20 rounded">Scenario</button>
        {onOpenTracker && (
          <button onClick={onOpenTracker} className="px-4 py-2 bg-white/10 rounded text-white/70 hover:bg-white/20 hover:text-white transition-all text-sm">
            Dev Room
          </button>
        )}
      </div>

      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 40 }).map((_, i) => (
          <motion.div
            key={i}
            className="absolute w-1 h-1 bg-white rounded-full opacity-20"
            animate={{
              x: [0, Math.random() * 800 - 400],
              y: [0, Math.random() * 800 - 400]
            }}
            transition={{ duration: 10 + Math.random() * 10, repeat: Infinity }}
          />
        ))}
      </div>

      <motion.div
        drag="x"
        dragElastic={0.1}
        onDrag={(e, info) => {
          rotation.set(rotation.get() + info.delta.x * 0.4);
        }}
        style={{ rotate: rotation }}
        className="relative w-[520px] h-[520px]"
      >

        {segments.map((seg, i) => {
          const angle = (i / segments.length) * 360;

          return (
            <motion.div
              key={seg.id}
              className="absolute w-32 h-32 flex items-center justify-center rounded-full cursor-pointer text-center text-sm"
              style={{
                top: "50%",
                left: "50%",
                transform: `rotate(${angle}deg) translate(200px) rotate(-${angle}deg)`
              }}
              whileHover={{ scale: 1.2 }}
              onClick={() => setActive(seg)}
            >
              <SegmentLabel seg={seg} index={i} total={segments.length} angle={currentAngle} />
            </motion.div>
          );
        })}

        <div className="absolute inset-0 border border-white/10 rounded-full" />

        <motion.div
          animate={{ scale: [1, 1.2, 1] }}
          transition={{ repeat: Infinity, duration: 3 }}
          className="absolute top-1/2 left-1/2 w-36 h-36 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/10 backdrop-blur flex items-center justify-center text-center text-xs"
        >
          Core Truth
        </motion.div>
      </motion.div>

      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-xs opacity-70">
        Dominant Tendencies: {generateProfile()}
      </div>

      {active && (
        <motion.div
          initial={{ opacity: 0, x: 120 }}
          animate={{ opacity: 1, x: 0 }}
          className="absolute right-10 top-1/2 -translate-y-1/2 w-96 p-6 bg-white/10 backdrop-blur rounded-2xl"
        >
          <h2 className="text-2xl mb-2">{active.virtue}</h2>

          <div className="space-y-3 text-sm">
            <div><strong>Virtue:</strong> Balanced expression.</div>
            <div><strong>Shadow:</strong> {active.shadow}</div>
            <div><strong>Collapse:</strong> {active.opposite}</div>
          </div>

          <button className="mt-6 px-4 py-2 bg-white text-black rounded" onClick={() => setActive(null)}>
            Close
          </button>
        </motion.div>
      )}

    </motion.div>
  );
}

function SegmentLabel({ seg, index, total, angle }) {
  const state = useTransform(angle, (a) => getState(a, index, total));

  const text = useTransform(state, (s) => {
    if (s === "virtue") return seg.virtue;
    if (s === "shadow") return seg.shadow;
    return seg.opposite;
  });

  const color = useTransform(state, (s) => {
    if (s === "virtue") return "#AEEFFF";
    if (s === "shadow") return "#FFB347";
    return "#FF4C4C";
  });

  return (
    <motion.div style={{ color }} className="px-2 py-1 rounded-full border border-white/20 backdrop-blur">
      <motion.span>{text}</motion.span>
    </motion.div>
  );
}
