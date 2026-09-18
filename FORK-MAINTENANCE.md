# Qlearn 下游改动登记册与 DeepTutor 升级手册

> 状态：生效中
>
> 维护对象：`jisongkun/Qlearn` 及其部署
>
> 上游：`HKUDS/DeepTutor`
>
> 最近一次仓库盘点：2026-08-05
>
> 当前登记基线：DeepTutor `v1.5.9`，提交 `37c3db6df7e886aee4f61c97ec5e618b8ab379e8`

本文是 Qlearn 作为 DeepTutor 长期下游 fork 的维护入口。它回答五个问题：

1. Qlearn 相对 DeepTutor 改了什么；
2. 为什么改，以及哪些行为必须保持不变；
3. 哪些改动最容易与未来上游冲突；
4. 上游升级时如何判断保留、重做、上游化或删除；
5. 将来增加后端功能时，如何避免把 fork 变成无法合并的独立分支。

本文不代替 Git 历史、测试或 ADR。Git 记录“代码如何变化”，本文记录“为什么、边界、风险和升级方法”。每一项 Qlearn 下游改动必须同时有可追踪的提交和登记项。

## 1. 文档体系

Qlearn 采用四层记录，避免把所有信息堆在一篇会迅速过期的长文里：

| 层级 | 作用 | 维护规则 |
| --- | --- | --- |
| `AGENTS.md` | 不可违反的兼容性合同和工作规则 | 只记录长期稳定规则 |
| 本文 | 下游改动总索引、风险地图和升级运行手册 | 每个下游功能提交同步更新 |
| `adr/` | 单个重大架构决策的背景、备选方案和后果 | 后端、协议、持久化或部署架构变化前创建 |
| Git/测试/发布记录 | 可执行事实、差异和验证证据 | 小而聚焦的提交；测试与功能同行 |

行业依据：

- GitHub 官方建议 fork 通过配置 `upstream` 后合并上游默认分支来同步。Qlearn 因此坚持 merge-based 同步，不重写共享上游历史：<https://docs.github.com/en/pull-requests/how-tos/work-with-forks/syncing-a-fork>
- ADR 用于记录一个重要决策的上下文、选择和后果，多个 ADR 组成决策日志：<https://adr.github.io/>
- Git `rerere` 可以记录并复用已经人工解决过的冲突，适合长期 fork 反复遇到相同冲突：<https://git-scm.com/docs/git-rerere>
- `git range-diff` 可以辅助审阅同一补丁系列在两次整理后的语义变化，但 Qlearn 不用它替代 merge 历史：<https://git-scm.com/docs/git-range-diff>

## 2. 仓库关系与当前状态

| 项目 | 当前值 |
| --- | --- |
| Qlearn origin | `git@github.com-jisongkun:jisongkun/Qlearn.git` |
| DeepTutor upstream | `https://github.com/HKUDS/DeepTutor.git` |
| Qlearn 当前开发分支 | `codex/qlearn-ui-redesign` |
| 已合入上游基线 | DeepTutor `v1.5.9` / `37c3db6d` |
| 基线后的 Qlearn 提交数 | 15（包含 v1.5.9 merge commit、治理与升级记录提交） |
| 盘点时上游最新 main | `37c3db6df7e886aee4f61c97ec5e618b8ab379e8`，发布线为 `v1.5.9` |
| 当前同步缺口 | 无（截至 2026-08-05 的 `upstream/main`） |

“当前值”是盘点快照，不是永久常量。每次完成上游合并后必须更新本节的基线和同步缺口。

## 3. 下游改动登记规范

### 3.1 稳定 ID

每项 Qlearn 改动使用稳定 ID：

```text
QL-<AREA>-NNN
```

AREA 建议值：

| AREA | 范围 |
| --- | --- |
| `GOV` | 合同、流程、维护规则 |
| `UI` | 视觉、布局、导航、交互呈现 |
| `UX` | 会改变用户交互状态但不改变服务能力的行为 |
| `OPS` | 部署、反向代理、运行拓扑 |
| `BUILD` | Docker、依赖、产物打包 |
| `BE` | Python 后端、API、运行时 |
| `DATA` | 数据结构、迁移、持久化 |
| `QA` | 测试、验收和视觉证据 |

ID 不因文件移动或重构而变化。改动被上游吸收后，将状态改为 `upstreamed`，不要复用旧 ID。

### 3.2 状态

| 状态 | 含义 |
| --- | --- |
| `planned` | 已决定但尚未实现 |
| `active` | 已提交并由 Qlearn 使用 |
| `pending` | 工作区存在实现，但尚未整理为正式提交 |
| `upstreamed` | 上游已提供等价能力，等待或已经删除下游补丁 |
| `superseded` | 被新的 Qlearn 实现替代 |
| `removed` | 不再需要，已从产品删除 |

