import pyarrow as pa


AUDIT_FIELDS = [
    pa.field("source", pa.string()),
    pa.field("as_of_date", pa.date32()),
    pa.field("ingested_at", pa.timestamp('us')),
    pa.field("version", pa.string()),
]

TradeCalendarSchema = pa.schema([
    pa.field("trade_date", pa.date32()),
    pa.field("is_open", pa.bool_()),
] + AUDIT_FIELDS)

SecurityMasterSchema = pa.schema([
    pa.field("symbol", pa.string()),
    pa.field("name", pa.string()),
    pa.field("list_date", pa.date32()),
    pa.field("delist_date", pa.date32()),
    pa.field("is_st", pa.bool_()),
    pa.field("industry", pa.string()),
] + AUDIT_FIELDS)

DailyBarSchema = pa.schema([
    pa.field("trade_date", pa.date32()),
    pa.field("symbol", pa.string()),
    pa.field("open", pa.float64()),
    pa.field("high", pa.float64()),
    pa.field("low", pa.float64()),
    pa.field("close", pa.float64()),
    pa.field("volume", pa.float64()),
    pa.field("amount", pa.float64()),
] + AUDIT_FIELDS)

AdjustFactorSchema = pa.schema([
    pa.field("trade_date", pa.date32()),
    pa.field("symbol", pa.string()),
    pa.field("adj_factor", pa.float64()),
] + AUDIT_FIELDS)

LimitPriceSchema = pa.schema([
    pa.field("trade_date", pa.date32()),
    pa.field("symbol", pa.string()),
    pa.field("limit_up", pa.float64()),
    pa.field("limit_down", pa.float64()),
] + AUDIT_FIELDS)

SuspensionSchema = pa.schema([
    pa.field("trade_date", pa.date32()),
    pa.field("symbol", pa.string()),
    pa.field("is_suspended", pa.bool_()),
] + AUDIT_FIELDS)
