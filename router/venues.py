
import random
import time
from dataclasses import dataclass, field
from typing import Optional

try:
    import pricer as cpp
    CPP_AVAILABLE = True
except ImportError:
    CPP_AVAILABLE = False
    print("W-C++ pricer not built.")


VENUE_CONFIGS = {
    "NYSE": {
        "fee_per_share": 0.0030,   
        "rebate_per_share": -0.002, 
        "spread_bps": 2.0,
        "depth_shares": 5000,
        "latency_mean_us": 45,
    },
    "NASDAQ": {
        "fee_per_share": 0.0030,
        "rebate_per_share": -0.0020,
        "spread_bps": 1.8,
        "depth_shares": 8000,
        "latency_mean_us": 38,
    },
    "BATS": {
        "fee_per_share": 0.0028,
        "rebate_per_share": -0.0022,
        "spread_bps": 1.9,
        "depth_shares": 6000,
        "latency_mean_us": 32,
    },
    "IEX": {
        "fee_per_share": 0.0009,   
        "rebate_per_share": 0.0,
        "spread_bps": 2.0,
        "depth_shares": 3000,
        "latency_mean_us": 350,    
    },
    "DARK": {
        "fee_per_share": 0.0010,
        "rebate_per_share": 0.0,
        "spread_bps": 0.0,         
        "depth_shares": 2000,
        "latency_mean_us": 120,
    },
}


@dataclass
class VenueQuote:
    venue: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    fee_per_share: float
    timestamp_us: float = field(default_factory=lambda: time.time() * 1e6)


class VenueSimulator:
    

    def __init__(self, name: str, mid_price: float):
        self.name = name
        self.mid_price = mid_price
        self.config = VENUE_CONFIGS.get(name, VENUE_CONFIGS["NYSE"])
        self._tick = 0.01  

    def get_quote(self, noise_bps: float = 0.5) -> VenueQuote:

        noise = random.gauss(0, self.mid_price * noise_bps / 10000)
        mid = round(self.mid_price + noise, 4)

        spread = self.mid_price * self.config["spread_bps"] / 10000
        half_spread = spread / 2

        if self.name == "DARK":
            bid = ask = round(mid, 4)
        else:
            bid = round(mid - half_spread, 4)
            ask = round(mid + half_spread, 4)


        depth = self.config["depth_shares"]
        bid_size = max(100, int(random.gauss(depth, depth * 0.3)))
        ask_size = max(100, int(random.gauss(depth, depth * 0.3)))

        return VenueQuote(
            venue=self.name,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            fee_per_share=self.config["fee_per_share"],
        )

    def update_mid(self, new_mid: float):
        self.mid_price = new_mid


class MarketSimulator:
  
    def __init__(self, ticker: str, initial_price: float):
        self.ticker = ticker
        self.mid_price = initial_price
        self.venues = {
            name: VenueSimulator(name, initial_price)
            for name in VENUE_CONFIGS
        }
        self._price_history = [initial_price]

    def tick(self, volatility_bps: float = 5.0) -> float:

        drift = random.gauss(0, self.mid_price * volatility_bps / 10000)
        self.mid_price = max(1.0, round(self.mid_price + drift, 4))
        for v in self.venues.values():
            v.update_mid(self.mid_price)
        self._price_history.append(self.mid_price)
        return self.mid_price

    def get_all_quotes(self) -> list[VenueQuote]:
        return [v.get_quote() for v in self.venues.values()]

    def get_quotes_as_cpp(self) -> list:

        if not CPP_AVAILABLE:
            raise RuntimeError("C++ pricer not available")
        cpp_quotes = []
        for vq in self.get_all_quotes():
            q = cpp.Quote()
            q.venue = vq.venue
            q.bid = vq.bid
            q.ask = vq.ask
            q.bid_size = vq.bid_size
            q.ask_size = vq.ask_size
            q.fee_per_share = vq.fee_per_share
            cpp_quotes.append(q)
        return cpp_quotes

    @property
    def price_history(self) -> list[float]:
        return self._price_history
