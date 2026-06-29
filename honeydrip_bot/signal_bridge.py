"""
Honey Drip signal bridge — stub for Phase 2 implementation.

This module will house the Honey Drip methodology signal generation logic.
During Phase 1, it returns an empty list so the engine runs end-to-end
without producing any trades.

Future implementation should:
- Ingest market data (price, volume, momentum indicators)
- Apply Honey Drip entry/exit criteria
- Return structured signal dicts with at minimum:
  {'ticker': str, 'action': 'buy'|'sell', 'price': float, 'source': str}
"""

from typing import List, Dict, Any


def get_signals() -> List[Dict[str, Any]]:
    # Stub: returns no signals during Phase 1
    # Replace with real Honey Drip logic before Phase 2 activation
    return []
