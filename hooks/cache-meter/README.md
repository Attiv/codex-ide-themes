# 📊 Codex 用量 Hook：Token、缓存命中与费用估算

这是一个可选的 Codex `Stop` Hook。每次回答结束后，用 Python 读取**本地会话日志**，
显示这次提问内部的模型调用用量。它不是提问次数统计，也不是账户余额查询。

不需要 API Key、不发网络请求、不读取 `auth.json`，也不会增加模型调用。
主题安装器 `./install.sh` 不会安装这个 Hook；请按下面步骤单独安装。

## 显示效果

下面是多次内部调用时的示例，数字不是固定值：

```text
Hook · 📊 Codex 用量（Token，不是提问次数）
    本次提问：内部调用模型 48 次
      输入：5.28M（缓存命中 5.12M，97%；未缓存 157.1K）
      输出：24.2K（含推理 7.3K）
    最近一次模型请求：
      输入：155.5K（缓存命中 154.2K，99%；未缓存 1.3K）
      输出：164
    💰 API 单价估算：未配置 gpt-6-astra 的价格
    模型：gpt-6-astra
```

`Hook ·` 和缩进由客户端呈现；脚本输出的是包含多行 `systemMessage` 的 JSON。
一轮只有一次模型请求时，不重复显示“最近一次模型请求”。

## 环境要求

- 支持 `Stop` / `systemMessage` 的 Codex 客户端。原脚本运行环境为 Codex CLI
  `0.153.2`；其他版本的日志格式可能不同。
- Python 3.9+，仅使用标准库。建议 Python 3.11+，因为日志缺少模型信息时，
  回退读取 `config.toml` 需要标准库 `tomllib`；3.9/3.10 没有该回退能力。
- 以下安装命令面向 macOS、Linux 或 WSL 的 Bash/Zsh。
- 默认配置目录为 `~/.codex`；自定义目录请在启动 Codex 前设置 `CODEX_HOME`，
  安装和运行时使用同一个目录。

## 安装

以下命令均在仓库根目录执行：

```bash
git clone https://github.com/Attiv/codex-ide-themes.git
cd codex-ide-themes
```

### 1. 安装脚本

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
mkdir -p "$codex_home/hooks"
if [ -f "$codex_home/hooks/cache-meter.py" ]; then
  cp -p "$codex_home/hooks/cache-meter.py" \
    "$codex_home/hooks/cache-meter.py.bak-$(date +%Y%m%d-%H%M%S)"
fi
cp hooks/cache-meter/cache-meter.py "$codex_home/hooks/cache-meter.py"
```

### 2. 注册 Stop Hook

编辑 `${CODEX_HOME:-$HOME/.codex}/hooks.json`，参考
[`hooks.example.json`](hooks.example.json) 添加以下配置：

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"${CODEX_HOME:-$HOME/.codex}/hooks/cache-meter.py\"",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**已有 `hooks.json` 时，不要用整个示例覆盖原文件。** 保留其他事件和已有
`Stop` 条目，只追加这个条目。没有该文件时，才可以直接复制示例：

```bash
codex_home="${CODEX_HOME:-$HOME/.codex}"
if [ ! -e "$codex_home/hooks.json" ]; then
  cp hooks/cache-meter/hooks.example.json "$codex_home/hooks.json"
else
  echo "hooks.json 已存在：请备份后手动合并 Stop 条目，不要覆盖。"
fi
```

若之前已注册过同名脚本（可能使用绝对路径），更新原条目即可，不要重复添加。
不要同时在全局配置、项目配置和 `config.toml` 中注册同一个脚本。

### 3. 启用并信任

重新打开 Codex，在 `/hooks` 中检查并信任新增的 Hook。若配置中显式关闭了
Hooks，请在现有 `[features]` 表中改为 `hooks = true`，不要重复创建同名 TOML 表。
官方文档说明了 Hook 信任流程、配置合并和 `Stop` 的 JSON 输出约定：
[OpenAI Hooks 文档](https://learn.chatgpt.com/docs/hooks)。

然后正常提问，等待回答结束即可。脚本没有有效用量时会静默退出。

## 可选：配置费用估算

**不配置价格也能显示 Token 与缓存信息。** 如需估算费用，将
[`prices.example.json`](prices.example.json) 的内容合并到
`${CODEX_HOME:-$HOME/.codex}/hooks/prices.json`：

```json
{
  "models": {
    "gpt-6-astra": {
      "input_per_m": 0.0,
      "output_per_m": 0.0,
      "cache_read_per_m": 0.0,
      "cache_write_per_m": 0.0
    }
  }
}
```

这里的 `0.0` **只是占位符，不是官方价格或免费额度**。请根据实际模型、服务商及
服务等级填写价格，不要照抄其他模型的价格。模型名必须与 Hook 显示的名称一致；
`models` 这一层不能省略。已有价格表时只合并需要的模型，不要覆盖其他配置。

所有字段的单位都是 **美元 / 一百万 Token**：

| 字段 | 含义 |
| --- | --- |
| `input_per_m` | 未缓存输入单价 |
| `output_per_m` | 输出单价，包含推理 Token |
| `cache_read_per_m` | 缓存命中输入单价 |
| `cache_write_per_m` | 缓存写入单价，仅日志提供对应字段时使用 |

估算公式：

```text
未缓存输入 = max(0, 输入 - 缓存命中 - 缓存写入)
美元估算 = (未缓存输入 × 输入单价
          + 缓存命中 × 缓存读取单价
          + 缓存写入 × 缓存写入单价
          + 输出 × 输出单价) / 1,000,000
