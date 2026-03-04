import { createApp } from 'vue'
import App from './App.vue'
import './style.css'
import axios from 'axios'

// 配置Axios默认值
axios.defaults.baseURL = 'http://localhost:5000/api'

const app = createApp(App)
app.config.globalProperties.$axios = axios
app.mount('#app')