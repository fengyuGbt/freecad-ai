# FreeCAD 第三方模块调研与 AI 集成实验

> 日期：2026-09-18 ｜ 环境：FreeCAD 1.0.2 (Rev 39319) + 智谱 GLM-4-Flash（免费模型）
> 目的：补足 FreeCAD 与 CATIA 的能力差距（曲面/装配），并验证大模型能否驱动第三方模块。

---

## 一、FreeCAD 与 CATIA 的核心差距（调研结论）

| 能力维度 | CATIA（商业标杆） | FreeCAD（开源） | 差距性质 |
|---|---|---|---|
| **Class-A 曲面** | FreeStyle / Generative Shape Design，行业金标准：数学完美的曲率连续曲面、斑马纹分析 | 基础 NURBS 曲面可用；高光质量曲面需第三方模块，仍达不到车身 A 面水平 | 大（生产级不可替代） |
| **大型装配 / 数字样机** | DMU Navigator 管理数万组件、干涉检查成熟 | 原生 Assembly 工作台（v1.0 新增）尚实验性；第三方装配模块有解但性能有限 | 大（超大装配） |
| **复杂约束网络性能** | 工业级求解器 | 大型模型约束网络性能会下降（业界评测 7.3/10） | 中 |
| **PLM / 多学科集成** | 3DEXPERIENCE + ENOVIA、KBE 知识工程、结构/电气/系统一体 | 无 PLM；FEM 等模块可用但集成度弱 | 大 |
| **行业专用工具** | 模具设计、高级钣金成型、线束、复合材料等专攻 | 覆盖面窄，靠第三方补充 | 中 |
| **成本与数据主权** | 高许可费（订阅 $7,560/年起） | 免费、可私有化部署、可编程 | FreeCAD 优势 |

**结论**：FreeCAD 定位是"零成本、可编程、数据主权"的开发与原型平台；生产级车身 A 面与超大型装配仍需 CATIA/NX。第三方模块可显著缩小"曲面/装配"差距，但替代不了生产级工具。

---

## 二、第三方模块调研（FreeCAD 官方 Addons 生态）

### 曲面方向

| 模块 | 维护者 | 状态 | 定位 |
|---|---|---|---|
| **Curves WB** | Christophe Grellier | 活跃（0.6.81, 2026-09） | NURBS 曲线/曲面建模工具集：Gordon 曲面、双轨扫掠、等参线、曲面分析、**斑马纹检查（ZebraTool）**。最推荐 |
| **Silk** | emmettfrancis | 维护 | 低阶/接缝连续 NURBS 曲面（A 面方向探索） |
| **CurvedShapes** | Chris_G | 活跃 | 从 2D 曲线生成 3D 形状 |
| **Nurbs** | (社区) | 脚本集 | 自由曲面/曲线管理脚本 |
| **Surface WB** | 内置 | 稳定 | 官方基础曲面工作台 |

### 装配方向

| 模块 | 维护者 | 定位 | 特点 |
|---|---|---|---|
| **A2plus** | kbwbe | 最简装配 | 约束式（面贴合/轴对齐），KISS 原则，类似 SolidWorks 习惯，适合快速验证 |
| **Assembly3** | realthunder | 高级装配 | App Link + 约束求解器 + assembly freeze，适合大型装配 |
| **Assembly4** | Zolko-123 | 自顶向下 | 基于 LCS + Part::Attacher + ExpressionEngine，规避拓扑命名问题；有阵列/镜像/碰撞检查 |
| **Assembly WB（原生）** | FreeCAD 团队 | v1.0 新增 | 官方实验性装配工作台 |

**选型建议**：AI 集成优先选 **Assembly4**（基于坐标系与表达式，脚本可编程性最好）；快速原型用 A2plus；大型动态装配用 Assembly3。

---

## 三、FreeCAD 的 AI 生态（2026 现状）

| 项目 | 说明 |
|---|---|
| **FreeCAD MCP**（neka-nat 等多家实现） | MCP 服务器让 Claude/Codex 等通过标准协议驱动 FreeCAD（TCP/本地）；有 headless/Docker 变体 |
| **freecad-robust-mcp** | pip 可装的健壮版 MCP 桥，含 headless 执行（freecadcmd） |
| **ghbalf/freecad-ai** | FreeCAD 内 AI 助手工位，自然语言 → 生成 Python 代码建模型 |
| **CAD-Assistant**（arXiv 2412.13810） | 视觉 LLM + CAD 工具增强的通用 CAD 任务求解框架（基于 FreeCAD Python API） |
| **本仓库 freecad-ai** | 自研：工具注册 + 函数调用 + 几何自校验 + 自我修正闭环（零依赖，可接任何 OpenAI 兼容模型） |