```

价格缺失或四项全部为零时，显示“未配置价格”。部分字段缺失会按零处理，
所以请填写完整；服务商没有单独的缓存折扣时，应按其实际计费方式填写。
小于 `$0.01` 的金额用毫美元显示，例如 `$2.5m` 表示 `$0.0025`。

这只是本地用量乘单价，**不是账户实扣、ChatGPT 订阅扣费、剩余额度或账单**。
不会自动查询价格。同一轮中更换模型/服务商时，使用最后读取的模型单价可能不准，
不要将该估算用于结算。

## 工作原理与统计口径

1. Codex 在 `Stop` 时通过标准输入传入 JSON。
2. 优先读取 `transcript_path`；没有可读路径时，在 `$CODEX_HOME/sessions` 下
   按 `session_id` 匹配 `rollout-<时间>-<session_id>.jsonl`。
   无法匹配就静默退出，**不会拿其他最新会话的数据凑数**。
3. 顺序扫描 JSONL 的 `turn_context` 和 `event_msg.token_count`。
4. 按最后一个 `turn_id` 汇总 `last_token_usage`。相同 `turn_id` 的多条上下文
   （例如上下文压缩）不会另起一轮；旧日志没有 `turn_id` 时，以每个
   `turn_context` 为边界。
5. `last_token_usage` 是最近一次内部请求；`total_token_usage` 是会话累计，
   不能直接当成本次提问。本脚本不把会话累计显示为本轮用量。
6. `reasoning_output_tokens` 是 `output_tokens` 的明细，不再加一次。
   多次请求的输入可能重复携带上下文，所以一轮输入达到数百万 Token 并不表示
   用户输入了数百万字。缓存百分比是缓存 Token / 输入 Token，不是节省金额比例。
7. 通过 `{"systemMessage": "多行摘要"}` 输出；不返回继续执行或阻止停止的指令。

“内部调用模型次数”按有用量的日志记录计数，不是用户提问次数，也不是完整的 HTTP
请求审计。重复用量事件可能重复计数；未上报用量的重试、子线程请求等不一定覆盖。
脚本统计该会话文件中最后一轮的数据，不合并其他子代理会话，也不是跨线程计费器。

会话日志格式不是稳定的 Hook 接口，升级客户端或更换服务商后请重新核对。
[官方关于 transcript 格式的说明](https://learn.chatgpt.com/docs/hooks#common-input-fields)
也明确提示这一点。脚本逐行读取，不依赖“只读末尾 2 MiB”的截断窗口；
超大日志可能超过配置的 10 秒超时。

## 手动验证与排错

仓库提供了不含真实对话的两次请求样例：

```bash
printf '%s\n' '{"transcript_path":"hooks/cache-meter/example-rollout.jsonl"}' \
  | python3 hooks/cache-meter/cache-meter.py
```

预期为 JSON 输出：本次提问 **2 次**内部请求，输入 **3K**，缓存 **2.4K / 80%**，
未缓存 **600**，输出 **300**（含推理 **70**）。最终示例模型为 `example-model`。

也可以把 `transcript_path` 替换成自己机器上的实际 rollout 文件绝对路径。
请勿把真实对话日志、`config.toml` 或账户凭据提交到仓库。

| 现象 | 检查项 |
| --- | --- |
| 完全不显示 | `/hooks` 是否已信任、Hook 是否启用、客户端是否支持该事件 |
| 报 `python3` 找不到 | 为命令配置本机 Python 的绝对路径 |
| 手动运行正常，自动不显示 | 确认 Codex 的 `CODEX_HOME`、配置位置和 `transcript_path` |
| 显示两遍 | 是否在全局/项目/插件或多个 Stop 条目重复注册 |
| 显示未配置价格 | 模型名是否精确一致、是否包含 `models`、价格是否全零 |
| 没有数据 | 日志未提供 token_count、文件不可读或格式变化时会静默退出 |
| 超时 | 日志过大时可适当调高该 Hook 的 `timeout` |

卸载时，只删除 `hooks.json` 中对应的 `cache-meter.py` 条目，然后删除该脚本。
`prices.json` 如果还被其他工具使用，请保留。不要删除整个 Hooks 配置文件。
