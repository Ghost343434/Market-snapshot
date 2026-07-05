"""
Pulls current index, sector, and macro data and writes it to data.json
at the repo root. Run on a schedule by .github/workflows/update-data.yml.
"""

import json
import datetime
import yfinance as yf

INDICES = [
    ("^GSPC", "S&P 500"),
    ("^DJI", "Dow 30"),
    ("^IXIC", "Nasdaq Comp"),
    ("^RUT", "Russell 2000"),
]

SECTORS = [
    ("XLK", "Technology"),
    ("XLV", "Health Care"),
    ("XLF", "Financials"),
    ("XLY", "Consumer Discretionary"),
    ("XLC", "Communication Svcs"),
    ("XLI", "Industrials"),
    ("XLP", "Consumer Staples"),
    ("XLE", "Energy"),
    ("XLU", "Utilities"),
    ("XLB", "Materials"),
    ("XLRE", "Real Estate"),
]

MACRO = [
    ("^VIX", "VIX"),
    ("GC=F", "Gold (oz)"),
    ("CL=F", "WTI Crude"),
    ("BTC-USD", "Bitcoin"),
]

GROWTH = {"XLK", "XLY", "XLC"}
DEFENSIVE = {"XLP", "XLU", "XLV"}
VALUE = {"XLF", "XLI", "XLE", "XLB", "XLRE"}


def get_change(ticker):
    """Returns (last_price, pct_change_vs_previous_close)."""
    t = yf.Ticker(ticker)
    try:
        fi = t.fast_info
        last = float(fi["last_price"])
        prev = float(fi["previous_close"])
        if not prev:
            raise ValueError("no previous close")
        pct = (last - prev) / prev * 100
        return round(last, 2), round(pct, 2)
    except Exception:
        hist = t.history(period="5d")
        last = float(hist["Close"].iloc[-1])
        prev = float(hist["Close"].iloc[-2])
        pct = (last - prev) / prev * 100
        return round(last, 2), round(pct, 2)


def fmt_value(ticker, val):
    if ticker in ("GC=F", "CL=F", "BTC-USD"):
        return f"${val:,.2f}"
    return f"{val:,.2f}"


def build_theme(sector_data, vix_pct):
    growth_vals = [s["pct"] for s in sector_data if s["ticker"] in GROWTH]
    def_vals = [s["pct"] for s in sector_data if s["ticker"] in DEFENSIVE]
    val_vals = [s["pct"] for s in sector_data if s["ticker"] in VALUE]
    all_vals = [s["pct"] for s in sector_data]

    g_avg = sum(growth_vals) / len(growth_vals)
    d_avg = sum(def_vals) / len(def_vals)
    v_avg = sum(val_vals) / len(val_vals)
    a_avg = sum(all_vals) / len(all_vals)
    spread = max(all_vals) - min(all_vals)

    leaders = sorted(sector_data, key=lambda s: s["pct"], reverse=True)[:2]
    laggards = sorted(sector_data, key=lambda s: s["pct"])[:2]

    if spread < 1.0 and abs(a_avg) < 0.3:
        title = "Quiet Session"
        line = "Sectors traded in a narrow range with no clear leadership."
    elif a_avg > 0.5 and spread < 1.75:
        title = "Broad Rally"
        line = f"Gains were broad-based — {leaders[0]['name']} and {leaders[1]['name']} led a market where nearly every sector was higher."
    elif a_avg < -0.5 and spread < 1.75:
        title = "Broad Risk-Off"
        line = f"Selling was broad-based — {laggards[0]['name']} and {laggards[1]['name']} led declines with few places to hide."
    elif g_avg < d_avg - 0.75 and g_avg < v_avg - 0.75:
        title = "Rotation: Growth → Value & Defensives"
        line = f"{leaders[0]['name']} and {leaders[1]['name']} led while {laggards[0]['name']} and {laggards[1]['name']} lagged."
    elif g_avg > d_avg + 0.75 and g_avg > v_avg + 0.75:
        title = "Rotation: Value/Defensives → Growth"
        line = f"{leaders[0]['name']} and {leaders[1]['name']} led as risk appetite favored growth over defensives."
    else:
        title = "Mixed / Stock-Picker's Market"
        line = f"No clean pattern — {leaders[0]['name']} led while {laggards[0]['name']} lagged, but moves didn't cluster by style."

    if vix_pct <= -3:
        sub = "Volatility fell sharply — consistent with rotation or improving risk appetite, not a selloff."
    elif vix_pct >= 5:
        sub = "Volatility spiked notably — worth treating this as a genuine risk-off move."
    else:
        sub = "Volatility was little changed, consistent with normal day-to-day positioning."

    return {"title": title, "line": line, "subline": sub}


def main():
    indices_data = []
    for ticker, name in INDICES:
        val, pct = get_change(ticker)
        indices_data.append({"label": name, "value": f"{val:,.2f}", "pct": pct})

    sector_data = []
    for ticker, name in SECTORS:
        val, pct = get_change(ticker)
        sector_data.append({"ticker": ticker, "name": name, "pct": pct})
    sector_data.sort(key=lambda s: s["pct"], reverse=True)

    macro_data = []
    vix_pct = 0.0
    for ticker, name in MACRO:
        val, pct = get_change(ticker)
        macro_data.append({"label": name, "value": fmt_value(ticker, val), "pct": pct})
        if ticker == "^VIX":
            vix_pct = pct

    theme = build_theme(sector_data, vix_pct)

    output = {
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "theme": theme,
        "indices": indices_data,
        "sectors": sector_data,
        "macro": macro_data,
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print("Wrote data.json:", output["updated_at"], "-", theme["title"])


if __name__ == "__main__":
    main()
