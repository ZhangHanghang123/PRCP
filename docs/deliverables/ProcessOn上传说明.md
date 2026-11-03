# PRCP 组合反算主流程 — Visio 图交付说明

## 一、交付物

| 文件 | 用途 |
|---|---|
| `PRCP组合反算主流程.vsdx` | **ProcessOn 上传用主文件**（Visio 2013+ 格式，ZIP 封装） |
| `PRCP组合反算主流程_preview.png` | 150 DPI 位图，发微信/汇报直接看 |
| `PRCP组合反算主流程_preview.svg` | 矢量图，可插 PPT / Word，任意放大不糊 |
| `PRCP组合反算主流程_preview.html` | 单文件预览页，离线可开、可打印 A3 |
| `PRCP组合反算主流程_data.json` | 中间数据，改文案后可跳过 Excel 直接重生成 |
| `PRCP组合反算主流程_流程表.xlsx` | 流程表源文件（改口径改这里） |

## 二、上传 ProcessOn 的操作

1. 登录 [processon.com](https://www.processon.com/)
2. 左侧「我的文件」→ 左上角「新建」→ **导入**
3. 选择 `PRCP组合反算主流程.vsdx`
4. 导入后自动生成为流程图文件，形状/连接线/文字均可**单独选中继续编辑**

> **格式说明**：ProcessOn 官方支持导入 `xmind / mmap / mm / km / txt / opml / pos / vsd / csv / xls / xlsx`。
> Visio 侧 2020 年起原生支持 `.vsdx`（旧版 `.vsd` 反而不支持），本文件即 `.vsdx`。
> 导入后若发现字体偏差，是 Visio 与 ProcessOn 的字体渲染差异，右侧样式面板可调。

## 三、图的内容

- **页面**：A3 横向（17×11 英寸）
- **阶段**：7 个（列头 chevron）—— 方案发起 → 数据准备 → 新业务模拟 → 任务下发 → 模型反算 → 指标计量 → 结果输出
- **操作项**：28 个，每个一张卡片，无合并、无省略
- **角色泳道**：7 个，颜色全局一致，图例完整列出

| 角色 | 负责环节 | 主要表/引擎 |
|---|---|---|
| 业务人员 | 方案发起（6 项） | prcp_reverse_scheme / prcp_model |
| 数据准备服务 | 数据准备（3 项） | prcp_coa_node / prcp_data_basic |
| 新业务模拟引擎 | 新业务模拟（6 项） | sim_scheme / sim_growth_config / sim_rhythm / sim_term_ratio |
| 计量引擎 | 任务下发（1 项） | prcp_reverse_scheme/run |
| 计量模型引擎 | 模型反算（4 项） | NONLINEAR_SOLVER / ANT_COLONY / DNN_NEURAL_NETWORK |
| 指标计量引擎 | 指标计量（4 项） | prcp_kpi_definition / prcp_data_basic |
| 反算驾驶舱 | 结果输出（4 项） | reverse_result / prcp_reverse_target |

内容取自 `PRCP/docs/PRCP系统整理流程图.html` 的「0.2 泳道总图」，口径与该文档一致。

## 四、改图 / 重出

**改口径（角色、环节、说明文字）→ 改 Excel，重跑：**

```bash
cd C:/银行经营/PRCP/docs
python build_prcp_flow_table.py    # 改这个脚本里的 ROWS 再跑，生成流程表
python "C:/Users/zhanghh/.workbuddy/skills/visio-flow-generator/scripts/run.py" \
  --input "C:/银行经营/PRCP/docs/PRCP组合反算主流程_流程表.xlsx" \
  --output-dir "C:/银行经营/PRCP/docs/deliverables" \
  --theme bank-blue --name "PRCP组合反算主流程"
```

**只改文案（不重读 Excel）→ 改 `_data.json` 后重生成：**

```bash
cd C:/银行经营/PRCP/docs/deliverables
python "C:/Users/zhanghh/.workbuddy/skills/visio-flow-generator/scripts/generate_vsdx.py" \
  --input PRCP组合反算主流程_data.json --output PRCP组合反算主流程.vsdx --theme bank-blue
```

**PNG 需用系统 Python 3.14**（WorkBuddy 自带 3.13 的 pip 损坏）：

```bash
C:/Users/zhanghh/AppData/Local/Programs/Python/Python314/python.exe \
  "C:/Users/zhanghh/.workbuddy/skills/visio-flow-generator/scripts/export_png.py" \
  --input PRCP组合反算主流程_data.json --output PRCP组合反算主流程_preview.png
```

主题可选：`bank-blue`（默认，银行蓝）/ `tech-gray`（科技灰）/ `consulting-navy`（咨询藏青）。

## 五、质量验收记录

**权威验证：本机 Microsoft Visio 2013（15.0.5597）COM 实测打开通过**

| 项 | 结果 |
|---|---|
| **Visio 2013 打开** | ✅ 成功，81 shapes / 47 含文本 / 27 条 1D 连接线 |
| **Visio 另存** | ✅ 成功（结构被完整解析） |
| **Visio 导出渲染** | ✅ 成功 |
| 页面尺寸 | 17.00 × 11.00 in（Visio 读出值正确） |
| OPC 打包 | ✅ `[Content_Types].xml` 为首个条目且不压缩（ISO/IEC 29500-2 要求） |
| ContentTypes | ✅ document / pages / **page1** / windows 全部声明 |
| 关系链 | ✅ 全部闭合，每个 Target 存在 |
| VisioDocument 子元素顺序 | ✅ DocumentSettings→Colors→FaceNames→StyleSheets→DocumentSheet |
| Shape 子元素顺序 | ✅ 全部为 Cell*→Section*→Text（Visio 官方 schema 要求） |
| 命名空间前缀 | ✅ `r:id` / `xmlns:r` 全部正确 |
| XML 合法性 | ✅ 全部可解析 |
| 第三方 vsdx 库 | ✅ 成功打开 |
| 文字溢出 | ✅ 无 |
| 图例完整性 | ✅ 7 个角色全列出，颜色与卡片一致 |
| 页脚 | ✅ 来源 + 绘制日期齐全 |

三套自动化测试：
- `test_visio_layout_fix.py` — 布局算法 21 条断言 ✅
- `verify_vsdx_compat.py` — 文件结构 43 条断言（对照真实 Visio 文件）✅
- `verify_text_render.py` — 文本还原 + 连线几何 10 条断言（含第三方库交叉验证）✅
- `verify_with_visio.py` — Visio COM 实开 8 条断言（含"卡片首行非空 28/28"）✅

## 六、本次修复的 skill 缺陷（影响后续所有出图）

`~/.workbuddy/skills/visio-flow-generator/` 原脚本备份在 `scripts/_backup_20261102/`。

### A. 布局类（文字溢出）

1. **分栏后卡高未按子栏宽度重算** → 文字溢出卡片。
   `plan_column()` 改用宽度感知的迭代规划，选定栏数后按该栏宽度重算卡高。
2. **`max(6, ...)` 折行下限无视物理宽度** → 窄栏横向溢出 50%。
   改用 `card_units(card_w, pt)` 按卡片实际可排版宽度计算上限。
3. **wrap() 按字符数硬切** → 英文表名被折成碎字。
   改为按视觉宽度折行（中文 1.0 / 半角 0.5~0.6）。

### B. 文件格式类（**导致 Visio 打不开**）

4. **`<Rel ID="rId1">` 缺 `r:` 命名空间** → 第三方解析器直接崩溃。
   改为 `<Rel r:id="...">` 并在 `Pages` 根元素声明 `xmlns:r`。
5. **Shape 内 `Text` 出现在 `Section` 之前** → 违反 Visio schema 的
   `Cell* , Trigger* , Section* , Text?` 顺序，Visio 判文件损坏。
   Geometry/Character/Paragraph 三个 Section 统一排在 Text 之前。
6. **`[Content_Types].xml` 缺 pageN.xml 的 Override** → 页面部件类型不对，
   Visio 识别不出页面 → 报「文件已损坏」。补 `application/vnd.ms-visio.page+xml`。
7. **缺 `visio/windows.xml` 部件及对应关系** → 补齐（Visio 打开必需）。
8. **`document.xml` 根元素缺 `xmlns:r`** → 补齐。
9. **`<Sheet>` 元素名错误** → Visio 规范用 `DocumentSheet`，改名并补属性。
10. **`[Content_Types].xml` 非 ZIP 首个条目且被压缩** → 违反 OPC 规范，
    改为第一个写入且 `ZIP_STORED` 不压缩。
11. **连接线不是 1D connector** → Visio 里拖动不吸附。
    补 `1D=1` / `BeginX,Y` / `EndX,Y`，实测 27 条全部被 Visio 识别为一维连接线。

### C. 渲染类（**导致箭头歪、文字不显示、连线没连上**）

12. **连接线用 `Angle=atan2` 表达方向 + `Height=0`** → Visio 的线是**矩形**，
    方向由 `Width/Height` 表达（`Height` 可为负），`Angle` 应为 **0**。
    错误写法会让线跑到错误位置（散落在空白处的短斜线）。
    依据：本机 Visio 2013 另存样本逐项比对（`references/vsdx-format.md` §5.1）。
13. **连接线 Geometry 用相对坐标** → 1D 形状的绘制基准是 Begin/End 绝对坐标，
    相对坐标基准不一致 → 线被画歪。改用绝对坐标 `MoveTo/LineTo`。
14. **Text 的 cp/pp 标记序列不合规** → 违反 Visio 三条硬规则
    （IX 连续递增 / `<pp>` 只在段首且其后换行 / 段内不手工折行），
    Visio 加载时「规范化」文本 → **卡片首行（操作名）丢失、文字被竖排到框外**。
    改为官方标准范式：
    ```
    <Text><cp IX="0"/>操作名
    <pp IX="0"/><cp IX="1"/>责任人：xxx
    <pp IX="0"/><cp IX="2"/>备注</Text>
    ```
    一张卡片 = 3 个段落，段内折行**交给 Visio 自动处理**（不手工插 `\n`）。
15. **阶段间箭头画在泳道顶部空白处**（0.06 英寸装饰短线）→ 视觉上就是
    「散落在空白里、没连上」。改为**从上一列最后一张卡片连到下一列第一张卡片**，
    走「横向 → 纵向 → 横向」三段正交折线，垂直段落在两列空隙里，
    只有最后一段带箭头。

### 后续出图注意

- 操作项一列超过 6 个时，该列会自动分 2~3 个子栏，卡片会变窄、折行变密 —— 属预期行为。
- 卡片文案宜短：**「操作」控制在 12 字以内、备注控制在 16 字以内**（整列宽时的物理上限），超出会自动折行。
- 若要长文，放备注或拆成两个操作项，别指望加宽。
- **改完 skill 后必须跑四套验证再交付**：
  `test_visio_layout_fix.py`（布局）→ `verify_vsdx_compat.py`（结构）
  → `verify_text_render.py`（文本与连线）→ `verify_with_visio.py`（Visio 实开）。

