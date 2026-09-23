<template>
  <el-container class="main-layout">
    <!-- 顶部 -->
    <el-header class="header">
      <div class="header-left">
        <i class="el-icon-bank" style="font-size: 24px; color: #C7000B;"></i>
        <span class="gradient-text" style="font-size: 18px; font-weight: bold; margin-left: 8px;">PRCP · Java 版</span>
      </div>
      <div class="header-right">
        <el-dropdown @command="onCommand">
          <span class="user-info">
            <i class="el-icon-user-solid"></i>
            {{ user ? user.real_name || user.username : '未登录' }}
            <i class="el-icon-arrow-down"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
      </div>
    </el-header>

    <el-container>
      <!-- 侧边栏 -->
      <el-aside width="220px" class="aside">
        <el-menu :default-active="$route.path" router>
          <el-menu-item index="/dashboard">
            <i class="el-icon-data-board"></i>
            <span slot="title">驾驶舱</span>
          </el-menu-item>
          <el-menu-item index="/coa">
            <i class="el-icon-share"></i>
            <span slot="title">账户册维护</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <i class="el-icon-document"></i>
            <span slot="title">报表表项管理</span>
          </el-menu-item>
          <el-menu-item index="/kpi">
            <i class="el-icon-data-line"></i>
            <span slot="title">指标管理</span>
          </el-menu-item>
          <el-menu-item index="/metric-coefficient">
            <i class="el-icon-data-analysis"></i>
            <span slot="title">指标计量系数</span>
          </el-menu-item>
          <el-menu-item index="/reverse-metric-table">
            <i class="el-icon-tickets"></i>
            <span slot="title">反算指标结果表</span>
          </el-menu-item>
          <el-menu-item index="/sys">
            <i class="el-icon-setting"></i>
            <span slot="title">系统管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <!-- 主内容 -->
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
import { mapGetters } from 'vuex'

export default {
  name: 'MainLayout',
  computed: { ...mapGetters('user', ['user']) },
  methods: {
    onCommand(cmd) {
      if (cmd === 'logout') {
        this.$confirm('确认退出？', '提示', { type: 'warning' })
          .then(() => {
            this.$store.dispatch('user/logout')
            this.$router.push('/login')
          })
          .catch(() => {})
      }
    }
  }
}
</script>

<style scoped>
.main-layout { height: 100vh; }
.header {
  background: #fff;
  border-bottom: 2px solid #C7000B;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
  height: 56px;
}
.header-left { display: flex; align-items: center; }
.user-info {
  cursor: pointer;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
}
.aside {
  background: #fff;
  border-right: 1px solid #e8e8e8;
}
.el-menu { border-right: 0; }
.el-main { padding: 0; background: #f0f2f5; overflow: auto; }
</style>
