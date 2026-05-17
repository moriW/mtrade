import sys
from datetime import date
from qtrade.data.collectors.akshare_provider import AkShareProvider
from qtrade.core.log import setup_logging

def main():
    setup_logging(level="INFO")
    provider = AkShareProvider()
    
    symbol = "000001.SZ"
    start_date = date(2023, 1, 1)
    end_date = date(2023, 12, 31)
    
    print(f"Fetching historical daily bars for {symbol} from {start_date} to {end_date}...")
    df = provider.get_daily_bars(symbol, start_date, end_date)
    
    if not df.empty:
        print(f"\nSuccessfully fetched {len(df)} rows.")
        print(df.head())
        print("\nAudit fields appended automatically:")
        print(df[["trade_date", "source", "as_of_date", "ingested_at", "version"]].head())
    else:
        print("No data found or fetch failed.")

if __name__ == "__main__":
    main()
