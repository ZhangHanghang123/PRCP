# PRCP 技术栈迁移方案 — Vue2 + ElementUI + ECharts + SpringBoot

> 文档版本: v1.0  |  日期: 2026-09-23  |  作者: PRCP WorkBuddy Agent
> 状态: 方案设计完成，待评审立项

---

## 一、迁移目标

将 PRCP 模块从当前 **FastAPI + SQLAlchemy + React 18 + AntD + Vite** 技术栈，
迁移至 **SpringBoot 2.7 + MyBatis + Vue 2.7 + ElementUI 2 + ECharts 5** 技术栈。

### 1.1 业务目标

| 目标 | 说明 |
|------|------|
| **企业级 Java 栈** | 满足银行/金融机构对 Java 技术栈的偏好（人才招聘、生态成熟、运维标准化） |
| **Vue2 + ElementUI** | 贴合国内银信类项目主流前端栈（UI 库经典稳定，文档齐全） |
| **ECharts 集成** | 复用金融图表生态（曲线/热力图/雷达图等 80+ 图表类型） |
| **完全数据兼容** | DDL 不变，所有 30+ 张表不动；前端用户无感切换 |
| **API 接口兼容** | 接口路径 /prcp/api/* 完全保留，前端零感知切换 |

### 1.2 迁移原则

| 原则 | 含义 |
|------|------|
| **接口先行** | 优先稳定 OpenAPI 契约，前后端并行开发 |
| **数据不动** | DDL SQL 不变，迁移过程数据库 0 风险 |
| **业务等价** | 算法包（sim/reverse/esg）必须业务等价，回归测试通过 |
| **渐进迁移** | 推荐分阶段切换，旧版（Python/React）作为兜底 |
| **并行运行** | 迁移期间新旧两套可同时运行（不同端口），便于灰度切流 |

---

## 二、技术栈对比

### 2.1 后端对比

| 维度 | 当前（Python） | 目标（Java） | 优势/取舍 |
|------|---------------|-------------|-----------|
| 框架 | FastAPI 0.110 | SpringBoot 2.7.x | Java 企业级生态 |
| ORM | SQLAlchemy 2.0 | MyBatis 3 / MyBatis-Plus 3.5 | MyBatis SQL 可控；MP 简化 CRUD |
| 依赖注入 | FastAPI Depends | Spring @Autowired / @Resource | 标准化 |
| 异步 | asyncio (uvicorn) | CompletableFuture / @Async | Java 同步更易调试 |
| 校验 | Pydantic v2 | Jakarta Validation (Hibernate Validator) | 等价 |
| 配置 | .env / pydantic-settings | application.yml + @ConfigurationProperties | 等价 |
| JWT | python-jose | jjwt 0.11 / java-jwt | 等价 |
| 数据库 | MySQL 8 (PyMySQL) | MySQL 8 (Druid + mysql-connector-j) | 等价 |
| 缓存 | Redis (py-redis) | Spring Data Redis + Lettuce | 等价 |
| 日志 | loguru / uvicorn | logback / log4j2 | SLF4J 标准化 |
| 部署 | uvicorn + systemd | java -jar + systemd | 等价 |

### 2.2 前端对比

| 维度 | 当前（React） | 目标（Vue 2.7） | 取舍 |
|------|--------------|-----------------|------|
| 框架 | React 18 | Vue 2.7 | Vue 2 中文社区成熟 |
| UI 库 | Ant Design 5 | ElementUI 2.15 | ElementUI 银行业标配 |
| 图表 | ECharts 5 (echarts-for-react) | ECharts 5 (vue-echarts) | 同图表库 |
| 路由 | react-router-dom 6 | vue-router 3 | 等价 |
| 状态 | useState / Zustand | Vuex 3 | 等价 |
| HTTP | axios | axios | 复用 |
| 构建 | Vite 5 | webpack 4 (vue-cli 5) | Vite 启动快但 webpack 生态老 |
| 类型 | TypeScript | JavaScript（ES6+） | Vue 2 TS 集成较繁琐 |
| 日期 | dayjs | dayjs | 复用 |

---

## 三、PRCP 项目现状盘点

### 3.1 文件规模

| 类型 | 数量 | 规模评估 |
|------|------|----------|
| 后端 Python 文件 | 78 | ~15000 行 |
| 后端 Router 模块 | 21 | ~8000 行 |
| 后端算法/Service | ~15 | ~3000 行 |
| 后端 Scripts | 23 | ~5000 行 |
| 前端 Pages | 27 | ~12000 行 |
| 前端 Components | ~10 | ~2000 行 |
| 数据库表 | 30+ | — |
| E2E 测试 | 13 套 | ~3000 行 |
| **总计** | — | **约 5 万行** |

### 3.2 后端 Router 模块清单

| 模块 | 文件 | 核心接口数 | 迁移优先级 |
|------|------|-----------|----------|
| auth | `auth.py` | 3 | P0 |
| dashboard | `dashboard.py` | 3 | P0 |
| coa（账户册） | `coa.py` | 15 | P0 |
| reports（报表） | `reports.py` | 10 | P1 |
| kpi（指标） | `kpi.py` | 18 | P1 |
| data_maint | `data_maint.py` | 8 | P2 |
| model | `model.py` | 15 | P2 |
| reverse | `reverse.py` | 8 | P2 |
| data_reverse | `data_reverse.py` | 10 | P2 |
| engines（引擎） | `engines.py` | 4 | P2 |
| sim（模拟） | `sim.py` | 11 | P3 |
| rate（利率） | `rate.py` | 8 | P3 |
| esg（场景工厂） | `esg.py` | 22 | P3 |
| balance（资负） | `balance.py` | 5 | P2 |
| basic（基础数据） | `basic.py` | 6 | P2 |
| dict（字典） | `dict.py` | 5 | P1 |
| system | `admin.py` | 4 | P0 |
| **新加（本次迭代）** | | | |
| metric_coefficient | `metric_coefficient.py` | 9 | P0 |
| reverse_metric_table | （同 metric_coefficient） | 1 | P0 |
| reverse_dashboard | `reverse_dashboard.py` | 4 | P0 |

### 3.3 前端页面清单

| 模块 | 文件 | 路由 | 优先级 |
|------|------|------|--------|
| 登录 | `Login.tsx` | `/login` | P0 |
| Dashboard 驾驶舱 | `ReverseDashboard.tsx` | `/dashboard` | P0 |
| 账户册 | `COA.tsx` | `/coa` | P0 |
| 报表表项 | `Reports.tsx` | `/reports` | P1 |
| 指标管理 | `KPI.tsx`, `KpiScore.tsx` | `/kpi` | P1 |
| 数据维护 | `DataMaint.tsx`, `BalanceSheet.tsx`, `BasicDataSheet.tsx` | `/data-maint/:cat` | P2 |
| 模型管理 | `ModelManage.tsx` | `/model` | P2 |
| 组合反算 | `ReverseCalc.tsx`, `ReverseResult.tsx` | `/reverse`, `/data-maint/REVERSE` | P2 |
| 利率管理 | `RateCurve.tsx` | `/rate` | P3 |
| 新业务模拟 | `Sim*.tsx` | `/sim/*` | P3 |
| ESG | `Esg*.tsx` | `/esg/*` | P3 |
| **新加（本次迭代）** | | | |
| 指标计量系数 | `MetricCoefficient.tsx` | `/metric-coefficient` | P0 |
| 反算指标结果表 | `ReverseMetricTable.tsx` | `/reverse-metric-table` | P0 |
| 系统管理 | `System.tsx` | `/system` | P0 |

### 3.4 工作量评估（按优先级）

| 阶段 | 内容 | 估时（人天） |
|------|------|------------|
| P0 | 环境搭建 + 认证 + Dashboard + 账户册 + 指标计量系数 + 反算驾驶舱 | 12 |
| P1 | 报表 + 指标管理 + 字典 | 8 |
| P2 | 数据维护 + 模型 + 反算引擎 + 资负 | 18 |
| P3 | 利率 + 模拟 + ESG 算法包（最大头） | 22 |
| 收尾 | E2E 回归 + 部署 + 切换 | 5 |
| **合计** | — | **~65 人天**（单人约 3 个月） |

> 单纯迁移不算工作量，**算法包移植是最大坑**（HJM 月频版、Svensson 6 参数、PCA 因子等需要 Java 重写或调库）。

---

## 四、目录结构设计

### 4.1 后端 Spring Boot 多模块（推荐）

采用 Maven 多模块结构（金融项目标配）：

```
prcp-backend/                          # 父工程（POM）
├── pom.xml                            # 父 POM（统一版本管理）
├── prcp-common/                       # 通用模块
│   ├── src/main/java/com/prcp/common/
│   │   ├── constant/                  # 常量
│   │   ├── exception/                 # 全局异常
│   │   ├── result/                    # R<T> 统一响应
│   │   ├── utils/                     # 工具类（日期、加密、HTTP）
│   │   └── validation/                # 自定义校验注解
│   └── pom.xml
├── prcp-framework/                    # 框架模块
│   ├── src/main/java/com/prcp/framework/
│   │   ├── config/                    # MyBatis/Druid/Redis/Cors/Swagger 配置
│   │   ├── security/                  # JWT 拦截器/过滤器
│   │   ├── log/                       # 操作日志注解 + 切面
│   │   └── web/                       # 分页、全局异常处理器
│   └── pom.xml
├── prcp-system/                       # 系统模块（用户/角色/字典）
│   ├── src/main/java/com/prcp/system/
│   │   ├── controller/
│   │   ├── service/
│   │   ├── mapper/                    # MyBatis mapper 接口
│   │   ├── entity/                    # 实体类
│   │   └── dto/vo/
│   └── pom.xml
├── prcp-business/                     # 业务模块（账户册/指标/反算/...）
│   ├── src/main/java/com/prcp/business/
│   │   ├── coa/                       # 账户册
│   │   ├── reports/                   # 报表
│   │   ├── kpi/                       # 指标
│   │   ├── reverse/                   # 反算
│   │   ├── sim/                       # 模拟
│   │   ├── rate/                      # 利率
│   │   ├── esg/                       # ESG（含算法包）
│   │   ├── metric/                    # 指标计量系数
│   │   └── dashboard/                 # 驾驶舱
│   └── pom.xml
└── prcp-app/                          # 启动模块（聚合）
    ├── src/main/java/com/prcp/PrcpApplication.java
    ├── src/main/resources/
    │   ├── application.yml
    │   ├── application-dev.yml
    │   ├── application-prod.yml
    │   ├── mapper/                    # MyBatis XML 放这里（可选）
    │   └── logback-spring.xml
    └── pom.xml
```

### 4.2 前端 Vue2 工程

采用 vue-cli 5（webpack 4，ElementUI 兼容最佳）：

```
prcp-frontend/
├── package.json
├── vue.config.js                      # 代理 /prcp/api → http://localhost:8006
├── babel.config.js
├── .env.development
├── .env.production
├── public/
│   ├── index.html
│   └── prcp_icon.svg
└── src/
    ├── main.js                        # 入口
    ├── App.vue                        # 根组件
    ├── router/
    │   └── index.js                   # vue-router 配置
    ├── store/                         # Vuex
    │   ├── index.js
    │   ├── modules/
    │   │   ├── user.js                # 用户/token
    │   │   ├── app.js                 # 全局 app 状态
    │   │   └── dict.js                # 字典
    │   └── getters.js
    ├── api/                           # axios 封装 + 各模块 API
    │   ├── request.js                 # axios 实例 + 拦截器
    │   ├── auth.js
    │   ├── coa.js
    │   ├── reports.js
    │   ├── kpi.js
    │   ├── dataMaint.js
    │   ├── reverse.js
    │   ├── sim.js
    │   ├── rate.js
    │   ├── esg.js
    │   ├── metric.js
    │   └── dashboard.js
    ├── components/                    # 公共组件
    │   ├── SvgIcon/
    │   ├── PageContainer/
    │   ├── ECharts/                   # ECharts 通用封装（line/pie/bar/heatmap/radar）
    │   ├── DataTable/                 # 通用表格（含分页/筛选）
    │   ├── DictSelect/                # 字典下拉
    │   └── DateRangePicker/
    ├── layouts/
    │   └── MainLayout.vue             # 侧边栏菜单 + 头部 + 内容区
    ├── views/                         # 页面（对应路由）
    │   ├── login/Index.vue
    │   ├── dashboard/Index.vue
    │   ├── coa/
    │   │   ├── List.vue
    │   │   └── Tree.vue
    │   ├── reports/
    │   ├── kpi/
    │   ├── dataMaint/
    │   │   ├── Index.vue
    │   │   ├── financial.vue
    │   │   ├── param.vue
    │   │   └── ...
    │   ├── model/
    │   ├── reverse/
    │   ├── sim/
    │   ├── rate/
    │   ├── esg/
    │   ├── metric/
    │   └── system/
    ├── utils/                         # 工具函数
    │   ├── auth.js                    # token 存取
    │   ├── format.js                  # 数字/日期格式化
    │   ├── dict.js                    # 字典本地缓存
    │   └── validate.js
    ├── styles/
    │   ├── index.scss                 # 全局样式
    │   ├── element-variables.scss     # ElementUI 主题变量
    │   └── variables.scss
    └── assets/
```

---

## 五、迁移路线（5 阶段）

### Phase 1：基础搭建 + 试点（P0，12 人天）

**目标**：搭建 SpringBoot + Vue2 工程骨架，跑通 1 个完整模块（账户册）。

| 步骤 | 内容 | 估时 |
|------|------|------|
| 1.1 | 父工程 POM + 各 module pom | 0.5 |
| 1.2 | SpringBoot 启动类 + application.yml + Druid + MyBatis-Plus + Swagger | 1 |
| 1.3 | 统一响应 R<T> + 全局异常 + JWT 过滤器 + CORS | 1.5 |
| 1.4 | Vue2 项目脚手架 + 路由 + Vuex + axios 拦截器 + 登录页 | 1 |
| 1.5 | 账户册后端 Controller/Service/Mapper（树形 CRUD） | 2 |
| 1.6 | 账户册前端页面（ElementUI el-table + el-tree） | 2 |
| 1.7 | 数据准备 + 联调 + 部署验证 | 1 |
| 1.8 | nginx 配置 `/prcp-java/` 路径（与 Python 版并行） | 0.5 |
| 1.9 | 灰度切流：先 5% 用户切到新版，观察 3 天无问题逐步放量 | 2.5 |

**验收**：账户册模块功能与 Python 版完全一致，能登录、查树、加节点、改、删。

### Phase 2：核心模块（P0+P1，18 人天）

**目标**：完成 4 个 P0 + 3 个 P1 模块。

| 模块 | 估时 |
|------|------|
| 系统管理（用户/角色/字典） | 2 |
| Dashboard 驾驶舱（8 KPI + 5 指标趋势 + 热力图 + Top + 风险预警） | 4 |
| 指标计量系数维护（10 号） | 2 |
| 反算驾驶舱（同 Dashboard） | — |
| 反算指标结果表（11 号） | 1.5 |
| 报表表项管理 | 2 |
| 指标管理（方案/定义/试算） | 3 |
| 字典管理 | 1.5 |
| **小计** | 16 |

### Phase 3：业务模块（P2，18 人天）

| 模块 | 估时 |
|------|------|
| 数据维护（账务/参数/规模/价格/中收/RWA 共 8 类） | 6 |
| 资产负债表 | 2 |
| 基础数据表 | 2 |
| 模型管理 | 3 |
| 反算引擎（含 ROI 模型） | 3 |
| 反算结果查询 | 2 |
| **小计** | 18 |

### Phase 4：高级模块（P3，22 人天，最大坑）

| 模块 | 估时 | 难度 |
|------|------|------|
| 利率管理（采集 + 期限点 + 13 期限点） | 3 | ⭐⭐ |
| 新业务模拟（5 步算法引擎移植） | 5 | ⭐⭐⭐ |
| ESG 工厂 - Svensson 6 参数（Java 用 Apache Commons Math） | 3 | ⭐⭐⭐ |
| ESG 工厂 - PCA 因子分解（EigenValueDecomposition） | 2 | ⭐⭐ |
| ESG 工厂 - HJM 月频版（Java 矩阵运算） | 4 | ⭐⭐⭐⭐ |
| ESG 工厂 - 情景集管理（npz → MySQL LONGBLOB） | 2 | ⭐⭐ |
| ESG 工厂 - 前端页面（4 个） | 3 | ⭐⭐ |
| **小计** | 22 | — |

**算法包移植关键技术点**：

```java
// HJM 月频版（Java 版）
// 用 smilej-java 或 commons-math3 矩阵库
double dt = 1.0/12.0;  // 月频
double[][] volatility = new double[60][60];
// ... 移植 Python numpy 代码
```

```java
// Svensson 6 参数（Java 版）
// 用 Apache Commons Math 的 LevenbergMarquardtOptimizer
public double[] fitSvensson(double[] taus, double[] yields) {
    // θ0 + θ1*exp(-τ/λ1) + θ2*(τ/λ1)*exp(-τ/λ1) + θ3*(τ/λ2)*exp(-τ/λ2)
}
```

### Phase 5：收尾上线（5 人天）

| 步骤 | 内容 | 估时 |
|------|------|------|
| 5.1 | E2E 回归测试（13 套） | 2 |
| 5.2 | 性能压测（JMeter） | 1 |
| 5.3 | 100% 切流 + Python 版停服 + Git tag | 0.5 |
| 5.4 | 文档更新（README/CHANGELOG/部署指南） | 0.5 |
| 5.5 | 团队培训 + 运维交接 | 1 |

---

## 六、技术选型推荐

### 6.1 后端核心依赖（pom.xml）

```xml
<parent>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-parent</artifactId>
    <version>2.7.18</version>
</parent>

<dependencies>
    <!-- Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Validation -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-validation</artifactId>
    </dependency>

    <!-- AOP（操作日志切面） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-aop</artifactId>
    </dependency>

    <!-- Security（鉴权用） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>

    <!-- Redis -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>

    <!-- MyBatis-Plus（CRUD 简化） -->
    <dependency>
        <groupId>com.baomidou</groupId>
        <artifactId>mybatis-plus-boot-starter</artifactId>
        <version>3.5.5</version>
    </dependency>

    <!-- MySQL 驱动 -->
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <version>8.0.33</version>
    </dependency>

    <!-- Druid 连接池（带 SQL 监控） -->
    <dependency>
        <groupId>com.alibaba</groupId>
        <artifactId>druid-spring-boot-starter</artifactId>
        <version>1.2.20</version>
    </dependency>

    <!-- JWT -->
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-api</artifactId>
        <version>0.11.5</version>
    </dependency>
    <dependency>
        <groupId>io.jsonwebtoken</groupId>
        <artifactId>jjwt-impl</artifactId>
        <version>0.11.5</version>
        <scope>runtime</scope>
    </dependency>

    <!-- 矩阵运算（HJM/PCA/Svensson） -->
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-math3</artifactId>
        <version>3.6.1</version>
    </dependency>
    <dependency>
        <groupId>com.googlecode.efficient-java-matrix-library</groupId>
        <artifactId>EJML</artifactId>
        <version>0.41</version>
    </dependency>

    <!-- Swagger 3 -->
    <dependency>
        <groupId>org.springdoc</groupId>
        <artifactId>springdoc-openapi-ui</artifactId>
        <version>1.7.0</version>
    </dependency>

    <!-- Excel 导入导出 -->
    <dependency>
        <groupId>com.alibaba</groupId>
        <artifactId>easyexcel</artifactId>
        <version>3.3.4</version>
    </dependency>

    <!-- Hutool 工具集 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
        <version>5.8.22</version>
    </dependency>

    <!-- Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

### 6.2 前端核心依赖（package.json）

```json
{
  "dependencies": {
    "vue": "2.7.16",
    "vue-router": "3.6.5",
    "vuex": "3.6.2",
    "axios": "1.6.5",
    "element-ui": "2.15.14",
    "echarts": "5.4.3",
    "vue-echarts": "4.1.0",
    "dayjs": "1.11.10",
    "file-saver": "2.0.5",
    "xlsx": "0.18.5",
    "vuex-persistedstate": "4.1.0"
  },
  "devDependencies": {
    "@vue/cli-plugin-babel": "5.0.8",
    "@vue/cli-plugin-router": "5.0.8",
    "@vue/cli-plugin-vuex": "5.0.8",
    "@vue/cli-service": "5.0.8",
    "sass": "1.69.7",
    "sass-loader": "13.3.2"
  }
}
```

---

## 七、代码骨架（最小可运行示例）

### 7.1 后端：账户册模块完整骨架

#### 7.1.1 实体类

```java
package com.prcp.business.coa.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("prcp_coa_node")
public class CoaNode {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long schemeId;
    private String nodeCode;
    private String nodeName;
    private Long parentId;
    private Integer nodeLevel;
    private String path;
    private Integer sortOrder;
    private String status;
    private Integer isDeleted;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

#### 7.1.2 Mapper

```java
package com.prcp.business.coa.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.prcp.business.coa.entity.CoaNode;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;
import java.util.Map;

@Mapper
public interface CoaNodeMapper extends BaseMapper<CoaNode> {

    @Select("""
        SELECT id, node_code, node_name, parent_id, node_level, path
        FROM prcp_coa_node
        WHERE scheme_id = #{schemeId} AND is_deleted = 0
        ORDER BY path, sort_order
    """)
    List<Map<String, Object>> listByScheme(@Param("schemeId") Long schemeId);
}
```

#### 7.1.3 Service

```java
package com.prcp.business.coa.service;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.prcp.business.coa.entity.CoaNode;
import com.prcp.business.coa.mapper.CoaNodeMapper;
import com.prcp.common.result.R;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;

@Service
@RequiredArgsConstructor
public class CoaNodeService extends ServiceImpl<CoaNodeMapper, CoaNode> {

    private final CoaNodeMapper coaNodeMapper;

    public R<List<Map<String, Object>>> listTree(Long schemeId) {
        if (schemeId == null) {
            return R.fail("方案 ID 不能为空");
        }
        return R.ok(coaNodeMapper.listByScheme(schemeId));
    }

    public R<?> create(CoaNode node) {
        // 业务校验 + 自动填充 parent_id/path/node_level
        node.setIsDeleted(0);
        node.setStatus("ACTIVE");
        boolean ok = save(node);
        return ok ? R.ok(node) : R.fail("创建失败");
    }

    public R<?> update(Long id, CoaNode node) {
        node.setId(id);
        boolean ok = updateById(node);
        return ok ? R.ok() : R.fail("更新失败");
    }

    public R<?> softDelete(Long id) {
        boolean ok = removeById(id);
        return ok ? R.ok() : R.fail("删除失败");
    }
}
```

#### 7.1.4 Controller

```java
package com.prcp.business.coa.controller;

import com.prcp.business.coa.entity.CoaNode;
import com.prcp.business.coa.service.CoaNodeService;
import com.prcp.common.result.R;
import com.prcp.framework.security.PreAuthorize;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import javax.validation.Valid;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/prcp/api/coa")
@RequiredArgsConstructor
public class CoaController {

    private final CoaNodeService coaNodeService;

    /**
     * 账户册方案下的节点树（对应 Python GET /coa/nodes?scheme_id=...）
     */
    @GetMapping("/nodes")
    public R<List<Map<String, Object>>> nodes(@RequestParam Long schemeId) {
        return coaNodeService.listTree(schemeId);
    }

    /**
     * 创建节点（对应 Python POST /coa/node）
     */
    @PostMapping("/node")
    @PreAuthorize("hasAuthority('coa:write')")
    public R<?> createNode(@Valid @RequestBody CoaNode node) {
        return coaNodeService.create(node);
    }

    /**
     * 更新节点（对应 Python PUT /coa/node/{id}）
     */
    @PutMapping("/node/{id}")
    @PreAuthorize("hasAuthority('coa:write')")
    public R<?> updateNode(@PathVariable Long id, @Valid @RequestBody CoaNode node) {
        return coaNodeService.update(id, node);
    }

    /**
     * 删除节点（对应 Python DELETE /coa/node/{id}）
     */
    @DeleteMapping("/node/{id}")
    @PreAuthorize("hasAuthority('coa:write')")
    public R<?> deleteNode(@PathVariable Long id) {
        return coaNodeService.softDelete(id);
    }
}
```

#### 7.1.5 统一响应 R<T>

```java
package com.prcp.common.result;

