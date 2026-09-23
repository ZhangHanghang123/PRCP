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
