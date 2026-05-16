

import asyncio
import json
import time
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from router import RoutingEngine, Order, Side, OrderType, RoutingStrategy

app = FastAPI(title="Smart Order Router", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


engine = RoutingEngine(ticker="AAPL", initial_price=185.00)



class OrderRequest(BaseModel):
    ticker: str = "AAPL"
    side: str = "buy"
    qty: int = 100
    order_type: str = "market"
    limit_price: Optional[float] = None
    strategy: str = "best_price"
    max_venues: int = 3


@app.get("/")
def root():
    return {"status": "ok", "service": "Smart Order Router"}


@app.get("/nbbo")
def get_nbbo():
    return engine.get_nbbo()


@app.get("/quotes")
def get_quotes():

    return {"quotes": engine.get_all_quotes(), "ticker": engine.ticker}


@app.post("/order")
def submit_order(req: OrderRequest):
 
    try:
        order = Order(
            ticker=req.ticker,
            side=Side(req.side),
            qty=req.qty,
            order_type=OrderType(req.order_type),
            limit_price=req.limit_price,
            strategy=RoutingStrategy(req.strategy),
            max_venues=req.max_venues,
        )
        result = engine.route(order)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/order/compare")
def compare_strategies(req: OrderRequest):
    
    results = {}
    for strategy in RoutingStrategy:
        order = Order(
            ticker=req.ticker,
            side=Side(req.side),
            qty=req.qty,
            order_type=OrderType(req.order_type),
            strategy=strategy,
            max_venues=req.max_venues,
        )
        result = engine.route(order)
        results[strategy.value] = result.to_dict()
    return {"comparison": results, "ticker": req.ticker}


@app.get("/history")
def get_history(limit: int = 50):

    history = engine.history
    return {"orders": history[-limit:], "total": len(history)}


@app.get("/history/stats")
def get_stats():

    history = engine.history
    if not history:
        return {"message": "No orders yet"}

    import statistics
    slippages = [h["slippage_bps"] for h in history]
    latencies = [h["total_latency_us"] for h in history]

    by_strategy = {}
    for h in history:
        s = h["strategy"]
        by_strategy.setdefault(s, []).append(h["slippage_bps"])

    return {
        "total_orders": len(history),
        "avg_slippage_bps": round(statistics.mean(slippages), 4),
        "median_slippage_bps": round(statistics.median(slippages), 4),
        "avg_latency_us": round(statistics.mean(latencies), 2),
        "by_strategy": {
            s: round(statistics.mean(v), 4)
            for s, v in by_strategy.items()
        },
    }


@app.delete("/history")
def clear_history():
    """Clear order history."""
    engine.order_history.clear()
    return {"message": "History cleared"}


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws/quotes")
async def ws_quotes(websocket: WebSocket):

    await manager.connect(websocket)
    try:
        while True:
            quotes = engine.get_all_quotes()
            nbbo = engine.get_nbbo()
            await websocket.send_json({
                "type": "quotes",
                "quotes": quotes,
                "nbbo": nbbo,
                "timestamp": time.time(),
            })
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.websocket("/ws/orders")
async def ws_orders(websocket: WebSocket):
    
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            try:
                order = Order(
                    ticker=data.get("ticker", "AAPL"),
                    side=Side(data.get("side", "buy")),
                    qty=int(data.get("qty", 100)),
                    strategy=RoutingStrategy(data.get("strategy", "best_price")),
                )
                result = engine.route(order)
                await websocket.send_json({
                    "type": "fill",
                    "result": result.to_dict(),
                })
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
