from datetime import date
from qtrade.core import (
    Bar,
    Signal,
    Order,
    OrderDirection,
    OrderType,
    OrderStatus,
    init_config,
    get_logger,
)


def test_core_types_bar():
    bar = Bar(
        trade_date=date(2026, 5, 15),
        symbol="000001.SZ",
        open=10.0,
        high=10.5,
        low=9.8,
        close=10.2,
        volume=100000,
        amount=1020000,
    )
    assert bar.symbol == "000001.SZ"
    assert bar.close == 10.2
    assert bar.adj_factor == 1.0


def test_core_types_signal_order():
    signal = Signal(
        trade_date=date(2026, 5, 15),
        symbol="000001.SZ",
        score=0.8,
        direction=OrderDirection.LONG,
    )
    assert signal.direction == OrderDirection.LONG

    order = Order(
        order_id="ord_001",
        symbol="000001.SZ",
        trade_date=date(2026, 5, 15),
        direction=OrderDirection.LONG,
        order_type=OrderType.LIMIT,
        price=10.2,
        volume=100,
    )
    assert order.status == OrderStatus.NEW
    assert order.volume == 100


def test_config_loading(tmp_path):
    toml_content = """
env = "paper"

[data]
raw_dir = "/tmp/raw"
clean_dir = "/tmp/clean"
feature_dir = "/tmp/feature"

[log]
level = "INFO"
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(toml_content)

    config = init_config(str(config_file))
    assert config.env == "paper"
    assert config.data.raw_dir == "/tmp/raw"


def test_logger():
    logger = get_logger("test")
    assert logger is not None