import lombok.Data;
import java.io.Serializable;

@Data
public class R<T> implements Serializable {
    private Integer code;
    private String msg;
    private T data;

    public static <T> R<T> ok() { return ok(null); }
    public static <T> R<T> ok(T data) {
        R<T> r = new R<>();
        r.setCode(0);
        r.setMsg("OK");
        r.setData(data);
        return r;
    }
    public static <T> R<T> fail(String msg) {
        R<T> r = new R<>();
        r.setCode(500);
        r.setMsg(msg);
        return r;
    }
    public static <T> R<T> fail(int code, String msg) {
        R<T> r = new R<>();
        r.setCode(code);
        r.setMsg(msg);
        return r;
    }
}
```

#### 7.1.6 JWT 过滤器

```java
package com.prcp.framework.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;

@Component
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private static final String SECRET = "prcp-secret-key-2026";
    private static final String HEADER = "Authorization";
    private static final String PREFIX = "Bearer ";

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String header = req.getHeader(HEADER);
        if (header != null && header.startsWith(PREFIX)) {
            String token = header.substring(PREFIX.length());
            try {
                Claims claims = Jwts.parser()
                        .setSigningKey(SECRET.getBytes())
                        .parseClaimsJws(token)
                        .getBody();
                req.setAttribute("user_id", claims.get("user_id"));
                req.setAttribute("username", claims.getSubject());
            } catch (Exception e) {
                // token 无效 → 后续 Security 拦截
            }
        }
        chain.doFilter(req, res);
    }
}
```

### 7.2 前端：账户册模块完整骨架

#### 7.2.1 入口 main.js

```javascript
import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'
import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import './styles/index.scss'

