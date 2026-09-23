/**
 * Vue CLI 配置
 */
const { defineConfig } = require('@vue/cli-service')

module.exports = defineConfig({
  transpileDependencies: true,
  publicPath: '/prcp-java/',
  outputDir: 'dist',
  lintOnSave: false,
  productionSourceMap: false,

  devServer: {
    port: 8080,
    open: false,
    proxy: {
      '/prcp-java/api': {
        target: 'http://127.0.0.1:8008',
        changeOrigin: true,
        pathRewrite: { '^/prcp-java/api': '/prcp-java/api' }
      }
    }
  },

  configureWebpack: {
    performance: { hints: false }
  }
})
