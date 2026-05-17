import pandas as pd
from typing import List, Dict, Any


def compare_backtests(
    o3_equity: List[dict],
    o3_trades: List[dict],
    o4_equity: List[dict],
    o4_trades: List[dict],
) -> Dict[str, Any]:
    df3 = pd.DataFrame(o3_equity)
    df4 = pd.DataFrame(o4_equity)

    if df3.empty or df4.empty:
        return {"error": "one or both backtests produced no results"}

    df3["trade_date"] = pd.to_datetime(df3["trade_date"])
    df4["trade_date"] = pd.to_datetime(df4["trade_date"])

    merged = pd.merge(
        df3[["trade_date", "equity"]].rename(columns={"equity": "o3_equity"}),
        df4[["trade_date", "equity"]].rename(columns={"equity": "o4_equity"}),
        on="trade_date",
        how="inner",
    )

    if merged.empty:
        return {"error": "no overlapping dates"}

    merged["diff"] = merged["o4_equity"] - merged["o3_equity"]
    merged["diff_pct"] = (merged["o4_equity"] / merged["o3_equity"] - 1) * 100

    o3_final = df3["equity"].iloc[-1]
    o4_final = df4["equity"].iloc[-1]
    final_diff_pct = (o4_final / o3_final - 1) * 100

    df3t = pd.DataFrame(o3_trades) if o3_trades else pd.DataFrame()
    df4t = pd.DataFrame(o4_trades) if o4_trades else pd.DataFrame()

    o3_trade_count = len(df3t)
    o4_trade_count = len(df4t)

    explanations = []
    if abs(final_diff_pct) > 0.1:
        explanations.append(f"O4 vs O3 final equity differs by {final_diff_pct:.2f}%")
    if o3_trade_count != o4_trade_count:
        explanations.append(
            f"Trade count differs: O3={o3_trade_count}, O4={o4_trade_count} "
            "(event-driven may skip orders due to risk/T+1/lot-size constraints)"
        )
    if not explanations:
        explanations.append("O3 and O4 results are consistent within tolerance.")

    return {
        "o3_final_equity": round(float(o3_final), 2),
        "o4_final_equity": round(float(o4_final), 2),
        "final_diff_pct": round(float(final_diff_pct), 4),
        "o3_trades": o3_trade_count,
        "o4_trades": o4_trade_count,
        "explanations": explanations,
        "max_daily_diff_pct": round(float(merged["diff_pct"].max()), 4),
    }