Vue.use(ElementUI, { size: 'small' })
Vue.config.productionTip = false

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
```

#### 7.2.2 API 封装（axios）

```javascript
// src/api/request.js
import axios from 'axios'
import { Message } from 'element-ui'
import router from '@/router'
import { getToken } from '@/utils/auth'

const service = axios.create({
  baseURL: process.env.VUE_APP_BASE_API,
  timeout: 30000
})

service.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers['Authorization'] = `Bearer ${token}`
  return config
})

service.interceptors.response.use(
  response => {
    const res = response.data
    // 后端 R<T> 格式: { code, msg, data }
    if (res.code !== 0 && res.code !== 200) {
      Message.error(res.msg || '请求失败')
      if (res.code === 401) {
        router.push('/login')
      }
      return Promise.reject(res)
    }
    return res.data
  },
  error => {
    Message.error(error.message)
    return Promise.reject(error)
  }
)

export default service
```

```javascript
// src/api/coa.js
import request from './request'

export const coaApi = {
  listNodes: (schemeId) => request.get('/coa/nodes', { params: { scheme_id: schemeId } }),
  createNode: (data) => request.post('/coa/node', data),
  updateNode: (id, data) => request.put(`/coa/node/${id}`, data),
  deleteNode: (id) => request.delete(`/coa/node/${id}`),
  listSchemes: () => request.get('/coa/schemes')
}
```

#### 7.2.3 账户册页面

```vue
<!-- src/views/coa/Index.vue -->
<template>
  <div class="coa-page">
    <el-card>
      <!-- 顶部筛选 -->
      <el-row :gutter="20" class="filter-row">
        <el-col :span="6">
          <el-select v-model="filter.schemeId" placeholder="选择账户册方案"
                     @change="loadNodes" filterable>
            <el-option v-for="s in schemes" :key="s.id"
                       :label="`${s.scheme_code} | ${s.scheme_name}`"
                       :value="s.id" />
          </el-select>
        </el-col>
        <el-col :span="6">
          <el-input v-model="filter.keyword" placeholder="搜索节点编码/名称" clearable />
        </el-col>
        <el-col :span="12">
          <el-button type="primary" icon="el-icon-search" @click="loadNodes">查询</el-button>
          <el-button icon="el-icon-refresh" @click="onReset">重置</el-button>
          <el-button type="success" icon="el-icon-plus" @click="onAdd">新增节点</el-button>
        </el-col>
      </el-row>

      <!-- 表格 -->
      <el-table :data="filteredNodes" row-key="id" border default-expand-all
                :tree-props="{ children: 'children' }" v-loading="loading">
        <el-table-column prop="node_code" label="节点编码" width="180" />
        <el-table-column prop="node_name" label="节点名称" />
        <el-table-column prop="node_level" label="层级" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.node_level === 1 ? 'danger' : 'info'">L{{ row.node_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button type="text" @click="onEdit(row)">编辑</el-button>
            <el-button type="text" style="color: #f56c6c" @click="onDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 Modal -->
    <el-dialog :title="editing ? '编辑节点' : '新增节点'" :visible.sync="modalVisible" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="父节点" prop="parent_id">
          <el-cascader v-model="form.parent_path"
                       :options="cascaderOptions"
                       :props="{ checkStrictly: true, value: 'id', label: 'node_name' }"
                       clearable change-on-select />
        </el-form-item>
        <el-form-item label="节点编码" prop="node_code">
          <el-input v-model="form.node_code" />
        </el-form-item>
        <el-form-item label="节点名称" prop="node_name">
          <el-input v-model="form.node_name" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" @click="onSubmit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { coaApi } from '@/api/coa'

