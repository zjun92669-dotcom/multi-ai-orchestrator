# Codex 后台同步协作

## 目标

Codex 在后台派发和验收任务，WorkBuddy 在后台执行，用户不需要反复切换应用窗口。

## 分层

1. Codex 是外部调度器和验收方。
2. WorkBuddy 客户端运行主调度 AI 和三个成员。
3. Codex WorkBuddy Gateway 通过本机 ACP 连接 WorkBuddy。
4. Gateway 使用任务专属结果标记隔离当前任务。
5. WorkBuddy 主调度人创建原生团队和代理线程。
6. Gateway 返回任务状态、代理事件和最终结果。

WorkBuddy 可以作为指挥方，把分支任务交给 Codex CLI、HTTP AI 服务、MCP 连接器或其他 A2A 代理。外部 AI 的接入声明放在 `external_agents.json`。每次调用必须使用 `external_agent_adapter.py` 或 WorkBuddy 原生连接器，并保存请求、响应和时间。

Codex 和 WorkBuddy 的职责必须分开。Codex 负责发起任务、等待状态、检查结果和要求返工。WorkBuddy 负责创建代理团队、生成内容和执行文件操作。

每次任务必须使用一个稳定的 `trace_id`。Codex 发送的验收标准、交付物和工作目录要原样进入顶层任务。

## 安全边界

不要把 `codex-workbuddy` 这个 Gateway 控件的 Skill 安装到 WorkBuddy 内。那样会形成 WorkBuddy 到 Gateway 再到 WorkBuddy 的调用回路。

Gateway 只连接本机已登录的 WorkBuddy 会话。用户需要保持 WorkBuddy 运行，并保留一个已认证的会话。应用窗口可以放在后台，Codex 不依赖鼠标点击来推进任务。

WorkBuddy 可能在开始新任务时重放当前会话的历史消息。Gateway 必须只接收本次任务的结果。当前实现要求 WorkBuddy 在最终回答开头返回本次任务专用的结果标记，并在标记出现后才开始收集最终文本。

## 后台流程

```text
Codex 检查网关健康
→ Codex 提交完整任务说明
→ Gateway 将任务送入 WorkBuddy
→ WorkBuddy 主调度人拆分任务
→ 三个成员执行
→ Codex 读取状态和最终结果
→ Codex 对照验收标准
→ 失败时要求修订
→ 通过后记录验收
```

## 任务状态

Codex 只把以下状态视为结束：

- `completed`
- `failed`
- `cancelled`
- `needs_input`
- `verification_failed`

任务处于 `queued`、`running` 或 `prompting` 时，Codex 不宣布完成。

## 并发限制

当前 Gateway 采用严格串行模式。一条链路只允许一个活动任务。三个成员的并行发生在同一个 WorkBuddy 团队内部，不能通过同时提交多个 Gateway 任务来模拟。

主调度人可以创建下级代理。下级代理可以经授权继续创建下级。所有代理共用一个 `team_name`。每个代理只有一个直接上级。下级先向直接上级汇报，直接上级再逐级向上汇报。

## 过程可见

WorkBuddy 主调度人必须在最终结果中返回：

1. 用户原始目标。
2. `trace_id` 和 `team_name`。
3. 完整上下级树。
4. 每个成员的名字、直接上级和线程引用。
5. 任务拆分和候选成员。
6. 每个成员的任务、状态、对话摘要和产物。
7. 发送过的主要消息和消息类型。
8. 随机分配使用的种子。
9. 失败、重试和阻塞项。
10. 验收结果。

Codex 负责把这些结果汇总给用户。用户可以在 WorkBuddy 中直接打开各成员线程，查看完整对话和工具过程，也可以直接在 Codex 中补充要求。

Codex 不接受角色扮演记录作为多代理证据。缺少真实 `Agent` 线程或多个代理没有互相发消息时，验收必须失败。

外部 AI 返回结果后，WorkBuddy 必须检查结果内容，不能只看 HTTP 200 或进程退出码。Codex 再检查 WorkBuddy 的最终汇总和文件证据。

## 无切屏验收

1. WorkBuddy 保持后台运行，不切换到 App 前台操作。
2. Codex 提交一个只读任务。
3. Codex 通过状态接口看到任务进入运行中。
4. WorkBuddy 返回结构化结果。
5. Codex 完成验收，并把同一会话继续用于返工。

任何一步依赖人工点击发送按钮，都不算后台同步通过。
