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
    redirect: '/coa',
    children: [
      {
        path: 'coa',
        name: 'Coa',
        component: () => import('@/views/coa/Index.vue'),
        meta: { title: '账户册维护', icon: 'el-icon-share' }
      }
      // 后续模块在此添加
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
