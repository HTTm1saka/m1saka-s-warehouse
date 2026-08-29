# 🤖 AI 模拟交易系统

定时自动拉取币安现货行情 → 大模型分析并给出交易决策 → 模拟市价成交 → 网页面板实时呈现。
初始资金 **10 万美元**,全程模拟,不涉及真实资金。决策间隔在 `config.json` 的 `cycle_seconds` 中配置(当前:每 1 分钟)。

## 快速开始

```bash
python app.py
```

浏览器打开 **http://127.0.0.1:8000**

> 未配置大模型 API key 时,系统自动进入**演示模式**(内置规则模拟决策),开箱即可看到完整流程。
> 填好 key 重启后,即切换为真正的 AI 决策。

## 接入 AI(以 DeepSeek 为例)

1. 到 [platform.deepseek.com](https://platform.deepseek.com) 注册并创建 API key
2. 打开 `config.json`,填入:

```json
"llm": {
  "provider": "deepseek",
  "api_key": "sk-你的key",
  "model": "deepseek-chat",
  "base_url": "https://api.deepseek.com"
}
```

3. 重启 `python app.py` 即可

### 支持的提供商(改 config.json 即切换)

| provider | model 示例 | 说明 |
|---|---|---|
| `deepseek` | `deepseek-chat` | 国内可用,价格便宜(默认) |
| `openai` | `gpt-4o` | base_url 填 `https://api.openai.com/v1` |
| `anthropic` | `claude-opus-5` | 官方 SDK 调用,自带服务端回退保护 |
| `ollama` | `qwen2.5:7b` | 本地免费,默认地址 `http://localhost:11434` |
| `mock` | — | 内置规则演示,不需要网络和 key |

## AI 交易提示词

`trader_prompt.txt` 是发给大模型的系统提示词,包含角色设定、风控规则(单笔≤50%现金、保留10%现金、禁止做空、避免频繁换手等)和严格的 JSON 输出格式。直接编辑该文件即可调整策略,修改后下一个决策周期自动生效,无需重启。

## REST API(预留接口)

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/state` | 账户、持仓、价格、最新决策、交易记录全量状态 |
| POST | `/api/trigger` | 手动触发一轮 AI 决策(与定时循环互斥) |
| POST | `/api/trade` | 手动模拟下单,body: `{"symbol":"BTC/USDT","side":"buy","percent":10}` |
| POST | `/api/reset` | 重置账户,body: `{"confirm": true}` |
| GET | `/api/trades` | 最近 100 条成交 |
| GET | `/api/decisions` | 最近 50 条 AI 决策 |

示例:

```bash
curl http://127.0.0.1:8000/api/state
curl -X POST http://127.0.0.1:8000/api/trigger
```

## 接真实交易所的预留设计

- `app.py` 中 `execute_order()` 的语义与 ccxt 的 `create_order()` 一一对应(市价单、手续费、持仓均价),未来接实盘时只需把该函数内部替换为 `exchange.create_order(...)`,并在 config.json 中加入交易所的 apiKey/secret
- `POST /api/trade` 就是外部程序控制下单的入口,实盘后只需改后端实现,接口不变

## 文件说明

| 文件 | 作用 |
|---|---|
| `app.py` | 后端:交易引擎 + 5 分钟决策循环 + REST API |
| `config.json` | 配置:AI 提供商、币种、周期、手续费、初始资金 |
| `trader_prompt.txt` | AI 交易员提示词(可自由修改) |
| `state.json` | 账户状态持久化(自动生成,可删掉重置) |
| `static/index.html` | 网页面板 |

## 风险提示

本项目为学习演示用途。加密货币波动剧烈,AI 决策不构成任何投资建议;
即使将来接入真实交易所,也请先在交易所测试网充分验证,再考虑小额实盘。
