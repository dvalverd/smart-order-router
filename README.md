# Smart Order Router

[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](https://smart-order-router-ilpq.onrender.com)

A production-style smart order router for US equities. Routes orders across simulated NYSE, NASDAQ, BATS, IEX, and dark pool venues to minimize slippage and execution cost. Core routing logic is implemented in C++ and exposed to Python via pybind11.

## Stack

C++17, Python, pybind11, FastAPI, Streamlit, Plotly

## Architecture

```
Client order
    |
    v
Routing Engine (Python)
    |-- NBBO aggregator
    |-- C++ path(pybind11)
    |       |-- NBBO computation
    |       |-- Fee engine
    |       |-- Fill simulation
    |       |-- Slippage calculation
    |
    |-- Venue simulators
    |       |-- NYSE, NASDAQ, BATS (maker/taker fee model)
    |       |-- IEX (350us speed bump)
    |       |-- Dark pool (midpoint fills, hidden liquidity)
    |
    v
Fill result, slippage, VWAP deviation, latency
```

## Routing strategies

- `best_price` — route to venue with best net price after fees
- `split` — split order across top N venues weighted by available size

## Setup

Install dependencies:

```bash
pip3 install -r requirements.txt
```

Build the C++ extension:

```bash
pip3 install -e .
```


## Run

Dashboard:

```bash
python3 -m streamlit run dashboard.py/app.py
```

API server:

```bash
uvicorn api.server:app --reload
```

Tests:

```bash
pytest tests/ -v
```

## API endpoints

```
GET  /nbbo                  current National Best Bid and Offer
GET  /quotes                live quotes from all venues
POST /order                 route an order
POST /order/compare         compare all strategies on one order
GET  /history               order routing history
GET  /history/stats         aggregate statistics
```

## C++ 

The C++ module handles:

- NBBO computation across venues
- Fill price and fee calculation
- Slippage in basis points vs arrival price
- Simulated venue latency with realistic distributions
- Order splitting with proportional allocation

