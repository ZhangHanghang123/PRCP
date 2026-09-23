<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1 class="gradient-text">PRCP · Java 版</h1>
        <p>银行经营智能分析平台（SpringBoot + Vue2）</p>
      </div>
      <el-form ref="formRef" :model="form" :rules="rules" @submit.native.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" prefix-icon="el-icon-user" placeholder="用户名" size="large" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" prefix-icon="el-icon-lock"
                    type="password" placeholder="密码" size="large" show-password
                    @keyup.enter.native="onSubmit" />
        </el-form-item>
        <el-button type="primary" :loading="loading" @click="onSubmit" size="large" style="width: 100%">
          登录
        </el-button>
      </el-form>
      <div class="login-footer">
        <span>默认账号：admin / admin123</span>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'LoginIndex',
  data() {
    return {
      form: { username: 'admin', password: 'admin123' },
      rules: {
        username: [{ required: true, message: '请输入用户名' }],
        password: [{ required: true, message: '请输入密码' }]
      },
      loading: false
    }
  },
  methods: {
    onSubmit() {
      this.$refs.formRef.validate(async valid => {
        if (!valid) return
        this.loading = true
        try {
          await this.$store.dispatch('user/login', this.form)
          this.$message.success('登录成功')
          this.$router.push('/coa')
        } catch (e) {
          // 错误已由拦截器提示
        } finally {
          this.loading = false
        }
      })
    }
  }
}
</script>

<style scoped>
.login-page {
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  justify-content: center;
  align-items: center;
}
.login-card {
  width: 400px;
  padding: 40px 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.2);
}
.login-header {
  text-align: center;
  margin-bottom: 32px;
}
.login-header h1 {
  font-size: 28px;
  margin: 0 0 8px;
}
.login-header p {
  color: #999;
  font-size: 13px;
  margin: 0;
}
.login-footer {
  text-align: center;
  margin-top: 16px;
  font-size: 12px;
  color: #aaa;
}
</style>