### 3.3 冲突风险

| 等级 | 判断 |
| --- | --- |
| 低 | 仅新增 Qlearn 文件，不修改上游文件或协议 |
| 中 | 修改展示层上游文件，但保留 props、路由和数据行为 |
| 高 | 修改共享布局、构建、运行时、transport、API、WebSocket、认证或持久化 |
| 极高 | 改变既有 API/事件/数据库格式，或大范围重写上游模块 |

### 3.4 每项记录的必填字段

每个登记项至少包含：

- 状态、负责人、首次引入提交、最近验证基线；
- 产品目的和用户可见结果；
- 受影响路径；
- 必须保持的上游行为不变量；
- 是否影响 API、WebSocket、认证、持久化、构建或部署；
- 上游冲突热点和重放策略；
- 验证命令、关键流程和回滚方式；
- 对应上游 issue/PR，或“不计划上游化”的理由。

## 4. 当前下游改动总览

### 4.1 已提交并生效

| ID | 状态 | 范围 | 提交 | 风险 | 摘要 |
| --- | --- | --- | --- | --- | --- |
| `QL-GOV-001` | active | 治理 | `ef7241ba` | 低 | 建立 Qlearn/DeepTutor 兼容合同 |
| `QL-GOV-002` | active | 治理门禁 | `e0b9ecad` | 低 | 强制所有 Agent 先读登记册，并通过本地审阅和验证保持同步 |
| `QL-UI-001` | active | 品牌与首页 | `287eb9e5`, `72441076` | 中 | Qlearn 品牌、登录页、首页、欢迎区和基础视觉系统 |
| `QL-QA-001` | active | UI 验收 | `16857118` | 低 | 记录首页视觉与交互验证证据 |
| `QL-OPS-001` | active | 测试部署 | `7cd0646a`, `3840e453` | 中 | 阿里云东京 Docker Compose 与 OpenResty 拓扑 |
| `QL-OPS-003` | active | CI/CD 治理 | `6b3165e3` | 低 | 禁用 GitHub Actions；GitHub 仅用于源码协作，测试部署在 aliyuntokyo 本机执行 |
| `QL-BUILD-001` | active | 生产镜像 | `b67975af` | 高 | 在生产镜像中加入 Math Animator 依赖 |
| `QL-BE-001` | active | 后端运行时 | `40a4e146`, `b97b2ded` | 高 | 防止外部 API 地址造成 Next.js 代理回环 |

### 4.2 工作区中尚未提交

以下内容在 2026-08-05 盘点时仍是 dirty worktree，不能视为稳定发布清单：

| ID | 状态 | 范围 | 风险 | 当前内容 |
| --- | --- | --- | --- | --- |
| `QL-UI-002` | pending | 顶部导航 | 高 | 新增 `TopNavigation`，用顶部菜单替代左右主侧栏；保留会话、新对话、权限和账号操作 |
| `QL-UI-003` | pending | 首页对齐与响应式 | 中 | 统一欢迎区、会话头和 composer 宽度；移动端隐藏次要机器人区域；处理低高度布局 |
| `QL-UX-001` | pending | 会话 Activity/Viewer | 中 | 右侧活动面板不再跨页面自动恢复或因切换 capability 自动弹出，只在明确动作时打开 |
| `QL-OPS-002` | pending | 测试域名 | 中 | 部署名、容器名、数据目录和 OpenResty 域名从 `qlearn` 调整为 `qlearn-test` / `qlearntest.jisongkun.tech` |
| `QL-QA-002` | pending | 视觉验收 | 低 | 顶部导航、首页对齐、暗色及响应式截图和 `design-qa.md` 追加记录 |

工作区还有 `.playwright-mcp/`、根目录多张审查截图和对比图。这些是临时证据，不应原样全部提交。正式提交前只保留有长期价值的精选证据，移动到稳定的 QA 文档目录；临时日志应保持未跟踪或加入忽略规则。

## 5. 已提交改动详情

### QL-GOV-001 — Qlearn 兼容合同

- 状态：`active`
- 提交：`ef7241bab9f78199fb8bf05178339a51efdd96f9`
- 主要路径：`AGENTS.md`
- 目的：明确 Qlearn 是 UI 优先的 DeepTutor 兼容 fork，并定义安全修改面、行为不变量和 merge-based 同步流程。
- 行为不变量：不影响运行时产品行为。
- 上游冲突：低；该文件属于 Qlearn 治理层。
- 升级处理：始终保留；若上游新增自己的 `AGENTS.md`，合并双方内容，不用一方覆盖另一方。

### QL-GOV-002 — Agent 必读与登记册维护门禁