export default {
  name: 'CoaIndex',
  data() {
    return {
      filter: { schemeId: null, keyword: '' },
      schemes: [],
      nodes: [],
      loading: false,
      modalVisible: false,
      editing: null,
      form: { parent_path: [], node_code: '', node_name: '', sort_order: 0 },
      rules: {
        node_code: [{ required: true, message: '请输入节点编码' }],
        node_name: [{ required: true, message: '请输入节点名称' }]
      }
    }
  },
  computed: {
    filteredNodes() {
      const kw = this.filter.keyword.toLowerCase()
      if (!kw) return this.nodes
      const filter = (n) => {
        const matched = n.node_code.toLowerCase().includes(kw) || n.node_name.toLowerCase().includes(kw)
        const children = (n.children || []).filter(filter)
        if (matched || children.length) return { ...n, children }
        return null
      }
      return this.nodes.map(filter).filter(Boolean)
    },
    cascaderOptions() {
      const toOpts = (n) => ({
        id: n.id, node_name: n.node_code + ' ' + n.node_name,
        children: (n.children || []).map(toOpts)
      })
      return this.nodes.map(toOpts)
    }
  },
  mounted() {
    this.loadSchemes()
  },
  methods: {
    async loadSchemes() {
      this.schemes = await coaApi.listSchemes()
      if (this.schemes.length) {
        this.filter.schemeId = this.schemes[0].id
        this.loadNodes()
      }
    },
    async loadNodes() {
      if (!this.filter.schemeId) return
      this.loading = true
      try {
        const list = await coaApi.listNodes(this.filter.schemeId)
        this.nodes = this.buildTree(list)
      } finally { this.loading = false }
    },
    buildTree(list) {
      const map = new Map()
      list.forEach(n => map.set(n.id, { ...n, children: [] }))
      const roots = []
      list.forEach(n => {
        const node = map.get(n.id)
        if (n.parent_id && map.has(n.parent_id)) {
          map.get(n.parent_id).children.push(node)
        } else {
          roots.push(node)
        }
      })
      return roots
    },
    onReset() {
      this.filter.keyword = ''
      this.loadNodes()
    },
    onAdd() { this.editing = null; this.form = { parent_path: [], node_code: '', node_name: '', sort_order: 0 }; this.modalVisible = true },
    onEdit(row) { this.editing = row; this.form = { ...row }; this.modalVisible = true },
    onDelete(row) {
      this.$confirm(`确认删除 ${row.node_code}？`, '提示', { type: 'warning' })
        .then(async () => {
          await coaApi.deleteNode(row.id)
          this.$message.success('删除成功')
          this.loadNodes()
        })
        .catch(() => {})
    },
    async onSubmit() {
      await this.$refs.formRef.validate()
      const data = { ...this.form, scheme_id: this.filter.schemeId,
        parent_id: this.form.parent_path[this.form.parent_path.length - 1] || null }
      if (this.editing) {
        await coaApi.updateNode(this.editing.id, data)
      } else {
        await coaApi.createNode(data)
      }
      this.$message.success('保存成功')
      this.modalVisible = false
      this.loadNodes()
    }
  }
}
</script>

