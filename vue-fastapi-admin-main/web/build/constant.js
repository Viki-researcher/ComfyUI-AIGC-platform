export const OUTPUT_DIR = 'dist'

export const PROXY_CONFIG = {
  /**
   * @desc    不替换匹配值
   * @请求路径  http://localhost:3006/api/auth/login
   * @转发路径  http://127.0.0.1:9999/api/auth/login
   */
  '/api': {
    target: 'http://127.0.0.1:9999',
    changeOrigin: true,
  },
}