- 状态：`active`
- 首次提交：`e0b9ecadf12e31df5c928478cddf778eb2d33eff`
- 主要路径：`AGENTS.md`、本文
- 目的：保证后续 Agent 在任何代码、配置、依赖、部署或上游同步工作前完整阅读本文；代码变更必须在同一工作单元同步维护登记项。
- 行为不变量：不改变 Qlearn 产品运行时、API、WebSocket、认证或持久化行为。
- 升级前门禁：必须先记录目标版本/提交、旧基线、dirty worktree 保护方案和受影响 QL ID。
- 升级后门禁：必须记录新基线、各 QL ID 的保留/重做/上游化/删除结果、验证证据、部署结果和遗留事项，才可宣布升级完成。
- 执行方式：GitHub Actions 已禁用，不再使用 PR workflow 门禁；由 Agent 启动规则、本地 diff 审阅、必要测试和提交审阅共同执行。
- 回滚：不得为了跳过一次登记而删除 `AGENTS.md` 或本文；若未来重新引入自动门禁，必须由用户明确批准且不得承担部署职责。

### QL-UI-001 — 品牌、首页与基础视觉系统

- 状态：`active`
- 提交：`287eb9e523dc207e265d37e9b2c68c23374582a4`、`724410767c85e1f282e2d21e5f9c8d390be5e745`
- 产品目的：将 DeepTutor 默认呈现改造成 Qlearn 学习空间，同时保留原有路线、会话、能力和数据流。
- 新增路径：
  - `web/components/common/BrandLockup.tsx`
  - `web/components/qlearn/WelcomeCanvas.tsx`
  - `web/public/qlearn/hero-robot.mp4`
  - `web/public/qlearn/hero-robot-poster.jpg`
- 主要修改路径：
  - `web/app/(auth)/login/page.tsx`
  - `web/app/(auth)/register/page.tsx`
  - `web/app/(workspace)/home/[[...sessionId]]/page.tsx`
  - `web/app/globals.css`
  - `web/app/layout.tsx`
  - `web/components/chat/home/*`
  - `web/components/layout/AppShell.tsx`
  - `web/components/sidebar/SidebarShell.tsx`
  - `web/components/space/SpaceDashboard.tsx`
  - `web/lib/settings-nav.ts`
  - `web/locales/{en,zh}/app.json`
  - `web/tailwind.config.js`
- 必须保持：
  - `/home`, `/space`, `/book`, `/co-writer`, `/settings` 等既有 URL；
  - 会话选择、新建、重命名、删除及持久化行为；
  - capability 权限状态、loading/error/empty/streaming 状态；
  - API、WebSocket 和 auth 调用仍经现有边界；
  - 中英文 locale key 对齐。
- 冲突热点：`AppShell.tsx`、首页 page、`globals.css`、侧栏、locale 文件。
- 重放策略：先接受上游数据与事件处理，再将 Qlearn 的 `BrandLockup`、`WelcomeCanvas` 和 token 化样式作为组合层重新接回。
- 回滚：移除 Qlearn 新组件引用并恢复上游 shell；静态资产可在无引用后删除。

### QL-QA-001 — 初始视觉验收证据

- 状态：`active`
- 提交：`16857118aa9ddac516cf4e80c63bc34ecf2a7a8b`
- 路径：`design-qa.md`、`.planning/qa/*`、已解决 debug 记录。
- 目的：记录设计实现时的视口、状态、偏差和已验证交互。
- 风险：低，但二进制截图会增加仓库体积。
- 升级处理：不参与冲突取舍；只保留仍能解释当前设计的证据。

### QL-OPS-001 — 阿里云东京测试部署

- 状态：`active`
- 提交：`7cd0646a088ed8b1d433a9ec9294dd7504dda71b`、`3840e4531e1be1ea01f0e72c9b2255803250122a`
- 路径：`deploy/aliyuntokyo/**`
- 拓扑：OpenResty HTTPS → 宿主机 `127.0.0.1:13400` → 容器 `3782`；数据目录挂载到容器 `/app/data`。
- 必须保持：
  - 应用端口不直接暴露公网；
  - WebSocket upgrade header 和长连接超时；
  - `/app/data` 持久化；
  - 健康检查访问容器内 backend；
  - 域名证书路径与部署环境一致。
- 冲突热点：上游 Docker 入口、端口默认值、健康检查和镜像 target。
- 升级处理：先验证新镜像内部端口和健康端点，再调整部署层；不要为迁就旧 compose 修改上游 runtime。

### QL-OPS-003 — 禁用 GitHub Actions 与本机部署边界

