#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "pricer.h"

namespace py = pybind11;

PYBIND11_MODULE(pricer, m) {
    m.doc() = "Smart order router C++ : NBBO computation, fee engine, fill simulation";

    py::class_<Quote>(m, "Quote")
        .def(py::init<>())
        .def_readwrite("venue",         &Quote::venue)
        .def_readwrite("bid",           &Quote::bid)
        .def_readwrite("ask",           &Quote::ask)
        .def_readwrite("bid_size",      &Quote::bid_size)
        .def_readwrite("ask_size",      &Quote::ask_size)
        .def_readwrite("fee_per_share", &Quote::fee_per_share)
        .def("__repr__", [](const Quote& q) {
            return "<Quote venue=" + q.venue +
                   " bid=" + std::to_string(q.bid) +
                   " ask=" + std::to_string(q.ask) + ">";
        });

    py::class_<NBBO>(m, "NBBO")
        .def(py::init<>())
        .def_readwrite("best_bid",       &NBBO::best_bid)
        .def_readwrite("best_ask",       &NBBO::best_ask)
        .def_readwrite("best_bid_venue", &NBBO::best_bid_venue)
        .def_readwrite("best_ask_venue", &NBBO::best_ask_venue)
        .def("spread", [](const NBBO& n) { return n.best_ask - n.best_bid; })
        .def("mid",    [](const NBBO& n) { return (n.best_ask + n.best_bid) / 2.0; });

    py::class_<FillResult>(m, "FillResult")
        .def(py::init<>())
        .def_readwrite("venue",        &FillResult::venue)
        .def_readwrite("fill_price",   &FillResult::fill_price)
        .def_readwrite("fill_qty",     &FillResult::fill_qty)
        .def_readwrite("gross_cost",   &FillResult::gross_cost)
        .def_readwrite("fees",         &FillResult::fees)
        .def_readwrite("net_cost",     &FillResult::net_cost)
        .def_readwrite("slippage_bps", &FillResult::slippage_bps)
        .def_readwrite("latency_us",   &FillResult::latency_us);

    py::class_<RoutingDecision>(m, "RoutingDecision")
        .def(py::init<>())
        .def_readwrite("strategy",           &RoutingDecision::strategy)
        .def_readwrite("fills",              &RoutingDecision::fills)
        .def_readwrite("total_cost",         &RoutingDecision::total_cost)
        .def_readwrite("avg_fill_price",     &RoutingDecision::avg_fill_price)
        .def_readwrite("total_slippage_bps", &RoutingDecision::total_slippage_bps)
        .def_readwrite("vwap_deviation_bps", &RoutingDecision::vwap_deviation_bps);

    m.def("compute_nbbo",       &compute_nbbo,       "Compute National Best Bid and Offer across venues");
    m.def("compute_fill",       &compute_fill,       "Compute fill result for a single venue");
    m.def("route_best_price",   &route_best_price,   "Route order to best net price venue");
    m.def("route_split",        &route_split,        "Split order across top N venues by size");
    m.def("compute_vwap",       &compute_vwap,       "Compute VWAP across all venues");
}
