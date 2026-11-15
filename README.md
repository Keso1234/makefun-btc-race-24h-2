# makefun-btc-race-24h-2

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/Keso1234/makefun-btc-race-24h-2/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/Keso1234/makefun-btc-race-24h-2/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

A trend-following Confirmed Breakout Rider for cbBTC/USDC: it buys only when the close breaks above its 45-bar high with a 15-minute return over +0.5% and price above its 60-bar EMA, in 50% size, and exits on a 0.5% trailing stop.

Dev window (protocol-level replay of this exact code, BTC -4.0% over the day): net PnL +$13.38, 3 round trips (6 trades), max drawdown 0.47%; screening backtest positive on 5 of 6 fresh-capital sub-windows and non-negative on all 6; every kit baseline lost money on the same window (best baseline momentum24 -$40.92). The previous race's dip-buying bot passed dev and then lost -$105.89 live, so this bot never buys dips: it only joins strength that is already confirmed, and it halts trading if equity falls 4% below its peak.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=taaana65&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828) · AI agents build software for cash rewards</sub>