**结论**：AI×FreeCAD 已是活跃方向。我们的自研方案与 MCP 生态互补——MCP 适合"接 Claude/Codex 客户端"，自研 agent 适合"程序化可控、可加几何校验"的流水线。

---

## 四、实验记录（真实环境）

### 4.1 安装（远程 FreeCAD 1.0.2，Windows）

- 用户 Mod 目录：`C:\Users\eryes\AppData\Roaming\FreeCAD\Mod\`
- 安装 Curves WB（下载 zip 解压到 `Mod\Curves`）
- Assembly4 原仓库已迁移（Zolko-123 仓库不可访问），fork 可用；本次以 Curves 为主实验

**踩坑 1（重要）**：FreeCAD 1.0.2 headless（freecadcmd）中，第三方模块包名**大小写敏感**：
`import freecad.curves` 失败（find_spec 返回 None），必须 `import freecad.Curves`（目录名是 `Curves`）。
且 FreeCAD 扩展 `__path__` 但不同步 `ModuleSpec.submodule_search_locations`，子模块查找以 spec 为准。

**踩坑 2**：部分 Curves 模块（如 `interpolate`）依赖 GUI（`FreeCADGui.addCommand`），headless 下不可用；
纯计算模块（`gordon`）可用。→ AI 集成需选 headless 安全的工具面。

### 4.2 纯功能验证：Gordon 曲面（headless 通过）

用 `freecad.Curves.gordon.InterpolateCurveNetwork(profiles, guides).surface()` 从 2×2 曲线网络
生成 B-spline 曲面成功：60×40×12.16mm，体积 12800 mm³，导出 STL 正常。

### 4.3 AI 集成实验（GLM-4-Flash 驱动 Curves）

**v1（失败，有教育意义）**：给 LLM 一个接受"曲线点网络"（嵌套 JSON）的工具 `make_gordon_surface`，
GLM-4-Flash **无法正确生成嵌套数据结构**（把 profile 数组写成扁平点列表），且 7 轮重试参数完全一样、不学习错误。
→ 证实：免费模型对复杂几何数据的结构化生成不可靠，必须框架补偿。

**v2（成功）**：改为语义化工具 `make_panel_surface(name, length, width, arch_height)`——
框架自动生成 2×2 曲线网络并调用 Curves Gordon 求解器。GLM 一次调用成功：

```
args: {"length": "60", "width": "40", "arch_height": "10", "name": "curved_panel"}
结果: 60×40×15.2mm B-spline 拱面，面积 2658.36 mm²，STL 导出成功
```

**核心工程模式**：**"LLM 给意图，框架给几何"**——LLM 负责理解任务与给出语义参数（尺寸/拱高），
框架负责构造几何数据、执行第三方模块、做校验。这也是对车身设计场景最有现实意义的形态（AI 副驾）。

---

## 五、结论与下一步

1. **曲面**：Curves WB 是最值得集成的第三方模块（Gordon 曲面、斑马纹检查、双轨扫掠）；
   AI 已可驱动其生成曲面，但生产级 A 面仍不现实。
2. **装配**：建议下一步在 Assembly4（或原生 Assembly WB）上做同类集成实验（创建装配、LCS 约束）。
3. **AI 形态**：以"语义工具 + 框架几何构造 + 几何自校验"为基准模式；避免让 LLM 直接生成复杂几何数据。
4. **可做**：把 make_panel_surface 等语义工具沉淀进本仓库（见 examples/），逐步扩展工具面。

## 参考来源

- FreeCAD Addons 官方列表: https://www.freecad.org/addons.php
- Curves Workbench: https://github.com/tomate44/CurvesWB ｜ wiki: https://wiki.freecad.org/Curves_Workbench
- Assembly 模块选型: https://reqrefusion.github.io/FreeCAD-Documentation-html/wiki/Which_workbench_should_I_choose.html
- FreeCAD MCP 生态: https://mcp.directory/blog/freecad-mcp-complete-guide-2026 ｜ https://pypi.org/project/freecad-mcp/
- CAD-Assistant 论文: https://arxiv.org/pdf/2412.13810
- FreeCAD vs CATIA 对比: https://www.bestfreealternatives.com/alternatives/catia ｜ https://cadautoscript.com/blog/freecad-1x-open-source-cad/