- 状态：`active`
- 首次提交：`6b3165e382c7ec6c7ab5a1c1209312800baf3b40`
- 主要路径：`AGENTS.md`、本文；GitHub 仓库 Actions 权限属于外部配置
- 目的：GitHub 只承担源码协作，不运行 Qlearn CI、release、镜像发布或部署，避免 PR push、上游 release workflow 或误操作触发远端执行。
- 当前配置：2026-08-06 已通过 GitHub repository Actions permissions 将 `jisongkun/Qlearn` 设置为 `enabled=false`；删除 Qlearn 自建的 `fork-registry.yml`，上游 `tests.yml`、`pypi-release.yml` 和 `docker-release.yml` 仅为减少 merge churn 而保留，禁止启用或 dispatch。
- 部署边界：Qlearn 当前只有 `aliyuntokyo:/data/home/shinji/Developer/Qlearn-test` 测试环境，使用本机 Docker Compose；当前没有生产环境。未来生产若获授权，遵循 aliyuntokyo 权威 `*-test` checkout 经 SSH/rsync 发布到 `hw135`，不得使用 GitHub Actions。
- 验证：检查 GitHub Actions permissions 为 disabled；确认没有 queued/in_progress run；本地测试和部署按本文及 `sjopswiki` 执行。
- 上游升级：上游 workflow 文件可随 merge 更新但不得启用；不要为禁用 Actions 而反复删除上游文件，从而制造无意义冲突。
- 回滚：只有用户明确改变 CI/CD 策略后才能重新启用 Actions，并需先更新 `AGENTS.md`、本文与 `sjopswiki`。

### QL-BUILD-001 — Math Animator 生产依赖

- 状态：`active`
- 提交：`b67975af0f4bb5f5dcee956b1c015d170c5f7a02`
- 路径：`Dockerfile`
- 目的：生产镜像安装 `requirements/math-animator.txt`，并提供 Cairo、Pango、FFmpeg、TeX、字体等运行依赖。
- 非 UI 改动：是；会改变镜像体积、构建时间和系统包攻击面。
- 必须保持：Math Animator 能在生产容器实际渲染，而不只是模块可导入。
- 冲突热点：上游 Docker 多阶段构建、Python requirements 分组、系统包版本。
- 升级处理：若上游正式将 Math Animator 纳入生产镜像，应优先删除本补丁并采用上游实现；不得重复安装依赖。
- 验证：生产镜像 build、容器启动、Math Animator 最小渲染、产物下载。

### QL-BE-001 — 防止外部 API 代理回环

- 状态：`active`
- 提交：`40a4e1468bfb412e711dcd542503ef4269b99897`，Ruff 格式修正 `b97b2ded`
- 路径：
  - `deeptutor/services/config/runtime_settings.py`
  - `tests/services/config/test_runtime_settings.py`
- 目的：`DEEPTUTOR_API_BASE_URL` 只使用 in-network `next_public_api_base` 或 backend localhost，不再回退到浏览器使用的外部 URL，避免反向代理部署中请求重新进入前端形成回环。
- 非 UI 改动：是；属于 transport/runtime 边界。
- 必须保持：
  - 浏览器外部 API 地址与前端服务器访问 backend 的内部地址相互独立；
  - `next_public_api_base_external` 不得成为 server-side proxy target；
  - 本地单体启动仍回退到 `http://localhost:<backend_port>`。
- 冲突热点：runtime settings 字段解释、launcher 环境变量、`web/proxy.ts`。
- 升级处理：检查上游是否已有等价修复。若有，用上游测试替换本补丁；若没有，在合并后重跑专用测试。
- 上游化建议：高。该问题不是 Qlearn 品牌差异，而是通用反向代理 bug，适合提交 DeepTutor PR。

## 6. 待提交改动详情

### QL-UI-002 — 顶部导航替代左右主导航

- 状态：`pending`
- 新增路径：`web/components/navigation/TopNavigation.tsx`
- 修改路径：`AppShell.tsx`、`UtilitySidebar.tsx`、`WorkspaceSidebar.tsx`、locale 文件及相关首页组件。
- 产品目的：将主要菜单、新对话、最近会话和账号入口放进单行顶部导航，降低左右侧栏常驻占用。
- 必须保持：
  - 路由和 capability 权限判断；
  - 新会话、会话选择、重命名、删除处理器；
  - 管理员、个人资料、退出登录；
  - 移动端菜单、Escape、外部点击关闭和键盘可访问性。
- 冲突风险：高。它替换上游共享 AppShell/Sidebar 组合，是未来导航改动的主要冲突点。
- 整理要求：
  - 将新组件作为 additive wrapper 保持；
  - 不删除上游 Sidebar 组件，除非确认没有其他路线引用；
  - 单独提交导航，不与首页尺寸、Activity 行为或部署改动混合；
  - 增加路由、会话操作和移动端契约测试。

### QL-UI-003 — 首页宽度与响应式层级

- 状态：`pending`
- 目的：会话工具栏、欢迎内容和 composer 使用统一内容网格；小屏优先保证提问和学习入口可见。
- 必须保持：starter 仍调用现有 composer；机器人仅是次要展示，不参与能力逻辑。
- 冲突热点：首页 page、`WelcomeCanvas.tsx`、`ChatComposer.tsx`。
- 整理要求：作为独立 UI 提交，不和顶部导航提交混合。