<style scoped>
.coa-page { padding: 16px; }
.filter-row { margin-bottom: 16px; }
</style>
```

#### 7.2.4 路由

```javascript
// src/router/index.js
import Vue from 'vue'
import VueRouter from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'

Vue.use(VueRouter)

const routes = [
  { path: '/login', component: () => import('@/views/login/Index.vue') },
  {
    path: '/',
    component: MainLayout,
    redirect: '/dashboard',
    children: [
      { path: 'dashboard', component: () => import('@/views/dashboard/Index.vue'), meta: { title: '驾驶舱' } },
      { path: 'coa', component: () => import('@/views/coa/Index.vue'), meta: { title: '账户册' } },
      // ... 其他 26 个路由
    ]
  }
]

export default new VueRouter({ mode: 'history', base: '/prcp-java/', routes })
```

#### 7.2.5 ECharts 通用组件

```vue
<!-- src/components/ECharts/LineChart.vue -->
<template>
  <div :ref="el" :style="{ height, width: '100%' }" />
</template>

<script>
import * as echarts from 'echarts'

export default {
  name: 'LineChart',
  props: {
    option: { type: Object, required: true },
    height: { type: String, default: '400px' }
  },
  data() { return { chart: null } },
  mounted() { this.chart = echarts.init(this.$refs.el); this.chart.setOption(this.option) },
  watch: {
    option: {
      deep: true,
      handler(val) { this.chart && this.chart.setOption(val, true) }
    }
  },
  beforeDestroy() { this.chart && this.chart.dispose() }
}
</script>
```

---

## 八、数据库兼容方案

### 8.1 DDL 保持不变

**原则**：30+ 张 `prcp_*` / `sys_*` / `prcp_*` 表 DDL 0 改动，全部复用。

### 8.2 ORM 选择对比

| 维度 | MyBatis | MyBatis-Plus | JPA/Hibernate |
|------|---------|--------------|---------------|
| SQL 控制 | ✅ 完全可控 | ⚠️ 部分封装 | ❌ 难定制 |
| 学习成本 | 中 | 低 | 高 |
| 动态 SQL | XML 拼接 | Lambda | HQL/Criteria |
| 复杂查询 | ✅ 写 XML | ✅ 写 XML | ⚠️ 麻烦 |
| CRUD 效率 | 低 | 高（BaseMapper） | 中 |
| **推荐** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

**结论**：**推荐 MyBatis-Plus**（基于 MyBatis + 自带 BaseMapper CRUD）+ 复杂查询写 XML。

### 8.3 分页统一封装

```java
// src/main/java/com/prcp/common/page/PageQuery.java
@Data
public class PageQuery {
    private Integer pageNum = 1;
    private Integer pageSize = 20;
    private String keyword;
    private String orderBy;

