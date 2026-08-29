# -*- coding: utf-8 -*-
"""
AI 模拟交易系统
- 定时拉取币安行情(间隔由 config.json 的 cycle_seconds 配置),
  调用大模型做交易决策,模拟市价成交
- Flask 提供网页面板 + REST API 接口
- 初始资金 10 万美元,数据持久化在 state.json
"""
import json
import os
import threading
import time
import logging

import requests
import ccxt
from flask import Flask, jsonify, request, send_from_directory

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%H:%M:%S')
log = logging.getLogger('ai-trader')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
STATE_PATH = os.path.join(BASE_DIR, 'state.json')
PROMPT_PATH = os.path.join(BASE_DIR, 'trader_prompt.txt')

# ---------------------------------------------------------------- 配置与状态

_config_cache = {'mtime': 0, 'data': None}

def load_config():
    """加载 config.json(带缓存,文件被修改后自动重载)"""
    mtime = os.path.getmtime(CONFIG_PATH)
    if _config_cache['data'] is None or mtime != _config_cache['mtime']:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _config_cache['data'] = json.load(f)
        _config_cache['mtime'] = mtime
    return _config_cache['data']

def default_state():
    cfg = load_config()
    return {
        'start_cash': cfg['initial_cash'],
        'cash': cfg['initial_cash'],
        'positions': {},          # {symbol: {qty, avg_price}}
        'realized_pnl': 0.0,      # 已实现盈亏(累计)
        'trades': [],             # 成交记录
        'decisions': [],          # AI 决策记录(含未执行的)
        'price_history': [],      # 每个周期的价格快照(画曲线用)
        'last_prices': {},        # 最新价格
        'last_update': '',
        'next_decision_at': 0,
    }

_state_lock = threading.Lock()

def load_state():
    try:
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            s = json.load(f)
        d = default_state()
        d.update(s)
        return d
    except (FileNotFoundError, json.JSONDecodeError):
        return default_state()

def save_state(s):
    with _state_lock:
        with open(STATE_PATH, 'w', encoding='utf-8') as f:
            json.dump(s, f, ensure_ascii=False, indent=2)

STATE = load_state()
SYSTEM_PROMPT = None

def load_prompt():
    global SYSTEM_PROMPT
    mtime = os.path.getmtime(PROMPT_PATH)
    if SYSTEM_PROMPT is None or mtime != getattr(load_prompt, 'mtime', 0):
        with open(PROMPT_PATH, 'r', encoding='utf-8') as f:
            SYSTEM_PROMPT = f.read()
        load_prompt.mtime = mtime
    return SYSTEM_PROMPT

# ---------------------------------------------------------------- 行情获取

exchange = ccxt.binance({'enableRateLimit': True})

def fetch_market():
    """拉取各币种最新价、24h 涨跌幅和 5 分钟 K 线"""
    cfg = load_config()
    market = {'tickers': {}, 'klines': {}, 'time': now_str()}
    for symbol in cfg['symbols']:
        try:
            t = exchange.fetch_ticker(symbol)
            market['tickers'][symbol] = {
                'price': t['last'],
                'change_pct': round(t['percentage'] or 0, 2),
            }
            ohlcv = exchange.fetch_ohlcv(symbol, '5m', limit=20)
            market['klines'][symbol] = [
                [c[0], c[1], c[2], c[3], c[4], c[5]] for c in ohlcv
            ]
        except Exception as e:
            log.warning('拉取 %s 行情失败: %s', symbol, e)
    return market

def now_str():
    return time.strftime('%Y-%m-%d %H:%M:%S')

# ---------------------------------------------------------------- LLM 调用

