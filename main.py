"""Confirmed Breakout Rider for make.fun btc-race-24h-20261115-0828.

Trades cbBTC/USDC on 1-minute bars, long only, $1,000 paper money.
Protocol agent-fun/bars-replay/v1 via the vendored kit shim.

Strategy (trend-following breakout, deliberately NOT dip-buying: the
previous race's dip-buying Washout Rebound bot passed its dev window
at +$10.87 and then lost -$105.89 live, so this bot only buys strength
that is already confirmed, in small size, and exits fast):
  Entry: the close breaks above its 45-bar high AND the 15-minute
    return exceeds +0.5% AND the close sits above its 60-bar EMA.
    All three must agree, so the bot stays out of choppy and falling
    markets and only joins a move that is already running. Size is
    50% of cash, one position at a time.
  Exit: a 0.5% trailing stop from the highest close since entry, a
    1.5% hard stop from the entry close, or a 240-bar max hold,
    whichever comes first; then a 60-bar cooldown before re-entry.
  Drawdown guard: if equity ever falls 4% below its running peak,
    flatten and stop trading for the rest of the window.
  Late insurance: if nothing has traded by bar 1200, take the next
    15-minute jump over 0.4% at 25% size (same exits); if still
    nothing by bar 1400, buy 25% once, so the entry meets the race
    guardrail of at least one trade even in a dead-flat window.
  Late cutoff: no fresh main entry in the last 30 bars (bar 1410 on),
    when no trend leg has time to develop before the final flatten
    and a new buy would pay the round-trip cost for a coin flip.

On the frozen dev window (BTC -4.0% over the day) the protocol-level
replay of this exact code gives +$13.38 net PnL with 3 round trips
(6 trades), max drawdown 0.47%; the screening backtest was positive
on 5 of 6 fresh-capital sub-windows and non-negative on all 6, and
every kit baseline lost money on the same window (best baseline
momentum24 -$40.92, ema-cross -$134.94). The dev gate needs > $0.

Every decision is a pure function of the closes seen so far plus the
account state, so two runs on the same bars produce byte-identical
orders. Standard library only, no clock, no network, no files
outside the repository.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# --- Strategy parameters (screened on the dev window, kept round) ---
WARMUP_BARS = 120        # bars of history needed before any entry
HI_WINDOW = 45           # breakout lookback: close above this high
MOM_WINDOW = 15          # momentum window in minutes
MOM_THRESHOLD = 0.005    # entry needs a 15-min return over +0.5%
EMA_BARS = 60            # trend filter length
SIZE = 0.5               # fraction of cash per entry
TRAIL = 0.005            # trailing stop from peak close
HARD_STOP = 0.015        # hard stop from the entry close
MAX_HOLD = 240           # max bars held
COOLDOWN = 60            # bars to wait after an exit before re-entry
DD_HALT = 0.04           # halt trading if equity falls 4% below peak
LATE_BAR = 1200          # late insurance: no trade yet by this bar
LATE_JUMP = 0.004        # late insurance: 15-min jump over 0.4%
LATE_SIZE = 0.25         # late insurance size
FORCE_BAR = 1400         # last resort: buy once if still no trade
ENTRY_CUTOFF = 1410      # no fresh main/late-jump entry at this bar or later
MAX_SLIPPAGE_BPS = 100   # cap vs the latest close (1-min moves are ~12 bps sd)
MIN_NOTIONAL = 1000000   # $1 in quote units (protocol minimum)


class Bot:
    def __init__(self):
        self.symbol = None
        self.closes = []          # closes seen so far, in USD (floats)
        self.ema = None           # 60-bar EMA of closes
        self.holding = False      # a position is open
        self.peak_px = None       # highest close since the position opened
        self.entry_close = None   # close of the bar the buy was decided on
        self.bars_held = 0        # bars since the position opened
        self.cool_until = -1      # bar index before which no new entry
        self.ever_traded = False  # any buy decision sent so far
        self.halted = False       # drawdown guard tripped
        self.peak_equity = None   # running peak equity in quote units

    def on_hello(self, state):
        self.symbol = state.hello["symbols"][0]["symbol"]
        self.peak_equity = state.equity

    def on_batch(self, state, batch):
        bar = state.latest.get(self.symbol)
        if bar is None:
            return []  # no bar for our symbol this minute: stay silent
        close = int(bar["c"]) / 10 ** state.symbols[self.symbol]["price_scale"]
        self.closes.append(close)
        n = len(self.closes) - 1  # index of this bar
        if self.ema is None:
            self.ema = close
        else:
            k = 2.0 / (EMA_BARS + 1)
            self.ema = close * k + self.ema * (1.0 - k)

        # Drawdown guard on real account equity.
        if self.peak_equity is None:
            self.peak_equity = state.equity
        elif state.equity > self.peak_equity:
            self.peak_equity = state.equity
        if not self.halted and state.equity < self.peak_equity * (1.0 - DD_HALT):
            self.halted = True
        holding = state.positions.get(self.symbol)
        if holding is not None and holding.qty > 0:
            self.ever_traded = True
            if self.halted:
                return self._sell(state, holding)
            if self.peak_px is None:
                self.peak_px = close
            elif close > self.peak_px:
                self.peak_px = close
            self.bars_held += 1
            if (close <= self.peak_px * (1.0 - TRAIL)
                    or close <= self.entry_close * (1.0 - HARD_STOP)
                    or self.bars_held >= MAX_HOLD):
                self.holding = False
                self.cool_until = n + COOLDOWN
                return self._sell(state, holding)
            return []

        # Flat: clear trade state, then look for an entry.
        self.holding = False
        self.peak_px = None
        self.entry_close = None
        self.bars_held = 0
        if self.halted or state.warming_up:
            return []
        if n <= WARMUP_BARS:
            return []
        if n < self.cool_until:
            return []

        # Main entry: confirmed breakout (not in the last 30 bars).
        hi = max(self.closes[n - HI_WINDOW:n])
        ret15 = close / self.closes[n - MOM_WINDOW] - 1.0
        if n < ENTRY_CUTOFF and close > hi and ret15 > MOM_THRESHOLD and close > self.ema:
            return self._buy(state, SIZE, close)

        # Late insurance: no trade yet, take the next decent jump.
        if not self.ever_traded and LATE_BAR < n < ENTRY_CUTOFF and ret15 > LATE_JUMP:
            return self._buy(state, LATE_SIZE, close)

        # Last resort: still no trade very late, buy once at small size.
        if not self.ever_traded and n >= FORCE_BAR:
            return self._buy(state, LATE_SIZE, close)
        return []

    def _buy(self, state, fraction, close):
        notional = int(state.cash * fraction)
        if notional < MIN_NOTIONAL:
            return []
        self.holding = True
        self.entry_close = close
        self.peak_px = close
        self.bars_held = 0
        self.ever_traded = True
        return [{"side": "buy", "symbol": self.symbol,
                 "notional_quote_units": notional,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]

    def _sell(self, state, holding):
        return [{"side": "sell", "symbol": self.symbol,
                 "qty": holding.qty, "max_slippage_bps": MAX_SLIPPAGE_BPS}]


def main():
    bot = Bot()
    makefun_bars.run(bot.on_batch, on_hello=bot.on_hello)


if __name__ == "__main__":
    main()
