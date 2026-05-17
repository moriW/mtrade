import akshare as ak
import pandas as pd
from datetime import date
from qtrade.data.provider import DataProvider
from qtrade.core.errors import DataError
from qtrade.core.log import get_logger

logger = get_logger("akshare_provider")


class AkShareProvider(DataProvider):
    @property
    def name(self) -> str:
        return "akshare"

    def _add_audit_fields(self, df: pd.DataFrame, as_of_date: date) -> pd.DataFrame:
        if df.empty:
            return df
        df["source"] = self.name
        df["as_of_date"] = pd.to_datetime(as_of_date)
        df["ingested_at"] = pd.Timestamp.now(tz="UTC").tz_localize(None)
        df["version"] = "v1"
        return df

    def get_trade_calendar(self, start_date: date, end_date: date) -> pd.DataFrame:
        try:
            df = ak.tool_trade_date_hist_sina()
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            df = df[
                (df["trade_date"] >= start_date) & (df["trade_date"] <= end_date)
            ].copy()
            df["is_open"] = True

            all_dates = pd.date_range(start=start_date, end=end_date).date
            res_df = pd.DataFrame({"trade_date": all_dates})
            res_df["is_open"] = res_df["trade_date"].isin(df["trade_date"])
            res_df["trade_date"] = pd.to_datetime(res_df["trade_date"])

            return self._add_audit_fields(res_df, end_date)
        except Exception as e:
            logger.error("Failed to fetch trade calendar", error=str(e))
            raise DataError(f"AkShare trade calendar error: {e}")

    def get_security_master(self) -> pd.DataFrame:
        try:
            df = ak.stock_info_a_code_name()
            df = df.rename(columns={"code": "symbol", "name": "name"})

            def format_symbol(code: str) -> str:
                if code.startswith("6"):
                    return f"{code}.SH"
                elif code.startswith("8") or code.startswith("4"):
                    return f"{code}.BJ"
                else:
                    return f"{code}.SZ"

            df["symbol"] = df["symbol"].apply(format_symbol)
            df["list_date"] = pd.NaT
            df["delist_date"] = pd.NaT
            df["is_st"] = df["name"].str.contains("ST")
            df["industry"] = "Unknown"

            return self._add_audit_fields(df, date.today())
        except Exception as e:
            logger.error("Failed to fetch security master", error=str(e))
            raise DataError(f"AkShare security master error: {e}")

    def get_daily_bars(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        try:
            code = symbol.split(".")[0]
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="",
            )
            if df.empty:
                return pd.DataFrame()

            df = df.rename(
                columns={
                    "日期": "trade_date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            df["symbol"] = symbol

            cols = [
                "trade_date",
                "symbol",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
            ]
            return self._add_audit_fields(df[cols], end_date)
        except Exception as e:
            logger.error("Failed to fetch daily bars", symbol=symbol, error=str(e))
            raise DataError(f"AkShare daily bars error: {e}")

    def get_adjust_factors(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        try:
            code = symbol.split(".")[0]
            df_unadj = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="",
            )
            df_qfq = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust="qfq",
            )

            if df_unadj.empty or df_qfq.empty:
                return pd.DataFrame()

            df_unadj = df_unadj.set_index("日期")
            df_qfq = df_qfq.set_index("日期")

            adj_factor = df_qfq["收盘"] / df_unadj["收盘"]

            res = pd.DataFrame(
                {
                    "trade_date": pd.to_datetime(adj_factor.index),
                    "symbol": symbol,
                    "adj_factor": adj_factor.values,
                }
            ).dropna()

            return self._add_audit_fields(res, end_date)
        except Exception as e:
            logger.error("Failed to fetch adjust factors", symbol=symbol, error=str(e))
            raise DataError(f"AkShare adjust factors error: {e}")

    def get_limit_prices(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        df = self.get_daily_bars(symbol, start_date, end_date)
        if df.empty:
            return df

        df["limit_up"] = df["close"].shift(1) * 1.1
        df["limit_down"] = df["close"].shift(1) * 0.9
        return df[
            [
                "trade_date",
                "symbol",
                "limit_up",
                "limit_down",
                "source",
                "as_of_date",
                "ingested_at",
                "version",
            ]
        ]

    def get_suspension_info(
        self, symbol: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        df = self.get_daily_bars(symbol, start_date, end_date)
        cal = self.get_trade_calendar(start_date, end_date)
        cal = cal[cal["is_open"]]

        if df.empty:
            return pd.DataFrame()

        merged = pd.merge(cal, df, on="trade_date", how="left")
        merged["symbol"] = symbol
        merged["is_suspended"] = merged["close"].isna()

        res = merged[["trade_date", "symbol", "is_suspended"]].copy()
        return self._add_audit_fields(res, end_date)
