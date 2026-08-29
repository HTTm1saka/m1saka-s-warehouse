import ccxt

# 创建交易所连接(拉行情不需要 API key,免费公开)
exchange = ccxt.binance()

# 获取单个币的最新价格
ticker = exchange.fetch_ticker('BTC/USDT')
print(f"BTC/USDT 最新价: {ticker['last']} USDT")
print(f"  24小时涨跌幅: {ticker['percentage']}%")
print(f"  24小时成交量: {ticker['quoteVolume']} USDT")
print()

# 一次拉多个币
symbols = ['ETH/USDT', 'SOL/USDT', 'DOGE/USDT']
for symbol in symbols:
    t = exchange.fetch_ticker(symbol)
    print(f"{symbol} 最新价: {t['last']} USDT ({t['percentage']}%)")
