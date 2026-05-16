#include "pricer.h"
#include <algorithm>
#include <numeric>
#include <cmath>
#include <stdexcept>
#include <random>


static std::mt19937 rng(42);

static double sim_latency_us(const std::string& venue) {

    std::map<std::string, std::pair<double, double>> profiles = {
        {"NYSE",    {45.0, 8.0}},
        {"NASDAQ",  {38.0, 6.0}},
        {"BATS",    {32.0, 5.0}},
        {"DARK",    {120.0, 30.0}},
        {"IEX",     {350.0, 20.0}},   
    };
    auto it = profiles.find(venue);
    double mean = (it != profiles.end()) ? it->second.first : 50.0;
    double stddev = (it != profiles.end()) ? it->second.second : 10.0;
    std::normal_distribution<double> dist(mean, stddev);
    return std::max(1.0, dist(rng));
}

NBBO compute_nbbo(const std::vector<Quote>& quotes) {
    if (quotes.empty()) {
        throw std::runtime_error("No quotes to compute_nbbo");
    }

    NBBO nbbo;
    nbbo.best_bid = -1e18;
    nbbo.best_ask = 1e18;

    for (const auto& q : quotes) {
        if (q.bid > nbbo.best_bid && q.bid_size > 0) {
            nbbo.best_bid = q.bid;
            nbbo.best_bid_venue = q.venue;
        }
        if (q.ask < nbbo.best_ask && q.ask_size > 0) {
            nbbo.best_ask = q.ask;
            nbbo.best_ask_venue = q.venue;
        }
    }
    return nbbo;
}

FillResult compute_fill(
    const Quote& quote,
    int qty,
    bool is_buy,
    double arrival_price
) {
    FillResult fill;
    fill.venue = quote.venue;
    fill.fill_qty = qty;

    fill.fill_price = is_buy ? quote.ask : quote.bid;

    fill.gross_cost = fill.fill_price * qty * (is_buy ? 1.0 : -1.0);

    fill.fees = quote.fee_per_share * qty;

    fill.net_cost = fill.gross_cost + fill.fees;

    if (arrival_price > 0) {
        double price_diff = is_buy
            ? (fill.fill_price - arrival_price)
            : (arrival_price - fill.fill_price);
        fill.slippage_bps = (price_diff / arrival_price) * 10000.0;
    } else {
        fill.slippage_bps = 0.0;
    }

    fill.latency_us = sim_latency_us(quote.venue);
    return fill;
}

RoutingDecision route_best_price(
    const std::vector<Quote>& quotes,
    int qty,
    bool is_buy,
    double arrival_price
) {
    if (quotes.empty()) {
        throw std::runtime_error("No quotes provided");
    }


    std::vector<size_t> idx(quotes.size());
    std::iota(idx.begin(), idx.end(), 0);

    std::sort(idx.begin(), idx.end(), [&](size_t a, size_t b) {
        double net_a = is_buy
            ? quotes[a].ask + quotes[a].fee_per_share
            : quotes[a].bid - quotes[a].fee_per_share;
        double net_b = is_buy
            ? quotes[b].ask + quotes[b].fee_per_share
            : quotes[b].bid - quotes[b].fee_per_share;
        return is_buy ? (net_a < net_b) : (net_a > net_b);
    });


    const Quote& best = quotes[idx[0]];
    int available = is_buy ? best.ask_size : best.bid_size;

    RoutingDecision decision;
    decision.strategy = "best_price";

    if (available >= qty) {
    
        FillResult fill = compute_fill(best, qty, is_buy, arrival_price);
        decision.fills.push_back(fill);
    } else {

        int remaining = qty;
        for (size_t i : idx) {
            if (remaining <= 0) break;
            const Quote& q = quotes[i];
            int avail = is_buy ? q.ask_size : q.bid_size;
            int fill_qty = std::min(remaining, avail);
            if (fill_qty > 0) {
                FillResult fill = compute_fill(q, fill_qty, is_buy, arrival_price);
                decision.fills.push_back(fill);
                remaining -= fill_qty;
            }
        }
    }


    double total_cost = 0.0;
    double total_qty = 0.0;
    double total_slippage = 0.0;

    for (const auto& f : decision.fills) {
        total_cost += f.net_cost;
        total_qty += f.fill_qty;
        total_slippage += f.slippage_bps * f.fill_qty;
    }

    decision.total_cost = total_cost;
    decision.avg_fill_price = (total_qty > 0) ? (total_cost / total_qty) : 0.0;
    decision.total_slippage_bps = (total_qty > 0) ? (total_slippage / total_qty) : 0.0;


    double vwap = compute_vwap(quotes, qty, is_buy);
    if (vwap > 0 && total_qty > 0) {
        double avg_price = std::abs(total_cost) / total_qty;
        decision.vwap_deviation_bps = ((avg_price - vwap) / vwap) * 10000.0;
    } else {
        decision.vwap_deviation_bps = 0.0;
    }

    return decision;
}

