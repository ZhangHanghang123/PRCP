# PRCP Vue2 前端 — ElementUI 版

> 项目代号: prcp-vue
> 启动日期: 2026-09-23
> 技术栈: Vue 2.7.16 + ElementUI 2.15.14 + ECharts 5.4.3 + Vuex 3 + Vue Router 3

## 项目结构

```
prcp-vue/
├── package.json
├── vue.config.js                    # 公共路径 /prcp-java/
├── babel.config.js
├── .env.development                 # baseURL=/prcp-java/api
├── .env.production
├── public/
│   ├── index.html
│   └── prcp_icon.svg
└── src/
    ├── main.js                      # 入口（注册 ElementUI）
    ├── App.vue
    ├── router/index.js              # vue-router 3
    ├── store/
    │   ├── index.js
    │   └── modules/user.js          # Vuex user 模块
    ├── api/
    │   ├── request.js               # axios 实例 + 拦截器
    │   ├── auth.js                  # 登录接口
    │   └── coa.js                   # 账户册接口
    ├── utils/auth.js                # token 工具
    ├── layouts/MainLayout.vue       # 主布局（侧边栏 + 顶部 + 内容）
    ├── views/
    │   ├── login/Index.vue          # 登录页
    │   └── coa/Index.vue            # 账户册页面（树形 CRUD）
    ├── styles/index.scss            # 全局样式
    └── components/                  # 待补充
```

## 已实现功能（PoC v1.0）

| 页面 | 路径 | 功能 |
|------|------|------|
| 登录 | `/login` | 用户名密码登录，JWT 存 localStorage |
| 主布局 | `/` | 侧边栏 + 顶部 + 内容区 |
| 账户册 | `/coa` | 方案下拉 + 树形表格 + 新增/编辑/删除 |

## 环境要求

| 工具 | 版本 |
|------|------|
| Node.js | 16+ (推荐 18) |
| npm | 8+ |

## 本地开发

```bash
# 1. 安装依赖
cd C:\银行经营\prcp-vue
npm install

# 2. 启动开发服务器（dev 默认 localhost:8080）
npm run serve

# 浏览器打开：http://localhost:8080/prcp-java/

# 注意：访问路径必须带 /prcp-java/ 前缀，因为 vue.config.js 设置了 publicPath
```

## 生产构建

```bash
npm run build

# 产物位置：dist/
# - dist/index.html
# - dist/static/js/*.js
# - dist/static/css/*.css
```

## 部署到服务器

```bash
# 1. 上传 dist 到服务器
scp -r dist/* almd@43.143.253.186:/tmp/prcp-vue-dist/
scp -r dist/static almd@43.143.253.186:/tmp/prcp-vue-dist/static
ssh almd@43.143.253.186 'echo "almd" | sudo -S bash -c "mkdir -p /var/www/prcp-java; rm -f /var/www/prcp-java/static/js/*.js /var/www/prcp-java/static/css/*.css; cp -r /tmp/prcp-vue-dist/* /var/www/prcp-java/; cp -r /tmp/prcp-vue-dist/static /var/www/prcp-java/"'

# 2. 验证
curl -sk https://wxfzhh.online/prcp-java/ | head -5
```

## nginx 配置

```nginx
# /etc/nginx/sites-enabled/wxfzhh.online

# Java 版前端
location /prcp-java/ {
    alias /var/www/prcp-java/;
    try_files $uri $uri/ /prcp-java/index.html;
}

# Java 版 API（8008 端口）
location /prcp-java/api/ {
    proxy_pass http://127.0.0.1:8008/prcp-java/api/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 双版本并行

| 路径 | 后端 | 端口 |
|------|------|------|
| `/prcp/` | Python FastAPI | 8006 |
| `/prcp/api/` | Python FastAPI | 8006 |
| `/prcp-java/` | **Java SpringBoot** | **8008** |
| `/prcp-java/api/` | **Java SpringBoot** | **8008** |

**互不冲突**：
- 用户访问 `wxfzhh.online/prcp/` → 看到 Python 版
- 用户访问 `wxfzhh.online/prcp-java/` → 看到 Java 版
- 两个版本共享同一数据库

## 关键技术细节

### 公共路径

`vue.config.js` 设置 `publicPath: '/prcp-java/'`，所有静态资源会带上前缀。

### 路由 base

```javascript
// src/router/index.js
export default new VueRouter({
  mode: 'history',
  base: '/prcp-java/',
  routes
})
```

### axios baseURL

```javascript
// src/api/request.js
baseURL: process.env.VUE_APP_BASE_API  // = '/prcp-java/api'
```

### ElementUI 全局尺寸

```javascript
Vue.use(ElementUI, { size: 'small' })
```

## 与 Python/React 版对比

| 维度 | React 版 | Vue 版 |
|------|---------|--------|
| 框架 | React 18 + TS | Vue 2.7 + JS |
| UI 库 | Ant Design 5 | ElementUI 2 |
| 状态 | useState/Zustand | Vuex 3 |
| 路由 | react-router-dom 6 | vue-router 3 |
| 构建 | Vite 5 | webpack 4 (vue-cli 5) |
| 公共路径 | `/prcp/` | `/prcp-java/` |
| API 路径 | `/prcp/api/` | `/prcp-java/api/` |

## 下一步规划

| 阶段 | 内容 | 状态 |
|------|------|------|
| Phase 1（当前） | 登录 + 账户册 | ✅ 完成 |
| Phase 2 | 报表 + 指标 + 字典 + 驾驶舱 | 待开发 |
| Phase 3 | 数据维护 + 模型 + 反算 | 待开发 |
| Phase 4 | 利率 + 模拟 + ESG | 待开发 |
| Phase 5 | 切流 + 收尾 | 待开发 |

## 维护者

- 主开发：PRCP WorkBuddy Agent
- 启动日期：2026-09-23
- 仓库：`github.com:ZhangHanghang123/PRCP-Vue.git`（待创建）