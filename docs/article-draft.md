> The section below doubles as a ready-to-publish Chinese tech post. Copy it into 掘金 / 知乎 / 小红书 / B 站 as-is, or expand it using the prompt at the end.

### 用纯标准库，亲手写一个 MCP 服务器（零依赖、可读、可测）

**痛点：想给大模型加个"工具"，为什么要装一整个 SDK？**

2024 年底 Model Context Protocol（MCP）把"模型调用外部能力"这件事标准化了。理论上，只要你的程序会说 MCP，任何支持它的客户端（桌面应用、IDE 插件、自研 Agent）都能自动发现并调用你的工具。但现实里，很多人一上手就被劝退：官方或社区的 SDK 往往带一堆依赖、默认异步、还要手写 JSON Schema。对一个只想暴露三五个函数的场景来说，太重了。

其实 MCP 的本质非常简单：**它就是跑在一条流（通常是 stdin/stdout）上的 JSON-RPC 2.0**。理解了这一点，我们完全可以用 Python 标准库，几十行核心代码，自己实现一个能用的 MCP 服务器。

**核心原理：四层就够**

1. **传输层（Transport）**：从 stdin 一行一行读 JSON，往 stdout 写 JSON，每行一条消息（`\n` 分隔）。测试时用一个内存队列对（`InMemoryTransport`）就能在进程内跑通整条链路。
2. **协议层（Protocol）**：解析 JSON-RPC 2.0。`{"jsonrpc":"2.0","id":1,"method":"…","params":{…}}` 是请求；没有 `id` 的是通知（不需要回复）；回复分成功 `result` 和错误 `error` 两种。错误的 `code` 走标准区间（-32700 解析错、-32601 方法不存在、-32602 参数错、-32603 内部错）。
3. **模式生成（Schema）**：这是最爽的一点。用 `inspect` 读取函数签名和类型注解，自动生成工具需要的 `inputSchema`——`int→integer`、`str→string`、`list[T]→array`、`Optional[T]→可空`、`Literal[...]→枚举`，有默认值的参数自动标记为"可选"。**再也不用手写 JSON Schema，且永远和代码同步。**
4. **服务层（Server）**：负责握手与分发。`initialize` 做协议版本协商并返回能力声明（`capabilities`）；客户端回一个 `notifications/initialized` 通知（无回复）；之后 `tools/list`、`tools/call`、`resources/read`、`prompts/get` 各司其职。工具执行抛异常时，按规范把它包成 `isError: true` 的结果返回，而不是让整个协议崩掉。

**关键实现点（面试常问）**

- **协议版本协商**：服务器声明自己支持的版本列表（如 `["2024-11-05","2025-03-26"]`），客户端在 `initialize` 里带上它想用的版本；能匹配就匹配，匹配不上就回最新版。这是很多"连不上"问题的根源。
- **通知 vs 请求**：有没有 `id` 决定要不要回消息。漏回或错回都会让客户端卡死——本文的死循环 bug 正是这么来的（把"写"和"读"用到了同一侧队列上）。
- **工具错误是结果不是异常**：`tools/call` 里工具抛错，应该返回 `isError:true` 的结果对象，让模型拿到错误信息自行决策，而不是返回 JSON-RPC 错误码。
- **零依赖的价值**：纯标准库意味着可移植、可审计、无供应链风险，也方便直接 vendoring 进任意项目。

**和"手写裸 JSON-RPC" / "重型 SDK" 的对比**

| 方案 | 依赖 | 写工具的成本 | 可测试性 | 可读性 |
|------|------|------------|---------|--------|
| 裸手写 JSON-RPC | 0 | 每工具手写 schema + 分发分支，易错 | 低（要起进程） | 低 |
| 社区重型 SDK | 多 | 低，但被迫接受其运行时/异步模型 | 中 | 中（要读源码） |
| **Sage（本文）** | **0** | **装饰器 + 自动 schema** | **高（内存传输单测）** | **高（全标准库）** |

**如何扩展成一个真实项目**

- 把 `calculate` / `echo` 换成你的真实能力：查数据库、调内部 API、读本地文件。
- 给工具加 `resources`（如把一份知识库文档挂到 `app://kb`）和 `prompts`（如"按模板总结用户问题"）。
- 接一个真实 LLM 客户端在另一端驱动它，就是一个最小可用的 Agent 工具箱。
- 想要更稳，补上 Roadmap 里的日志追踪和流式输出。

> **📝 如何把本文扩展成一篇发布稿**：保留上面的"痛点→原理→实现点→对比→扩展"五段骨架；开头加一段 2–3 句的"我为什么做这个"钩子（比如"为了搞懂 MCP，我没装任何 SDK，用标准库撸了一个"）；结尾抛一个互动问题（"你第一个想暴露给大模型的能力是什么？"）；配一张本文的架构图（ASCII 即可，或导出成图）；加上 GitHub 链接和标签 `#MCP #LLM #Python #AI工程`。发布时标题用"为什么/如何"句式更容易被搜到。

## 🤝 Contributing

Contributions are welcome. The codebase is intentionally small and standard-library-only:

1. Fork the repository and create a feature branch.
2. Add or update tests under `tests/` — the suite must stay green (`python -m unittest discover -s tests`).
3. Keep new code dependency-free unless there is a compelling reason otherwise.
4. Open a pull request describing the change and the motivation.

Bug reports and ideas for new primitives (logging, streaming, templates) are equally valuable.

## 📄 License

Sage is released under the [MIT License](LICENSE). Use it freely in personal and commercial projects.