### QL-UX-001 — Activity/Viewer 显式打开策略

- 状态：`pending`
- 目的：右侧 Activity/Viewer 不再因 localStorage 或 capability 切换自行弹出并遮挡主工作区。
- 行为变化：这是交互状态变化，不是纯样式变化。
- 必须保持：当发送动作确实需要 capability 配置时，仍可显式打开 Activity；文件、本地文件和网页预览继续工作。
- 冲突热点：首页 page、`SessionViewerPanel.tsx`、`FilePreviewDrawer.tsx`。
- 整理要求：补充 viewer 初始关闭、显式打开、文件预览和 capability config gate 测试。

### QL-OPS-002 — 测试环境命名与域名

- 状态：`active`
- 变化：`qlearn` → `qlearn-test`；域名 → `qlearntest.jisongkun.tech`；默认数据目录 → `/data/opt/docker/qlearn-test/data`。
- 风险：数据目录变更可能造成“新容器看不到旧数据”的假丢失。
- 2026-08-27 数据盘收敛：checkout 改为 `/data/home/shinji/Developer/Qlearn-test`，Compose 默认数据目录直接改为 `/data/opt/docker/qlearn-test/data`，不保留旧路径 bind mount 或软链接。
- 验证：容器 Compose working directory、config file 和 `/app/data` Source 均指向 `/data`；健康检查通过，权威数据目录约 65 MiB。
- 回滚：停止容器，将数据一致性复制到明确选定的新目标，更新 `QLEARN_DATA_DIR` 后重建；不要依赖旧 `/opt/docker` 路径自动创建空数据目录。

## 7. 未来后端功能的兼容设计规则

用户明确计划未来增加后端能力。后端改动必须比 UI 改动使用更严格的准入门槛。

### 7.1 优先级顺序

新增功能按以下顺序选实现位置：

1. 使用 DeepTutor 已有 Tool、Capability、MCP、skill 或 provider 扩展点；
2. 新增独立的 Qlearn 模块，通过一个最小 adapter 接入上游注册表；
3. 在现有公共接口旁增加向后兼容的可选字段或新端点；
4. 最后才修改 orchestrator、transport、事件协议或持久化核心。

如果第 4 步不可避免，实施前必须先写 ADR。

### 7.2 命名空间

- 新模块优先放在独立 `qlearn_ext/` 或明确的 Qlearn-owned 包中；
- 新 HTTP 路径使用 `/api/v1/qlearn/...`，避免占用未来上游通用名称；
- 新事件使用 `qlearn.<domain>.<event>`；
- 新配置使用 `qlearn_*` 或 `qlearn.<section>`；
- 新数据库表、文件和缓存键必须有 Qlearn 前缀与版本。

命名空间不能成为复制上游代码的借口。Qlearn 模块应调用稳定接口，不应长期维护一份上游实现副本。

### 7.3 功能开关与兼容默认值

- 新后端功能默认关闭，除非它是完全向后兼容的新入口；
- 旧 API、WebSocket 事件和数据读取行为必须继续工作；
- 新字段应可选，旧客户端忽略后仍能运行；
- 删除或重命名必须经过至少一个兼容周期和迁移说明；
- 所有持久化变更必须有显式 schema/version、迁移、备份和回滚路径。

### 7.4 测试要求

后端功能至少需要：

- 单元测试：Qlearn 新模块自身；
- 契约测试：既有 API/WS 输入输出未变化；
- 升级测试：旧数据在新代码中可读；
- 降级说明：若数据一经迁移不可回退，必须在 ADR 和发布说明中突出；
- 集成测试：从 Web/CLI/SDK 中受影响的入口完成一次端到端流程；
- 上游合并回归：上游新版本合入后重跑对应契约测试。

### 7.5 上游化判断

满足任一条件时优先向 DeepTutor 提交 PR，而不是永久保留下游补丁：

- 修复的是 DeepTutor 通用 bug；
- 功能不依赖 Qlearn 品牌或私有业务；
- 改动位于 transport、auth、runtime、provider、数据模型等高冲突核心；
- 上游也会受益，且可以通过可选配置保持默认行为。

品牌、部署域名、私有业务流程和实验性差异通常保留下游，但仍要隔离实现。

## 8. 上游升级运行手册

### 8.1 升级前

升级开始时，先在本文新增一条“进行中的上游升级记录”。未记录以下内容不得执行 merge：

- 目标版本、目标提交和当前基线；
- 当前分支、HEAD 和工作区状态；
- dirty worktree 的保护方式；
- 上游改动涉及的 QL ID 与高风险边界；
- 计划执行的验证和部署环境。

1. 确保工作区干净；按 UI、部署、构建、后端分别提交，禁止携带未分类文件开始 merge。
2. 记录当前：

