import asyncio
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse

from paper_trader import PaperTrader

load_dotenv()

API_KEY = os.getenv('MASSIVE_API_KEY', '').strip()
SMALL_CAP_MAX = float(os.getenv('SMALL_CAP_MAX', '2000000000'))
GAIN_THRESHOLD = float(os.getenv('GAIN_THRESHOLD', '15'))
REFRESH_SECONDS = max(3, int(os.getenv('REFRESH_SECONDS', '10')))
DEMO_MODE = os.getenv('DEMO_MODE', 'true').lower() == 'true'
PAPER_STARTING_CASH = float(os.getenv('PAPER_STARTING_CASH', '1000'))
BASE = 'https://api.massive.com'
STATIC = Path(__file__).parent / 'static'

app = FastAPI(title='Small-Cap Live Scanner')
clients: set[WebSocket] = set()
latest_scan: list[dict[str, Any]] = []
last_scan_at: str | None = None
paper = PaperTrader(starting_cash=PAPER_STARTING_CASH)


def num(x, default=0.0):
    try:
        return float(x)
    except Exception:
        return default


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def score(row):
    pct = num(row.get('change_pct'))
    rvol = max(num(row.get('rvol')), 0)
    price = num(row.get('price'))
    high = num(row.get('day_high'))
    vwap = num(row.get('vwap'))
    catalyst = num(row.get('catalyst_score'), 50)
    momentum = clamp(50 + pct * 1.7)
    volume = clamp(35 + math.log10(rvol + 1) * 38)
    breakout = 85 if high and price >= high * .995 else clamp(40 + (price / high * 45 if high else 0))
    vwap_strength = clamp(50 + ((price / vwap) - 1) * 250) if vwap else 50
    total = round(clamp(.30*momentum + .25*volume + .15*breakout + .15*vwap_strength + .15*catalyst), 1)
    label = 'STRONG BULLISH' if total >= 80 else 'BULLISH' if total >= 68 else 'NEUTRAL' if total >= 52 else 'BEARISH'
    return {'score': total, 'label': label, 'model': 'Momentum Composite', 'components': {'momentum': round(momentum,1), 'relative_volume': round(volume,1), 'breakout': round(breakout,1), 'vwap': round(vwap_strength,1), 'catalyst': round(catalyst,1)}}