def call_llm(system_prompt, user_msg):
    """按 config.json 的 provider 调用对应的大模型,返回文本回复"""
    cfg = load_config()
    llm = cfg.get('llm', {})
    provider = llm.get('provider', 'deepseek').lower()
    api_key = llm.get('api_key', '')
    model = llm.get('model', 'deepseek-chat')
    base_url = (llm.get('base_url') or '').rstrip('/')

    # 演示模式:未配置 key 时用内置规则模拟决策,保证系统开箱即用
    if not api_key and provider in ('deepseek', 'openai', 'anthropic'):
        return call_mock(STATE), {'mock': True}
    if provider == 'mock':
        return call_mock(STATE), {'mock': True}

    if provider in ('deepseek', 'openai'):
        url = base_url + '/chat/completions'
        body = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_msg},
            ],
            'temperature': 0.7,
            'max_tokens': 800,
            'response_format': {'type': 'json_object'},
        }
        r = requests.post(url, json=body, timeout=60,
                          headers={'Authorization': 'Bearer ' + api_key})
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], {'mock': False}

    if provider == 'ollama':
        url = (base_url or 'http://localhost:11434') + '/v1/chat/completions'
        body = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_msg},
            ],
        }
        r = requests.post(url, json=body, timeout=120)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'], {'mock': False}

    if provider == 'anthropic':
        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        # 使用 beta 接口 + 默认服务端 fallback:
        # 若安全分类器拒绝请求,会自动改用回退模型重试,而不是直接失败
        resp = client.beta.messages.create(
            model=model or 'claude-opus-5',
            max_tokens=1024,
            betas=['server-side-fallback-2026-07-01'],
            fallbacks='default',
            system=system_prompt,
            messages=[{'role': 'user', 'content': user_msg}],
        )
        if resp.stop_reason == 'refusal':
            raise RuntimeError('模型拒绝响应(refusal)')
        text = ''.join(b.text for b in resp.content if b.type == 'text')
        return text, {'mock': False}

    raise ValueError('未知 provider: ' + provider)

def call_mock(state):
    """演示规则策略:首次决策时用 10% 现金买入第一个币种,之后观望"""
    cfg = load_config()
    first = cfg['symbols'][0]
    if state['positions']:
        return ('{"action": "hold", "symbol": "%s", "percent": 0, '
                '"reason": "演示模式:已有持仓,继续持有观望"}' % first)
    return ('{"action": "buy", "symbol": "%s", "percent": 10, '
            '"reason": "演示模式:按规则建仓,配置 API key 后由 AI 决策"}' % first)

def parse_decision(text, symbols):
    """从模型回复中提取并校验 JSON 决策"""
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        d = json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError('模型回复不是合法 JSON: %s' % e)
    action = str(d.get('action', '')).lower()
    if action not in ('buy', 'sell', 'hold'):
        raise ValueError('action 必须是 buy/sell/hold,收到: %r' % d.get('action'))
    symbol = d.get('symbol', '')
    if symbol not in symbols:
        raise ValueError('symbol 不在可交易列表: %r' % symbol)
    pct = float(d.get('percent', 0))
    pct = max(0.0, min(100.0, pct))
    if action == 'hold':
        pct = 0
    return {'action': action, 'symbol': symbol, 'percent': pct,
            'reason': str(d.get('reason', ''))[:200]}

# ---------------------------------------------------------------- 模拟交易引擎

def execute_order(decision, price, state, reason=''):
    """模拟市价成交。返回成交记录;不满足条件时返回 None 和说明"""
    cfg = load_config()
    fee_rate = cfg['fee_rate']
    min_notional = cfg['min_notional']
    symbol = decision['symbol']
    pct = decision['percent']
    cash = state['cash']
    pos = state['positions'].get(symbol)

    if decision['action'] == 'buy':
        notional = cash * pct / 100.0
        if notional < min_notional:
            return None, '金额 %.2f 低于最小限额 %d,放弃买入' % (notional, min_notional)
        fee = notional * fee_rate
        if notional + fee > cash:
            notional = cash / (1 + fee_rate)
            fee = notional * fee_rate
        qty = notional / price
        old = pos or {'qty': 0, 'avg_price': 0}
        avg = (old['qty'] * old['avg_price'] + qty * price) / (old['qty'] + qty)
        state['positions'][symbol] = {'qty': old['qty'] + qty, 'avg_price': avg}
        state['cash'] -= notional + fee
        trade = {'time': now_str(), 'symbol': symbol, 'side': 'buy', 'qty': round(qty, 8),
                 'price': price, 'value': round(notional, 2), 'fee': round(fee, 4),
                 'reason': reason or decision['reason']}
        return trade, None

    if decision['action'] == 'sell':
        if not pos or pos['qty'] <= 0:
            return None, '没有 %s 的持仓,无法卖出' % symbol
        qty = pos['qty'] * pct / 100.0
        value = qty * price
        if value < min_notional:
            return None, '卖出金额 %.2f 低于最小限额 %d,放弃卖出' % (value, min_notional)
        fee = value * fee_rate
        state['realized_pnl'] += (price - pos['avg_price']) * qty - fee
        state['cash'] += value - fee
        remain = pos['qty'] - qty
        if remain < 1e-8:
            state['positions'].pop(symbol, None)
        else:
            state['positions'][symbol] = {'qty': remain, 'avg_price': pos['avg_price']}
        trade = {'time': now_str(), 'symbol': symbol, 'side': 'sell', 'qty': round(qty, 8),
                 'price': price, 'value': round(value, 2), 'fee': round(fee, 4),
                 'reason': reason or decision['reason']}
        return trade, None

    return None, None  # hold