    public <T> Page<T> toPage() {
        return Page.of(pageNum, pageSize);
    }
}

// Controller 用法
@GetMapping("/list")
public R<PageResult<NodeVO>> list(@Valid PageQuery query) {
    Page<NodeVO> page = coaNodeService.page(query.toPage());
    return R.ok(PageResult.of(page));
}
```

---

## 九、API 兼容性设计

### 9.1 路径完全保留

**所有接口路径保持完全一致**：

| Python 版 | Java 版 |
|----------|---------|
| `GET /prcp/api/coa/nodes` | `GET /prcp/api/coa/nodes` ✅ |
| `POST /prcp/api/coa/node` | `POST /prcp/api/coa/node` ✅ |
| `GET /prcp/api/metric-coefficient/options` | `GET /prcp/api/metric-coefficient/options` ✅ |
| `GET /prcp/api/reverse-dashboard/snapshot` | `GET /prcp/api/reverse-dashboard/snapshot` ✅ |

### 9.2 响应格式统一

```json
{ "code": 0, "msg": "OK", "data": ... }
```

Java 端用 `R<T>` 完全对齐 Python 端的 `{"items": [...], "total": N}` 风格。

### 9.3 JWT Token 兼容

- 签名密钥保持 `prcp-secret-key-2026`
- Payload：`{sub: username, user_id, exp}`
- Token 格式：`Bearer eyJhbGc...`

### 9.4 nginx 路径分流

```nginx
# Python 版（8006 端口）
location /prcp/api/ {
    proxy_pass http://127.0.0.1:8006/prcp/api/;
}