```bash
git status --short
git rev-parse HEAD
git rev-parse upstream/main
git merge-base HEAD upstream/main
```

3. 更新本文中所有 `pending` 项；决定提交、丢弃或延后。
4. 备份部署数据和配置，尤其是 `/app/data`、认证配置和任何新 schema。
5. 可在维护者本机启用冲突复用：

```bash
git config rerere.enabled true
git config rerere.autoupdate true
```

`rerere` 是辅助工具，自动应用后仍必须审阅差异和测试。

### 8.2 获取并审阅上游

```bash
git fetch upstream
git log --oneline --decorate HEAD..upstream/main
git diff --stat HEAD...upstream/main
```

先阅读上游 release notes，再按风险地图检查：

- `web/components/layout/`, `web/components/sidebar/`, 首页和 locale；
- `Dockerfile` 和 requirements；
- `runtime_settings.py`, `web/proxy.ts`, API/WS/auth 边界；
- Qlearn 将来新增的 schema、路由和 event。

### 8.3 建立同步分支并合并

```bash
git switch main
git switch -c sync/upstream-vX.Y.Z
git merge --no-ff upstream/main
```

冲突处理顺序：

1. 先恢复上游新增或修复的行为；
2. 再检查对应 QL 登记项的产品目的和不变量；
3. 优先使用 wrapper、composition 和 Qlearn 新文件重新施加呈现；
4. 若上游已有等价能力，删除下游补丁并把登记项改为 `upstreamed`；
5. 不以“Qlearn 文件更新日期更晚”为理由整块选择 Qlearn 版本；
6. transport、auth、API、WS、持久化冲突必须逐字段审阅，禁止仅解决语法冲突。

### 8.4 冲突后的差异审计

```bash
git diff --check
git diff --name-status upstream/main...HEAD
git log --oneline upstream/main..HEAD
```

检查每个仍存在的下游差异是否有 QL ID。没有登记项的差异不能直接进入发布。

当某组补丁在升级过程中被重新整理，可辅助比较语义：

```bash
git range-diff <old-upstream>..<old-qlearn> <new-upstream>..<new-qlearn>
```

### 8.5 必需验证

前端基础门禁：

```bash
cd web
npm run lint
npm run test:node
npm run i18n:check
npm run build
```

后端或构建改动还要运行对应 Python 测试、生产镜像 build 和受影响端到端流程。至少验证：

- 登录、注册和 auth gate；
- 主聊天 WebSocket、流式输出、停止和重连；
- 会话新建、历史、重命名和删除；
- Knowledge Base 上传、索引和检索；
- Qlearn 顶部导航及移动端；
- Activity/Viewer 文件与网页预览；
- Math Animator 生产渲染；
- 反向代理 API 和 WebSocket；
- 新增后端功能的契约及数据迁移。

### 8.6 完成升级

1. 将本文基线更新为新上游提交；
2. 更新每个受影响登记项的“最近验证基线”；
3. 记录被删除、上游化或重新实现的补丁；
4. 提交同步 PR，PR 描述按 QL ID 列出保留差异和验证结果；
5. 测试环境部署并完成 smoke test 后再合并到主分支；
6. 保留 merge commit，推送 `origin main`。

### 8.7 上游升级记录

#### DeepTutor v1.6.8 + post-release fixes（进行中）

| 字段 | 记录 |
| --- | --- |
| 升级目标 | `upstream/main` / `897fce52f24bf22e6e50d8a3e4df532632a26322`（DeepTutor `v1.6.8` 后 3 个 mastery 修复） |
| 升级前基线 | DeepTutor `v1.5.9` / `37c3db6df7e886aee4f61c97ec5e618b8ab379e8` |
| 升级前 Qlearn HEAD | `66a354f831e22a56cfde1c95eda8df88ae71c0cf` |
| 工作分支 | `sync/upstream-v1.6.8`，隔离工作树 `/data/home/shinji/Developer/Qlearn-sync-v1.6.8` |
| dirty worktree 保护 | 权威开发目录 `/data/home/shinji/Developer/Qlearn-test` 保持在 `codex/qlearn-ui-redesign`，其 35 个未提交/未跟踪路径不做 stash、不覆盖；同步分支从已提交 HEAD 创建独立 worktree。待上游功能基线验证通过后，再按 QL ID 将 pending UI 适配到新架构。 |
| 上游源码差异 | 687 个提交、6,728 个路径；其中 4,447 个删除主要包含上游清理的 `web/.next-deeptutor/` 产物。上游从 v1.6.3 起切换到 v2 前端运行时并移除 v1 chat transport/legacy surfaces。 |
| 与 dirty worktree 重叠 | 8 个路径：旧首页 page、ChatComposer、SessionViewerPanel、FilePreviewDrawer、两个 Sidebar、英/中文 locale；旧首页 page 已被上游删除，必须在 v2 route composition 上重做而非保留旧文件。 |
| 初始受影响 QL ID | `QL-GOV-001/002`、`QL-UI-001/002/003`、`QL-UX-001`、`QL-QA-001/002`、`QL-BUILD-001`、`QL-BE-001`、`QL-OPS-001/002/003` |
| 行为不变量 | 先保留上游 v2 的 API/REST contract、turn runtime、WebSocket/stream、auth、session、KB、settings、reading、mastery 和错误状态，再重接 Qlearn 品牌、64px 单行顶部导航、New chat/Recents、1120px 首页网格、响应式与显式 Viewer 策略。不得恢复上游已删除的 v1 transport。 |
| 计划验证 | `web`: lint、node tests、i18n check、build；后端受影响测试；Docker 镜像 build；auth gate、chat turn/stream/cancel/reconnect、session CRUD/recycle bin、KB upload/index/retrieval、顶部导航、Activity/Viewer、Math Animator、反向代理 API/WS smoke。 |
| 部署计划 | 本轮先在隔离同步工作树完成合并与验证。未完成 QL reconciliation、全量门禁和测试环境回滚标签前，不更新 `/data/home/shinji/Developer/Qlearn-test`，不部署，不推送。 |
| 当前状态 | `in_progress` |