RoutingDecision route_split(
    const std::vector<Quote>& quotes,
    int qty,
    bool is_buy,
    double arrival_price,
    int max_venues
) {

    std::vector<size_t> idx(quotes.size());
    std::iota(idx.begin(), idx.end(), 0);


    std::sort(idx.begin(), idx.end(), [&](size_t a, size_t b) {
        double net_a = is_buy
            ? quotes[a].ask + quotes[a].fee_per_share
            : quotes[a].bid - quotes[a].fee_per_share;
        double net_b = is_buy
            ? quotes[b].ask + quotes[b].fee_per_share
            : quotes[b].bid - quotes[b].fee_per_share;
        return is_buy ? (net_a < net_b) : (net_a > net_b);
    });


    int n = std::min(max_venues, (int)quotes.size());
    double total_size = 0.0;
    for (int i = 0; i < n; i++) {
        total_size += is_buy ? quotes[idx[i]].ask_size : quotes[idx[i]].bid_size;
    }

    RoutingDecision decision;
    decision.strategy = "split";

    int remaining = qty;
    for (int i = 0; i < n && remaining > 0; i++) {
        const Quote& q = quotes[idx[i]];
        int avail = is_buy ? q.ask_size : q.bid_size;
        double weight = (total_size > 0) ? (avail / total_size) : (1.0 / n);
        int alloc = (i == n - 1)
            ? remaining
            : std::min(remaining, (int)std::round(qty * weight));
        alloc = std::min(alloc, avail);
        if (alloc > 0) {
            decision.fills.push_back(compute_fill(q, alloc, is_buy, arrival_price));
            remaining -= alloc;
        }
    }

   
    double total_cost = 0.0, total_qty = 0.0, total_slippage = 0.0;
    for (const auto& f : decision.fills) {
        total_cost += f.net_cost;
        total_qty += f.fill_qty;
        total_slippage += f.slippage_bps * f.fill_qty;
    }
    decision.total_cost = total_cost;
    decision.avg_fill_price = (total_qty > 0) ? (total_cost / total_qty) : 0.0;
    decision.total_slippage_bps = (total_qty > 0) ? (total_slippage / total_qty) : 0.0;

    double vwap = compute_vwap(quotes, qty, is_buy);
    if (vwap > 0 && total_qty > 0) {
        double avg_price = std::abs(total_cost) / total_qty;
        decision.vwap_deviation_bps = ((avg_price - vwap) / vwap) * 10000.0;
    } else {
        decision.vwap_deviation_bps = 0.0;
    }

    return decision;
}

double compute_vwap(const std::vector<Quote>& quotes, int qty, bool is_buy) {

    double total_value = 0.0;
    double total_size = 0.0;
    for (const auto& q : quotes) {
        double price = is_buy ? q.ask : q.bid;
        double size = is_buy ? q.ask_size : q.bid_size;
        total_value += price * size;
        total_size += size;
    }
    return (total_size > 0) ? (total_value / total_size) : 0.0;
}
