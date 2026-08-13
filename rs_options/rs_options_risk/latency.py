"""Latency state ladder. Spec §38.

Timestamps are injected by the caller (telemetry engine); this module
never reads a clock. Fail-closed: an uncalibrated monitor reports RED.
"""
from __future__ import annotations

from collections import deque

from .config import LatencyConfig
from .models import LatencySample, LatencyState


def _p95(values: list) -> float:
    if not values:
        return float("inf")
    xs = sorted(values)
    idx = min(len(xs) - 1, max(0, int(round(0.95 * (len(xs) - 1)))))
    return xs[idx]


class LatencyMonitor:
    def __init__(self, cfg: LatencyConfig | None = None):
        self.cfg = cfg or LatencyConfig()
        self._samples: deque = deque(maxlen=self.cfg.window_size)
        self._last_breach_ts: float | None = None   # last time in RED/BLACK

    def record(self, sample: LatencySample) -> None:
        self._samples.append(sample)

    # ------------------------------------------------------------- state
    def raw_state(self) -> LatencyState:
        cfg = self.cfg
        # BLACK dominates everything, calibrated or not (fail closed).
        if self._samples:
            last = self._samples[-1]
            if (last.clock_skew_ms > cfg.clock_skew_black_ms
                    or last.heartbeat_gap_ms > cfg.heartbeat_black_ms):
                return LatencyState.BLACK

        if len(self._samples) < cfg.min_samples:
            return LatencyState.RED          # uncalibrated → no live orders

        last = self._samples[-1]

        p95_age = _p95([s.data_age_ms for s in self._samples])
        p95_rtt = _p95([s.order_rtt_ms for s in self._samples])

        if (p95_age > cfg.data_age_red_ms
                or p95_rtt > cfg.rtt_red_ms
                or last.heartbeat_gap_ms > cfg.heartbeat_red_ms):
            return LatencyState.RED
        if p95_age > cfg.data_age_yellow_ms or p95_rtt > cfg.rtt_yellow_ms:
            return LatencyState.YELLOW
        return LatencyState.GREEN

    def state(self, now: float | None = None) -> LatencyState:
        """Raw state + hysteresis: after RED/BLACK, GREEN is withheld until
        `recovery_seconds` of sustained compliance (spec §38.4)."""
        s = self.raw_state()
        if s in (LatencyState.RED, LatencyState.BLACK):
            if now is not None:
                self._last_breach_ts = now
            return s
        if (s is LatencyState.GREEN
                and now is not None
                and self._last_breach_ts is not None
                and (now - self._last_breach_ts) < self.cfg.recovery_seconds):
            return LatencyState.YELLOW       # degraded until re-arm window passes
        return s

    def pipe_latency_p95_ms(self) -> float | None:
        """End-to-end pipe estimate: p95 data age + p95 order RTT (§38).
        None when uncalibrated — callers must fail closed via the ladder."""
        if len(self._samples) < self.cfg.min_samples:
            return None
        return (_p95([s.data_age_ms for s in self._samples])
                + _p95([s.order_rtt_ms for s in self._samples]))

    @property
    def sample_count(self) -> int:
        return len(self._samples)