#### DeepTutor v1.5.9（已完成）

| 字段 | 记录 |
| --- | --- |
| 升级目标 | DeepTutor `v1.5.9` / `37c3db6df7e886aee4f61c97ec5e618b8ab379e8` |
| 升级前基线 | DeepTutor `v1.5.8` / `44fa7a1552b88f9d8ce2c22259128a15ae2eb0c8` |
| 升级前 Qlearn HEAD | `40a4e1468bfb412e711dcd542503ef4269b99897`（登记门禁提交前） |
| 工作分支 | `codex/qlearn-ui-redesign` |
| dirty worktree 保护 | 保留并盘点现有 UI、部署和 QA 修改；先审计上游重叠路径，使用可恢复的临时同步分支/定向 stash，禁止覆盖用户改动 |
| 上游源码差异 | 73 个非构建产物路径；另含上游提交的 `web/.next-deeptutor/` 构建产物 4,322 个文件 |
| 与 dirty worktree 重叠 | 首页 page、英文 locale、中文 locale，共 3 个路径 |
| 初始受影响 QL ID | `QL-UI-001`、`QL-UI-002`、`QL-UI-003`；另重点验证上游 auth、orchestrator、settings、provider 与 embedding 变更 |
| 合并结果 | merge commit `98a2ab1ebf6755d988825c62ba27fd149b8f11db`；保留上游历史，`upstream/main` 是当前 HEAD 的祖先；定向 stash 自动恢复，3 个重叠文件无冲突 |
| QL reconciliation | `QL-UI-001` 保留，下游视觉层与上游会话标题/首屏语言修复同时存在；`QL-UI-002`、`QL-UI-003` 恢复为 pending；`QL-BE-001` 未被覆盖；`QL-OPS-001/002` 已使用完整 `/app/data` 挂载，不需要执行 v1.5.9 GHCR 单文件挂载迁移；其余登记项无语义变化 |
| 前端验证 | `npm run lint`：0 errors / 38 warnings；`npm run test:node`：380/380 passed；`npm run i18n:check`：locale parity 通过，非严格审计仅报告既有潜在项；`npm run build`：成功，57 routes |
| Python 验证 | 在与生产镜像一致的隔离容器环境运行测试：286 passed / 1 skipped / 1 warning；宿主机缺少 Python 项目依赖，因此未把宿主失败误记为代码失败 |
| 镜像验证 | `qlearn-test:aliyuntokyo`，image ID `sha256:25bb72f29ecd6cd929d5b8cd466522bfc5969f700aa4aab49ec0d5a7077e8f32`；确认 DeepTutor `1.5.9`、Manim `0.20.1` 与 `GeminiEmbeddingAdapter` 可导入 |
| 测试部署 | 2026-08-05 21:44（Asia/Shanghai）重建 `qlearn-test`；容器 `healthy`；继续挂载 `/data/opt/docker/qlearn-test/data -> /app/data`；宿主仅监听 `127.0.0.1:13400` |
| Smoke test | `http://127.0.0.1:13400/` 与 `https://qlearntest.jisongkun.tech/` 均按 auth gate 跳转 `/login?next=%2F` 并最终返回 HTTP 200；后端和前端进程均进入 RUNNING；启动日志无应用错误 |
| Git 远端状态 | 2026-08-06 已将 `origin` 修正为 `git@github.com-jisongkun:jisongkun/Qlearn.git`，并让 `github.com` 默认使用 `jisongkun` 专用密钥；升级与 CI/CD 治理已推送至 commit `6b3165e3` |
| 部署源码标识 | 已提交基线 HEAD `98a2ab1e` 加升级前已存在的 pending 工作区；tracked patch fingerprint `562066cc9a9ce54e3ca9b7410506bf40b669827c`；镜像内新增 `TopNavigation.tsx` blob `55f1343583a2a243fa677ea570c55f36ee0c181e`。这不是完全可复现的发布 SHA，后续必须把 pending 改动按 QL ID 提交后再构建 |
| 未覆盖的人工流程 | 未使用真实登录账号执行 chat WebSocket、KB 索引、Codex OAuth 和 Math Animator 实际渲染；自动化契约/构建与进程 smoke 已通过，这些登录后流程应在提升到主分支前补测 |
| 上游遗留 | 官方 v1.5.9 tag 自带 `web/.next-deeptutor/` 4,322 个构建产物文件，本次为保持上游历史原样合入；后续单独评估上游清理，不在同步 merge 中删除 |
| 回滚说明 | 构建前旧 `qlearn-test:aliyuntokyo` 标签未另存，无法对旧运行镜像做精确标签回滚；可从 v1.5.8 与已有 Qlearn 提交重建。以后部署必须先给当前 image ID 添加不可变 rollback 标签 |
| 当前状态 | `complete` |