# ---------------------------------------------------------------- 决策循环

cycle_lock = threading.Lock()
stop_event = threading.Event()

def build_context(market):
    """把市场快照 + 账户状态组装成给 AI 的 JSON 输入"""
    cfg = load_config()
    positions = []
    for sym, p in STATE['positions'].items():
        last = market['tickers'].get(sym, {}).get('price')
        if last:
            positions.append({'symbol': sym, 'qty': round(p['qty'], 8),
                              'avg_price': round(p['avg_price'], 4),
                              'current_price': last,
                              'unrealized_pnl_pct': round((last / p['avg_price'] - 1) * 100, 2)})
    prices = {s: t.get('price') for s, t in market['tickers'].items()}
    total = STATE['cash'] + sum(
        p['qty'] * prices.get(s, 0) for s, p in STATE['positions'].items())
    return {
        '时间': market['time'],
        '账户': {
            '总资产': round(total, 2),
            '可用现金': round(STATE['cash'], 2),
            '持仓': positions,
        },
        '行情': [
            {'symbol': s,
             '最新价': t['price'],
             '24h涨跌幅%': t['change_pct'],
             '5分钟K线_最近20根': market['klines'].get(s, [])}
            for s, t in market['tickers'].items()
        ],
        '最近成交': STATE['trades'][-5:],
        '最近决策': [d for d in STATE['decisions'][-3:] if d.get('action')],
    }

def decision_cycle():
    """一轮完整决策:拉行情 -> 问 AI -> 模拟成交 -> 记录"""
    cfg = load_config()
    log.info('=== 开始新一轮决策 ===')
    try:
        market = fetch_market()
    except Exception as e:
        log.error('行情获取失败: %s', e)
        return {'ok': False, 'error': '行情获取失败: %s' % e}

    # 更新价格快照(即使 AI 出错也记录,用于画曲线)
    prices = {s: t['price'] for s, t in market['tickers'].items()}
    if prices:
        STATE['last_prices'].update(prices)
        STATE['price_history'].append({'time': market['time'], 'prices': prices})
        STATE['price_history'] = STATE['price_history'][-500:]
        STATE['last_update'] = market['time']

    decision = None
    try:
        context = build_context(market)
        user_msg = ('请根据以下市场快照做出交易决策。'
                    '你的回复必须是 json 格式,不要包含其他内容:\n'
                    + json.dumps(context, ensure_ascii=False))
        raw, meta = call_llm(load_prompt(), user_msg)
        decision = parse_decision(raw, cfg['symbols'])
        decision['mock'] = meta.get('mock', False)
        decision['raw_reply'] = raw[:800]
        log.info('AI 决策: %s %s %.0f%% - %s',
                 decision['action'], decision['symbol'],
                 decision['percent'], decision['reason'])
    except Exception as e:
        log.error('AI 决策失败: %s', e)
        rec = {'time': now_str(), 'action': 'error', 'error': str(e)}
        STATE['decisions'].append(rec)
        STATE['decisions'] = STATE['decisions'][-50:]
        save_state(STATE)
        return {'ok': False, 'error': 'AI 决策失败: %s' % e, 'decision': rec}

    # 执行交易
    result = {'ok': True, 'decision': decision, 'trades': []}
    if decision['action'] in ('buy', 'sell'):
        price = market['tickers'].get(decision['symbol'], {}).get('price')
        if price:
            trade, err = execute_order(decision, price, STATE)
            if trade:
                STATE['trades'].append(trade)
                STATE['trades'] = STATE['trades'][-200:]
                result['trades'].append(trade)
                log.info('成交: %s %s %s @ %s',
                         trade['side'], trade['symbol'], trade['qty'], trade['price'])
            else:
                decision['exec_note'] = err
                result['note'] = err
        else:
            result['note'] = '该币种暂无行情,无法成交'

    decision['time'] = now_str()
    decision.pop('raw_reply', None)
    STATE['decisions'].append(decision)
    STATE['decisions'] = STATE['decisions'][-50:]
    STATE['next_decision_at'] = time.time() + cfg['cycle_seconds']
    save_state(STATE)
    return result

def background_loop():
    """后台线程:先跑一轮,之后每 cycle_seconds 秒跑一轮"""
    time.sleep(3)  # 等服务起来再跑第一轮
    while not stop_event.is_set():
        if cycle_lock.acquire(blocking=False):
            try:
                decision_cycle()
            except Exception as e:
                log.error('决策循环异常: %s', e)
            finally:
                cycle_lock.release()
        stop_event.wait(load_config()['cycle_seconds'])