# Java 版（8008 端口，新版）
location /prcp-java/api/ {
    proxy_pass http://127.0.0.1:8008/prcp/api/;
}
```

切流时改 location 块即可。

---

## 十、部署方案

### 10.1 后端 systemd 服务

```ini
# /etc/systemd/system/prcp-java.service
[Unit]
Description=PRCP Java Backend
After=network.target mysql.service

[Service]
Type=simple
User=almd
WorkingDirectory=/home/almd/prcp-java
ExecStart=/usr/bin/java -Xms1g -Xmx2g -jar prcp-app.jar --spring.profiles.active=prod
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 10.2 前端 nginx

```nginx
# /var/www/prcp-java/index.html
server {
    listen 443 ssl;
    server_name wxfzhh.online;
    # ...

    # 新版 Java 版
    location /prcp-java/ {
        alias /var/www/prcp-java/;
        try_files $uri $uri/ /prcp-java/index.html;
    }
    location /prcp-java/api/ {
        proxy_pass http://127.0.0.1:8008/prcp/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 10.3 前端 vue.config.js 代理

```javascript
module.exports = {
  publicPath: '/prcp-java/',
  outputDir: 'dist',
  devServer: {
    port: 8080,
    proxy: {
      '/prcp/api': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true
      }
    }
  }
}
```

---

## 十一、风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| 算法包业务不等价（HJM/Svensson/PCA） | 高 - 反算结果与 Python 不一致 | 单元测试 + 用同一份种子数据对比 Python/Java 输出，容差 ≤ 1e-6 |
| ESG 工厂 HJM 浮点精度 | 中 | 用 double + Decimal 校验；保留 Python 版 3 个月做对比 |
| JWT 不兼容导致登录失败 | 高 | Token 算法和密钥完全对齐 Python 版，登录态无缝切换 |
| 时间类型不一致（LocalDateTime vs datetime） | 中 | 全局 jackson 配置 `JavaTimeModule` + 时区 `Asia/Shanghai` |
| BigDecimal 序列化丢失精度 | 中 | 配置 `BigDecimal.toPlainString()` + scale |
| ElementUI 主题色与 AntD 不一致 | 低 | 用 element-variables.scss 定制蓝色主题 `#409EFF` |
| 27 个页面同步迁移工作量大 | 高 | 优先 P0（5 个核心页面），P3 阶段灵活安排 |
| 团队 Java 经验不足 | 中 | 培训 1 周 + Code Review + 参考阿里巴巴 Java 开发手册 |
| 老 Python 版继续运行时的数据并发 | 低 | 切流期间数据库双写不可行（旧版仍写、新版只读），需短暂只读模式 |

