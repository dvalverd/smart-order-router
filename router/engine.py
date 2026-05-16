
import time
import random
from typing import Optional
from .models import Order, Fill, RoutingResult, RoutingStrategy
from .venues import MarketSimulator

try:
    import pricer as cpp
    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False


class RoutingEngine:
  

    def __init__(self, ticker: str = "AAPL", initial_price: float = 185.00):
        self.ticker = ticker
        self.market = MarketSimulator(ticker, initial_price)
        self.order_history: list[RoutingResult] = []
        self._use_cpp = CPP_AVAILABLE

    def route(self, order: Order) -> RoutingResult:

        t0 = time.time()


        arrival_price = self.market.tick()

        if self._use_cpp:
            result = self._route_cpp(order, arrival_price)
        else:
            result = self._route_python(order, arrival_price)

        result.total_latency_us = (time.time() - t0) * 1e6
        self.order_history.append(result)
        return result

    def _route_cpp(self, order: Order, arrival_price: float) -> RoutingResult:

        cpp_quotes = self.market.get_quotes_as_cpp()

        if order.strategy == RoutingStrategy.BEST_PRICE:
            decision = cpp.route_best_price(
                cpp_quotes, order.qty, order.is_buy, arrival_price
            )
        elif order.strategy == RoutingStrategy.SPLIT:
            decision = cpp.route_split(
                cpp_quotes, order.qty, order.is_buy, arrival_price, order.max_venues
            )
        else:

            decision = cpp.route_best_price(
                cpp_quotes, order.qty, order.is_buy, arrival_price
            )

        fills = [
            Fill(
                order_id=order.order_id,
                venue=f.venue,
                fill_price=f.fill_price,
                fill_qty=f.fill_qty,
                gross_cost=f.gross_cost,
                fees=f.fees,
                net_cost=f.net_cost,
                slippage_bps=f.slippage_bps,
                latency_us=f.latency_us,
            )
            for f in decision.fills
        ]

        return RoutingResult(
            order=order,
            fills=fills,
            strategy=decision.strategy,
            arrival_price=arrival_price,
            avg_fill_price=decision.avg_fill_price,
            total_cost=decision.total_cost,
            total_slippage_bps=decision.total_slippage_bps,
            vwap_deviation_bps=decision.vwap_deviation_bps,
            total_latency_us=0.0,
            venues_used=list({f.venue for f in fills}),
        )

    def _route_python(self, order: Order, arrival_price: float) -> RoutingResult:

        quotes = self.market.get_all_quotes()

        quotes.sort(
            key=lambda q: (q.ask + q.fee_per_share) if order.is_buy
                          else (q.bid - q.fee_per_share),
            reverse=not order.is_buy
        )

        fills = []
        remaining = order.qty

        for q in quotes:
            if remaining <= 0:
                break
            avail = q.ask_size if order.is_buy else q.bid_size
            fill_qty = min(remaining, avail)
            if fill_qty <= 0:
                continue

            fill_price = q.ask if order.is_buy else q.bid
            gross = fill_price * fill_qty * (1 if order.is_buy else -1)
            fees = q.fee_per_share * fill_qty
            net = gross + fees
            slippage = ((fill_price - arrival_price) / arrival_price * 10000
                        if order.is_buy
                        else (arrival_price - fill_price) / arrival_price * 10000)

            fills.append(Fill(
                order_id=order.order_id,
                venue=q.venue,
                fill_price=fill_price,
                fill_qty=fill_qty,
                gross_cost=gross,
                fees=fees,
                net_cost=net,
                slippage_bps=slippage,
                latency_us=random.gauss(50, 10),
            ))
            remaining -= fill_qty

            if order.strategy != RoutingStrategy.SPLIT:
                break 

        total_cost = sum(f.net_cost for f in fills)
        total_qty = sum(f.fill_qty for f in fills)
        avg_price = abs(total_cost) / total_qty if total_qty > 0 else 0
        avg_slippage = (
            sum(f.slippage_bps * f.fill_qty for f in fills) / total_qty
            if total_qty > 0 else 0
        )


        total_val = sum((q.ask if order.is_buy else q.bid) *
                        (q.ask_size if order.is_buy else q.bid_size)
                        for q in quotes)
        total_sz = sum(q.ask_size if order.is_buy else q.bid_size for q in quotes)
        vwap = total_val / total_sz if total_sz > 0 else arrival_price
        vwap_dev = ((avg_price - vwap) / vwap * 10000) if vwap > 0 else 0

        return RoutingResult(
            order=order,
            fills=fills,
            strategy=order.strategy.value,
            arrival_price=arrival_price,
            avg_fill_price=avg_price,
            total_cost=total_cost,
            total_slippage_bps=avg_slippage,
            vwap_deviation_bps=vwap_dev,
            total_latency_us=0.0,
            venues_used=list({f.venue for f in fills}),
        )

    def get_nbbo(self) -> dict:

        if self._use_cpp:
            cpp_quotes = self.market.get_quotes_as_cpp()
            nbbo = cpp.compute_nbbo(cpp_quotes)
            return {
                "best_bid": nbbo.best_bid,
                "best_ask": nbbo.best_ask,
                "best_bid_venue": nbbo.best_bid_venue,
                "best_ask_venue": nbbo.best_ask_venue,
                "spread": nbbo.spread(),
                "mid": nbbo.mid(),
            }
        else:
            quotes = self.market.get_all_quotes()
            best_bid = max(quotes, key=lambda q: q.bid)
            best_ask = min(quotes, key=lambda q: q.ask)
            return {
                "best_bid": best_bid.bid,
                "best_ask": best_ask.ask,
                "best_bid_venue": best_bid.venue,
                "best_ask_venue": best_ask.venue,
                "spread": best_ask.ask - best_bid.bid,
                "mid": (best_bid.bid + best_ask.ask) / 2,
            }

    def get_all_quotes(self) -> list[dict]:
        quotes = self.market.get_all_quotes()
        return [
            {
                "venue": q.venue,
                "bid": q.bid,
                "ask": q.ask,
                "bid_size": q.bid_size,
                "ask_size": q.ask_size,
                "fee_per_share": q.fee_per_share,
                "spread": round(q.ask - q.bid, 4),
            }
            for q in quotes
        ]

    @property
    def history(self) -> list[dict]:
        return [r.to_dict() for r in self.order_history]