# ---------------------------------------------------------------- Flask 与 REST API

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.json.ensure_ascii = False

def state_payload():
    """组装给前端和外部调用方的完整状态"""
    cfg = load_config()
    llm = cfg.get('llm', {})
    provider = llm.get('provider', 'deepseek')
    mock_mode = provider == 'mock' or not llm.get('api_key')
    positions = []
    for sym, p in STATE['positions'].items():
        last = STATE['last_prices'].get(sym)
        positions.append({
            'symbol': sym, 'qty': p['qty'], 'avg_price': p['avg_price'],
            'price': last,
            'value': (p['qty'] * last) if last else None,
            'pnl_pct': round((last / p['avg_price'] - 1) * 100, 2) if last else None,
        })
    prices = STATE['last_prices']
    total = STATE['cash'] + sum(
        p['qty'] * prices.get(s, 0) for s, p in STATE['positions'].items())
    return {
        'account': {
            'initial': STATE['start_cash'],
            'total': round(total, 2),
            'cash': round(STATE['cash'], 2),
            'position_value': round(total - STATE['cash'], 2),
            'realized_pnl': round(STATE['realized_pnl'], 2),
            'return_pct': round((total / STATE['start_cash'] - 1) * 100, 2),
        },
        'positions': positions,
        'prices': prices,
        'last_update': STATE['last_update'],
        'next_decision_at': STATE['next_decision_at'],
        'cycle_seconds': cfg['cycle_seconds'],
        'symbols': cfg['symbols'],
        'provider': provider,
        'model': llm.get('model'),
        'mock_mode': mock_mode,
        'last_decision': STATE['decisions'][-1] if STATE['decisions'] else None,
        'decisions': list(reversed(STATE['decisions'][-20:])),
        'trades': list(reversed(STATE['trades'][-30:])),
        'price_history': STATE['price_history'][-200:],
    }

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/state')
def api_state():
    return jsonify(state_payload())

@app.route('/api/trigger', methods=['POST'])
def api_trigger():
    """手动触发一轮 AI 决策(与定时循环互斥)"""
    if not cycle_lock.acquire(blocking=False):
        return jsonify({'ok': False, 'error': '已有一轮决策正在进行中'}), 409
    try:
        result = decision_cycle()
        result['state'] = state_payload()
        return jsonify(result), (200 if result['ok'] else 500)
    finally:
        cycle_lock.release()

@app.route('/api/trade', methods=['POST'])
def api_trade():
    """预留接口:外部程序手动下单(模拟)。body: {"symbol","side","percent"}"""
    data = request.get_json(silent=True) or {}
    cfg = load_config()
    symbol = data.get('symbol', '')
    side = str(data.get('side', '')).lower()
    pct = float(data.get('percent', 0))
    if symbol not in cfg['symbols']:
        return jsonify({'ok': False, 'error': 'symbol 不在可交易列表'}), 400
    if side not in ('buy', 'sell'):
        return jsonify({'ok': False, 'error': 'side 必须是 buy 或 sell'}), 400
    pct = max(0.0, min(100.0, pct))
    price = STATE['last_prices'].get(symbol)
    if not price:
        return jsonify({'ok': False, 'error': '暂无该币种行情'}), 400
    with _state_lock:
        trade, err = execute_order(
            {'action': side, 'symbol': symbol, 'percent': pct, 'reason': '手动下单'},
            price, STATE)
    if not trade:
        return jsonify({'ok': False, 'error': err}), 400
    STATE['trades'].append(trade)
    STATE['trades'] = STATE['trades'][-200:]
    save_state(STATE)
    return jsonify({'ok': True, 'trade': trade, 'state': state_payload()})

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """重置账户到初始资金(需要 body 里 confirm: true)"""
    data = request.get_json(silent=True) or {}
    if not data.get('confirm'):
        return jsonify({'ok': False, 'error': '需要 confirm: true 才会重置'}), 400
    global STATE
    with _state_lock:
        STATE = default_state()
        save_state(STATE)
    return jsonify({'ok': True, 'state': state_payload()})

@app.route('/api/trades')
def api_trades():
    return jsonify(STATE['trades'][-100:])

@app.route('/api/decisions')
def api_decisions():
    return jsonify(STATE['decisions'][-50:])

def main():
    cfg = load_config()
    thread = threading.Thread(target=background_loop, daemon=True, name='trader-loop')
    thread.start()
    log.info('AI 模拟交易系统已启动: http://%s:%s', cfg['host'], cfg['port'])
    app.run(host=cfg['host'], port=cfg['port'], debug=False, use_reloader=False)

if __name__ == '__main__':
    main()