---

## 十二、成本估算

| 项目 | 估时（人天） | 备注 |
|------|------------|------|
| 单人全程 | ~65 | 3 个月 |
| 3 人并行 | ~30 | 1.5 个月 |
| 5 人并行 | ~20 | 1 个月 |

**总成本**：
- 人力：单人 3 个月 / 3 人 1.5 个月
- 服务器：复用现有 8006 端口，Java 跑在 8008 端口（无额外费用）
- 工具：IntelliJ IDEA + Visual Studio Code + Maven + JDK 17（已有）

---

## 十三、下一步行动

### 决策项（已确认）

| # | 决策点 | 选定方案 |
|---|--------|----------|
| 1 | 迁移策略 | **C. 双版本长期并行** ✅ |
| 2 | 后端 ORM | **A. MyBatis-Plus（推荐）** ✅ |
| 3 | Vue 版本 | **A. Vue 2.7.16（推荐）** ✅ |
| 4 | 下一步行动 | **A. 先做 PoC 验证（账户册模块）** ✅ |
| 5 | 团队规模 | — |
| 6 | 后端启动时间 | 立即启动 PoC |
| 7 | 数据库兼容 | DDL 完全不变（推荐） |
| 8 | JWT 密钥 | 复用 Python 版密钥（推荐） |

**双版本并行架构**：
- Python 版：`/prcp/api/*` → nginx → 8006
- Java 版：`/prcp-java/api/*` → nginx → 8008
- 数据库共享（DDL 不变）
- 前端两个独立工程：`/prcp/` 和 `/prcp-java/`

### 启动命令（一旦决策后）

```bash
# 1. 创建项目
cd /c/银行经营
mkdir prcp-java && cd prcp-java
# 使用 Spring Initializr 生成脚手架
# 或用 IDEA 新建项目

# 2. 创建 Git 仓库
git init
git remote add origin git@github.com:ZhangHanghang123/PRCP-Java.git

# 3. 第一个 demo 模块（账户册）
# ... 按 7.1 代码骨架实现

# 4. 联调 + 部署到 /var/www/prcp-java/
```

---

## 十四、关键建议

1. **优先 P0 业务线（驾驶舱 + 账户册 + 指标计量系数）**：用户最常用、最有价值
2. **接口契约先稳定**：用 OpenAPI 生成 Java Controller + Vue API + 文档，一气呵成
3. **数据库零改动**：避免双轨运行期间的数据不一致
4. **保留 Python 版 3 个月**：作为业务对照基准和回滚备份
5. **算法包移植必须 100% 业务等价**：用同一份种子数据逐算法对比，容差 ≤ 1e-6
6. **ElementUI 主题色定制**：与现有 PRCP 蓝紫渐变 `#667eea → #764ba2` 保持一致的品牌色
7. **充分利用 Vue 2 生态成熟度**：ElementUI、vue-echarts、vuex-persistedstate 都是久经考验
8. **Java 端用 JRebel 或 Spring DevTools**：开发热部署，提升效率
9. **E2E 用 RestAssured 或 JMeter**：替代 Python 的 urllib 脚本
10. **CI/CD 用 Jenkins / GitHub Actions**：自动化构建 + 部署

---

## 附录 A：技术选型 Checklist

```
✅ Java 17 LTS（OpenJDK 17.0.9）
✅ SpringBoot 2.7.18（最后稳定版，兼容 Java 8/11/17）
✅ MyBatis-Plus 3.5.5（CRUD 自动化）
✅ MySQL Connector/J 8.0.33
✅ Druid 1.2.20（连接池 + SQL 监控）
✅ JJWT 0.11.5（JWT 鉴权）
✅ Apache Commons Math 3.6.1（矩阵运算）
✅ EJML 0.41（轻量矩阵库，HJM 用）
✅ SpringDoc OpenAPI 1.7.0（接口文档）
✅ EasyExcel 3.3.4（Excel 导入导出）
✅ Hutool 5.8.22（Java 工具集）
✅ Lombok 1.18.30（样板代码）
✅ Vue 2.7.16（最后稳定版，Vue3 改 OOP 太多）
✅ ElementUI 2.15.14（Vue2 配套）
✅ ECharts 5.4.3（图表）
✅ Vue-Router 3.6.5（Vue2 配套）
✅ Vuex 3.6.2（Vue2 配套）
✅ Axios 1.6.5（HTTP）
✅ dayjs 1.11.10（日期）
```

## 附录 B：参考资料

- Spring Boot 官方文档：https://spring.io/projects/spring-boot
- MyBatis-Plus 文档：https://baomidou.com/
- ElementUI 文档：https://element.eleme.io/
- vue-echarts：https://github.com/ecomfe/vue-echarts
- EJML 文档：http://ejml.org/
- Apache Commons Math：https://commons.apache.org/proper/commons-math/
- 阿里巴巴 Java 开发手册：https://github.com/alibaba/p3c

---

> **结论**：方案已完整，5 阶段路线清晰，代码骨架可直接上手。**建议启动顺序**：先决策 → Phase 1 PoC（账户册 12 天）→ 验证可行性 → 全量推进。