## 9. Pull Request 检查清单

每个 Qlearn PR 至少回答：

- [ ] 对应哪个 QL ID；新改动是否已创建登记项？
- [ ] 这是 UI、UX、OPS、BUILD、BE 还是 DATA？
- [ ] 是否修改上游拥有的文件？能否改成 additive wrapper？
- [ ] API、WebSocket、认证、持久化和路由是否完全兼容？
- [ ] 是否保留 loading、empty、error、disabled、permission 和 partial-stream 状态？
- [ ] 是否把多个冲突域混进同一个提交？
- [ ] 是否补充了验证和回滚方式？
- [ ] 是否应提交上游 PR？
- [ ] 本文和必要 ADR 是否随代码一起更新？

建议提交主题带 QL ID，例如：

```text
feat(qlearn-ui): add top navigation [QL-UI-002]
fix(runtime): avoid external proxy loop [QL-BE-001]
```

## 10. ADR 触发条件与模板

出现以下情况必须新建 `adr/NNNN-<slug>.md`：

- 新后端服务、队列、数据库或外部依赖；
- 修改 API、WebSocket、认证、provider 或事件协议；
- 新持久化格式或不可逆迁移；
- 绕过 DeepTutor Tool/Capability/plugin 扩展点；
- 引入会显著改变部署、成本、安全或运维方式的组件；
- 有两个以上合理方案且未来维护者需要理解取舍。

最小模板：

```markdown
# ADR-NNNN: 决策标题

- 状态：proposed | accepted | superseded | deprecated
- 日期：YYYY-MM-DD
- 关联 QL ID：QL-BE-NNN
- 上游基线：<commit>

## 背景

## 决策驱动因素

## 考虑过的方案

## 决策

## 对上游合并的影响

## API、事件与数据兼容性

## 验证、迁移与回滚

## 后果与后续工作
```

## 11. 新登记项模板

复制以下内容到“当前下游改动”对应章节：

```markdown
### QL-AREA-NNN — 标题

- 状态：planned | active | pending | upstreamed | superseded | removed
- 负责人：
- 首次提交：
- 最近验证上游基线：
- 关联 ADR / 上游 issue / PR：
- 冲突风险：低 | 中 | 高 | 极高

#### 目的与用户结果

#### 受影响路径

#### 上游行为不变量

#### API / WebSocket / Auth / Data / Build / Deploy 影响

#### 冲突热点与重放策略

#### 验证

#### 回滚

#### 上游化或长期保留下游的理由
```

## 12. 当前待办

按 2026-08-05 盘点结果：

1. 将 pending 顶部导航、首页对齐、Viewer 行为、测试域名按 QL ID 分成独立提交；
2. 处理根目录临时截图和 `.playwright-mcp/`，只保留精选证据；
3. 将 pending 工作区按 QL ID 提交并重新构建，使部署恢复为可由单一 Git SHA 复现；
4. 在提升到主分支前，用真实账号补测 chat WebSocket、KB、Codex OAuth 和 Math Animator 渲染；
5. 评估上游 v1.5.9 自带的 `web/.next-deeptutor/` 构建产物，优先推动上游清理，避免在同步 merge 中制造大面积删除；
6. 评估将 `QL-BE-001` 作为通用修复贡献上游；
7. 若修复 Codex OAuth/模型兼容层，先建立新的 `QL-BE-*` 登记项和 ADR，不得混入 UI 或上游同步提交；
8. 每次部署前先给当前镜像加不可变 rollback 标签，并记录“部署提交 SHA”，避免把工作区状态误认为线上状态。
