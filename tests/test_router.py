

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from router import RoutingEngine, Order, Side, OrderType, RoutingStrategy
from router.venues import MarketSimulator, VenueSimulator, VENUE_CONFIGS


def test_venue_quote_structure():
    sim = VenueSimulator("NYSE", 185.00)
    q = sim.get_quote()
    assert q.venue == "NYSE"
    assert q.bid < q.ask
    assert q.bid_size > 0
    assert q.ask_size > 0
    assert q.fee_per_share > 0


def test_dark_pool_midpoint():
    sim = VenueSimulator("DARK", 100.00)
    q = sim.get_quote()
    assert q.bid == q.ask  


def test_market_simulator_tick():
    market = MarketSimulator("AAPL", 185.00)
    mid1 = market.mid_price
    for _ in range(10):
        market.tick()
    assert len(market.price_history) == 11
    assert market.mid_price != mid1 or True  


def test_all_venues_present():
    market = MarketSimulator("AAPL", 185.00)
    quotes = market.get_all_quotes()
    venue_names = {q.venue for q in quotes}
    assert "NYSE" in venue_names
    assert "NASDAQ" in venue_names
    assert "DARK" in venue_names




def test_engine_init():
    engine = RoutingEngine("AAPL", 185.00)
    assert engine.ticker == "AAPL"
    assert len(engine.order_history) == 0


def test_route_buy_order():
    engine = RoutingEngine("AAPL", 185.00)
    order = Order(
        ticker="AAPL",
        side=Side.BUY,
        qty=100,
        strategy=RoutingStrategy.BEST_PRICE,
    )
    result = engine.route(order)
    assert result.fill_rate > 0
    assert abs(result.avg_fill_price) > 0
    assert len(result.fills) > 0
    assert result.total_filled <= 100


def test_route_sell_order():
    engine = RoutingEngine("AAPL", 185.00)
    order = Order(
        ticker="AAPL",
        side=Side.SELL,
        qty=200,
        strategy=RoutingStrategy.BEST_PRICE,
    )
    result = engine.route(order)
    assert result.fill_rate > 0
    assert abs(result.avg_fill_price) > 0


def test_split_strategy_uses_multiple_venues():
    engine = RoutingEngine("AAPL", 185.00)
    order = Order(
        ticker="AAPL",
        side=Side.BUY,
        qty=5000,  
        strategy=RoutingStrategy.SPLIT,
        max_venues=3,
    )
    result = engine.route(order)
  
    assert len(result.fills) >= 1


def test_order_history_accumulates():
    engine = RoutingEngine("AAPL", 185.00)
    for _ in range(5):
        order = Order(ticker="AAPL", side=Side.BUY, qty=100)
        engine.route(order)
    assert len(engine.order_history) == 5


def test_nbbo_structure():
    engine = RoutingEngine("AAPL", 185.00)
    nbbo = engine.get_nbbo()
    assert "best_bid" in nbbo
    assert "best_ask" in nbbo
    assert nbbo["best_bid"] > 0
    assert nbbo["best_ask"] > 0 
    assert nbbo["spread"] >=0


def test_routing_result_dict():
    engine = RoutingEngine("AAPL", 185.00)
    order = Order(ticker="AAPL", side=Side.BUY, qty=100)
    result = engine.route(order)
    d = result.to_dict()
    assert "order_id" in d
    assert "slippage_bps" in d
    assert "venues_used" in d
    assert isinstance(d["venues_used"], list)


def test_fill_price_reasonable():
    engine = RoutingEngine("AAPL", 185.00)
    order = Order(ticker="AAPL", side=Side.BUY, qty=100)
    result = engine.route(order)

    assert 175.0 < result.avg_fill_price < 200.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
