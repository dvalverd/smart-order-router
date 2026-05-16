#pragma once
#include <vector>
#include <string>
#include <map>

struct Quote {
    std::string venue;
    double bid;
    double ask;
    int bid_size;
    int ask_size;
    double fee_per_share;   
};

struct NBBO {
    double best_bid;
    double best_ask;
    std::string best_bid_venue;
    std::string best_ask_venue;
};

struct FillResult {
    std::string venue;
    double fill_price;
    int fill_qty;
    double gross_cost;
    double fees;
    double net_cost;
    double slippage_bps;    
    double latency_us;      
};

struct RoutingDecision {
    std::string strategy;
    std::vector<FillResult> fills;
    double total_cost;
    double avg_fill_price;
    double total_slippage_bps;
    double vwap_deviation_bps;
};


NBBO compute_nbbo(const std::vector<Quote>& quotes);

FillResult compute_fill(
    const Quote& quote,
    int qty,
    bool is_buy,
    double arrival_price
);

RoutingDecision route_best_price(
    const std::vector<Quote>& quotes,
    int qty,
    bool is_buy,
    double arrival_price
);

RoutingDecision route_split(
    const std::vector<Quote>& quotes,
    int qty,
    bool is_buy,
    double arrival_price,
    int max_venues
);

double compute_vwap(const std::vector<Quote>& quotes, int qty, bool is_buy);
