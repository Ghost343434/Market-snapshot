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


def fmt_signed(p):
    """e.g. +2.63% / -0.82% / +0.00%"""
    return f"{p:+.2f}%"


def fmt_abs(p):
    return f"{abs(p):.2f}%"


def find_by_label(items, label):
    return next((i for i in items if i["label"] == label), None)


def build_theme(indices_data, sector_data, macro_data):
    growth_vals = [s["pct"] for s in sector_data if s["ticker"] in GROWTH]
    def_vals = [s["pct"] for s in sector_data if s["ticker"] in DEFENSIVE]
    val_vals = [s["pct"] for s in sector_data if s["ticker"] in VALUE]
    all_vals = [s["pct"] for s in sector_data]

    g_avg = sum(growth_vals) / len(growth_vals)
    d_avg = sum(def_vals) / len(def_vals)
    v_avg = sum(val_vals) / len(val_vals)
    a_avg = sum(all_vals) / len(all_vals)
    spread = max(all_vals) - min(all_vals)

    ranked = sorted(sector_data, key=lambda s: s["pct"], reverse=True)
    leaders = ranked[:2]
    laggards = ranked[-2:][::-1]  # worst first

    # --- Headline classification ---
    if spread < 1.0 and abs(a_avg) < 0.3:
        title = "Quiet Session"
    elif a_avg > 0.5 and spread < 1.75:
        title = "Broad Rally"
    elif a_avg < -0.5 and spread < 1.75:
        title = "Broad Risk-Off"
    elif g_avg < d_avg - 0.75 and g_avg < v_avg - 0.75:
        title = "Rotation: Growth → Value & Defensives"
    elif g_avg > d_avg + 0.75 and g_avg > v_avg + 0.75:
        title = "Rotation: Value/Defensives → Growth"
    else:
        title = "Mixed / Stock-Picker's Market"

    sp = find_by_label(indices_data, "S&P 500")
    dow = find_by_label(indices_data, "Dow 30")
    nasdaq = find_by_label(indices_data, "Nasdaq Comp")
    rut = find_by_label(indices_data, "Russell 2000")

    vix = find_by_label(macro_data, "VIX")
    gold = find_by_label(macro_data, "Gold (oz)")
    oil = find_by_label(macro_data, "WTI Crude")
    btc = find_by_label(macro_data, "Bitcoin")

    sentences = []

    # 1. Leaders / laggards
    leaders_str = " and ".join(f"{l['name']} ({fmt_signed(l['pct'])})" for l in leaders)
    laggards_str = " and ".join(f"{l['name']} ({fmt_signed(l['pct'])})" for l in laggards)
    sentences.append(f"{leaders_str} led the market today, while {laggards_str} brought up the rear.")

    # 2. Money-flow / style read
    if g_avg < d_avg - 0.5 and g_avg < v_avg - 0.5:
        sentences.append(
            f"That split lines up with a rotation out of growth: growth-oriented sectors averaged "
            f"{fmt_signed(g_avg)} versus {fmt_signed(d_avg)} for defensives and {fmt_signed(v_avg)} for "
            f"value and cyclicals, suggesting money moved from high-multiple names into steadier, "
            f"cash-generative businesses."
        )
    elif g_avg > d_avg + 0.5 and g_avg > v_avg + 0.5:
        sentences.append(
            f"Growth sectors outpaced the rest, averaging {fmt_signed(g_avg)} versus {fmt_signed(d_avg)} "
            f"for defensives and {fmt_signed(v_avg)} for value, consistent with risk appetite favoring "
            f"higher-beta names."
        )
    else:
        sentences.append(
            f"Performance didn't cluster cleanly by style — growth averaged {fmt_signed(g_avg)}, "
            f"defensives {fmt_signed(d_avg)}, and value/cyclicals {fmt_signed(v_avg)} — more a "
            f"stock-by-stock market than a single broad theme."
        )

    # 3. Index breadth
    if sp and dow and nasdaq:
        if dow["pct"] - nasdaq["pct"] > 1.0:
            sentences.append(
                f"That shows up at the index level too: the blue-chip Dow gained {fmt_signed(dow['pct'])} "
                f"while the tech-heavy Nasdaq fell {fmt_signed(nasdaq['pct'])}, a wide enough gap to matter."
            )
        elif nasdaq["pct"] - dow["pct"] > 1.0:
            sentences.append(
                f"That shows up at the index level too: the tech-heavy Nasdaq gained {fmt_signed(nasdaq['pct'])} "
                f"while the blue-chip Dow lagged at {fmt_signed(dow['pct'])}."
            )
        else:
            sentences.append(
                f"Major indices moved in a tighter band — S&P 500 {fmt_signed(sp['pct'])}, "
                f"Dow {fmt_signed(dow['pct'])}, Nasdaq {fmt_signed(nasdaq['pct'])} — without one clearly dominating."
            )

    # 4. Small caps
    if rut and sp:
        if rut["pct"] < sp["pct"] - 0.3:
            sentences.append(
                f"Small caps underperformed as well, with the Russell 2000 at {fmt_signed(rut['pct'])}, "
                f"hinting the move favored large, established balance sheets over smaller, more "
                f"rate-sensitive companies."
            )
        elif rut["pct"] > sp["pct"] + 0.3:
            sentences.append(
                f"Small caps bucked the broader trend, with the Russell 2000 up {fmt_signed(rut['pct'])}, "
                f"outperforming large caps."
            )
        else:
            sentences.append(
                f"Small caps moved roughly in line with the broader market, with the Russell 2000 at "
                f"{fmt_signed(rut['pct'])}."
            )

    # 5. Volatility
    if vix:
        if vix["pct"] < 0:
            sentences.append(
                f"The VIX fell {fmt_abs(vix['pct'])} to {vix['value']}, which reads as an orderly "
                f"rotation rather than panic-driven selling."
            )
        else:
            sentences.append(
                f"The VIX rose {fmt_abs(vix['pct'])} to {vix['value']}, pointing to a bit more caution "
                f"creeping in beneath the surface."
            )

    # 6. Cross-asset
    if gold and oil and btc:
        gold_verb = "added" if gold["pct"] >= 0 else "slipped"
        btc_verb = "gained" if btc["pct"] >= 0 else "slipped"
        sentences.append(
            f"Gold {gold_verb} {fmt_abs(gold['pct'])} to {gold['value']}, crude oil was little changed at "
            f"{oil['value']}, and bitcoin {btc_verb} {fmt_abs(btc['pct'])} — cross-asset moves weren't all "
            f"pointing the same direction as equities."
        )

    return {"title": title, "summary": " ".join(sentences)}


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
    for ticker, name in MACRO:
        val, pct = get_change(ticker)
        macro_data.append({"label": name, "value": fmt_value(ticker, val), "pct": pct})

    theme = build_theme(indices_data, sector_data, macro_data)

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
