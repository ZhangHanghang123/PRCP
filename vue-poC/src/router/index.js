import Vue from 'vue'
import VueRouter from 'vue-router'

Vue.use(VueRouter)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Index.vue'),
    meta: { title: '登录', public: true }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'coa',
        name: 'Coa',
        component: () => import('@/views/coa/Index.vue'),
        meta: { title: '账户册维护', icon: 'el-icon-share' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/Index.vue'),
        meta: { title: '报表表项管理', icon: 'el-icon-document' }
      },
      {
        path: 'kpi',
        name: 'Kpi',
        component: () => import('@/views/kpi/Index.vue'),
        meta: { title: '指标管理', icon: 'el-icon-data-line' }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Index.vue'),
        meta: { title: '驾驶舱', icon: 'el-icon-data-board' }
      },
      {
        path: 'metric-coefficient',
        name: 'MetricCoefficient',
        component: () => import('@/views/metric-coefficient/index.vue'),
        meta: { title: '指标计量系数', icon: 'el-icon-data-line' }
      },
      {
        path: 'reverse-metric-table',
        name: 'ReverseMetricTable',
        component: () => import('@/views/reverse-metric-table/index.vue'),
        meta: { title: '反算指标结果表', icon: 'el-icon-tickets' }
      },
      {
        path: 'sys',
        name: 'Sys',
        component: () => import('@/views/sys/Index.vue'),
        meta: { title: '系统管理', icon: 'el-icon-setting' }
      },
      {
        path: 'basic-data',
        name: 'BasicData',
        component: () => import('@/views/basic-data/Index.vue'),
        meta: { title: '基础数据维护', icon: 'el-icon-data-analysis' }
      },
      {
        path: 'reverse-data',
        name: 'ReverseData',
        component: () => import('@/views/reverse-data/Index.vue'),
        meta: { title: '反算基础数据', icon: 'el-icon-refresh' }
      }
    ]
  }
]

const router = new VueRouter({
  mode: 'history',
  base: '/prcp-java/',
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('prcp-java-token')
  if (to.meta.public) {
    next()
  } else if (!token) {
    next('/login')
  } else {
    next()
  }
})

export default router