async def get_json(client, path, params=None):
    if not API_KEY:
        return None
    params = params or {}
    params['apiKey'] = API_KEY
    try:
        response = await client.get(BASE + path, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def classify(text):
    t = text.lower()
    bullish = ['contract','award','approval','approved','fda','acquisition','partnership','agreement','revenue','guidance','government','order','positive','profit']
    bearish = ['offering','dilution','dilutive','warrant','convertible','bankruptcy','going concern','reverse split']
    b = sum(w in t for w in bullish); br = sum(w in t for w in bearish)
    return ('Bullish', clamp(65 + b*7 - br*12)) if b > br else ('Bearish', clamp(45 + b*5 - br*12)) if br > b else ('Mixed/Unclear', 50)


async def live_scan():
    async with httpx.AsyncClient(headers={'User-Agent':'SmallCapLiveScanner/1.0'}) as client:
        data = await get_json(client, '/v2/snapshot/locale/us/markets/stocks/tickers')
        if not data or not data.get('tickers'):
            return []
        rows=[]
        for t in data['tickers']:
            day=t.get('day') or {}; prev=t.get('prevDay') or {}; last=t.get('lastTrade') or {}
            price=num(last.get('p') or day.get('c')); prev_close=num(prev.get('c'))
            if not price or not prev_close: continue
            pct=(price/prev_close-1)*100
            volume=num(day.get('v')); avg=max(num(prev.get('v')),1); rvol=volume/avg
            cap=num(t.get('marketCap'))
            if pct < GAIN_THRESHOLD: continue
            if cap and cap > SMALL_CAP_MAX: continue
            rows.append({'ticker':t.get('ticker',''),'price':price,'change_pct':pct,'volume':volume,'rvol':rvol,'day_high':num(day.get('h')),'vwap':num(day.get('vw')),'market_cap':cap,'exchange':t.get('exchange','')})
        rows.sort(key=lambda r:r['change_pct'], reverse=True)
        rows=rows[:50]
        async def enrich(r):
            news=await get_json(client,'/v2/reference/news',{'ticker':r['ticker'],'limit':3,'sort':'published_utc','order':'desc'})
            items=(news or {}).get('results') or []
            if items:
                n=items[0]; title=n.get('title',''); kind, cs=classify(title+' '+n.get('description',''))
                r['news']=[{'title':x.get('title',''),'url':x.get('article_url',''),'source':(x.get('publisher') or {}).get('name',''),'published':x.get('published_utc','')} for x in items]
                r['catalyst']=title; r['catalyst_score']=cs; r['catalyst_type']=kind
            else:
                r['news']=[]; r['catalyst']='No recent news found'; r['catalyst_score']=45; r['catalyst_type']='Unknown'
            r['quant']=score(r); r['data_mode']='LIVE'; return r
        return await asyncio.gather(*(enrich(r) for r in rows))


def demo_scan():
    base=[('ABCD',1.24,47.2,14.6,120000000,'Government contract announced'),('XYZZ',3.81,32.8,8.2,480000000,'Regulatory approval announced'),('QWER',2.16,21.4,5.1,210000000,'Strategic partnership announced'),('TEST',.72,16.1,3.8,95000000,'Unusual volume; catalyst unclear')]
    rows=[]
    for ticker,p,pct,rvol,cap,headline in base:
        j=random.uniform(-.7,.7); price=round(p*(1+j/100),4)
        r={'ticker':ticker,'price':price,'change_pct':round(pct+j,2),'volume':int(5_000_000*rvol),'rvol':round(rvol,2),'day_high':round(price*1.01,4),'vwap':round(price*.97,4),'market_cap':cap,'exchange':'NASDAQ','news':[{'title':headline,'url':'','source':'Demo','published':datetime.now(timezone.utc).isoformat()}],'catalyst':headline,'catalyst_score':85,'catalyst_type':'Bullish','data_mode':'DEMO'}
        r['quant']=score(r); rows.append(r)
    return rows


async def broadcast(payload):
    for ws in list(clients):
        try: await ws.send_json(payload)
        except Exception: clients.discard(ws)


async def loop():
    global latest_scan,last_scan_at
    while True:
        rows=await live_scan() if API_KEY else (demo_scan() if DEMO_MODE else [])
        latest_scan=rows; last_scan_at=datetime.now(timezone.utc).isoformat()
        prices={r['ticker']:r['price'] for r in rows}
        paper.mark_to_market(prices)
        await broadcast({'type':'scan','timestamp':last_scan_at,'rows':rows,'mode':'LIVE' if API_KEY else 'DEMO','paper':paper.snapshot(prices)})
        await asyncio.sleep(REFRESH_SECONDS)


@app.on_event('startup')
async def startup():
    asyncio.create_task(loop())


@app.get('/')
async def index(): return FileResponse(STATIC/'index.html')

@app.get('/paper')
async def paper_page(): return FileResponse(STATIC/'paper.html')

@app.get('/health')
async def health(): return {'ok':True,'mode':'LIVE' if API_KEY else 'DEMO','count':len(latest_scan),'updated':last_scan_at,'paper_enabled':paper.enabled}

@app.get('/api/stocks')
async def stocks(): return {'timestamp':last_scan_at,'rows':latest_scan}

@app.get('/api/paper')
async def paper_status():
    prices={r['ticker']:r['price'] for r in latest_scan}
    return paper.snapshot(prices)

@app.post('/api/paper/buy')
async def paper_buy(payload: dict):
    ticker=str(payload.get('ticker','')).upper().strip()
    row=next((r for r in latest_scan if r['ticker']==ticker),None)
    if not row: raise ValueError('Ticker is not in the current scanner universe')
    price=num(payload.get('price'), row['price'])
    stop=num(payload.get('stop'), 0)
    target=payload.get('target')
    target=num(target, 0) if target is not None else None
    if not stop: stop=round(price*0.93,4)
    return paper.open_long(ticker,price,stop,target,num((row.get('quant') or {}).get('score')))

@app.post('/api/paper/sell')
async def paper_sell(payload: dict):
    ticker=str(payload.get('ticker','')).upper().strip()
    row=next((r for r in latest_scan if r['ticker']==ticker),None)
    price=num(payload.get('price'), row['price'] if row else 0)
    if not price: raise ValueError('A current price is required')
    return paper.close(ticker,price,str(payload.get('reason','manual')))

@app.post('/api/paper/reset')
async def paper_reset(payload: dict | None = None):
    cash=num((payload or {}).get('cash'), PAPER_STARTING_CASH)
    paper.reset(cash)
    return paper.snapshot()

@app.post('/api/paper/kill-switch')
async def paper_kill_switch():
    paper.enabled=False
    return {'enabled':False,'message':'Paper trading kill switch activated'}

@app.websocket('/ws')
async def ws(socket:WebSocket):
    await socket.accept(); clients.add(socket)
    prices={r['ticker']:r['price'] for r in latest_scan}
    await socket.send_json({'type':'scan','timestamp':last_scan_at,'rows':latest_scan,'mode':'LIVE' if API_KEY else 'DEMO','paper':paper.snapshot(prices)})
    try:
        while True: await socket.receive_text()
    except Exception: clients.discard(socket)
