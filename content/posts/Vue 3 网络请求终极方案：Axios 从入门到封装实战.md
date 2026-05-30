---
title: "Vue 3 网络请求终极方案：Axios 从入门到封装实战"
date: 2026-05-30T16:17:00+08:00
draft: false
images: ["/images/post/vue3-axios-guide.jpg"]
tags: ["Vue3", "Axios", "网络请求", "前端开发"]
categories: ["Vue"]
series: ["前端开发系列"]
author: "GW"
summary: "只会用 fetch？那是业余玩家。Axios 才是企业级 Vue 项目的标配。本文将带你通俗掌握 Axios 的核心用法、拦截器黑科技，以及如何在 Vue 3 项目中优雅地封装一个请求工具类。"
---

# Vue 3 网络请求终极方案：Axios 从入门到封装实战

在 Vue 3 应用中，数据通常存储在远程服务器上。我们需要一个“搬运工”来把数据搬到页面上，这个搬运工就是 **Axios**。

虽然浏览器自带 `fetch`，但 Axios 因为其强大的**拦截器**和**极简的语法**，成为了全球前端开发者的首选。

---

## 一、 快速上手：安装与第一次请求

### 1. 安装
```bash
npm install axios
```

### 2. 基础用法（以获取用户信息为例）
在 Vue 3 的 `<script setup>` 中，我们可以直接使用：

```vue
<script setup>
import axios from 'axios'
import { ref, onMounted } from 'vue'

const userList = ref([])

const getData = async () => {
  try {
    // 发送 GET 请求
    const res = await axios.get('https://api.example.com/users')
    userList.value = res.data // 注意：Axios 返回的数据在 .data 属性中
  } catch (error) {
    console.error('请求失败了：', error)
  }
}

onMounted(() => getData())
</script>
```

---

## 二、 拦截器：请求与响应的“安检员”

这是 Axios 最牛的功能。你可以把它想象成机场安检：

### 1. 请求拦截器 (Request Interceptor) —— “出发前检查”
比如：每次请求都在 Header 里自动塞入 `token`。

```javascript
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})
```

### 2. 响应拦截器 (Response Interceptor) —— “回来后过滤”
比如：如果服务器返回 401（未登录），直接让页面跳转到登录页。

```javascript
axios.interceptors.response.use(
  response => response.data, // 以后在组件里直接拿数据，不用再写 .data
  error => {
    if (error.response.status === 401) {
      alert('登录失效，请重新登录')
      // 跳转逻辑...
    }
    return Promise.reject(error)
  }
)
```

---

## 三、 实战：Vue 3 项目中的优雅封装

不要在每个组件里都去引入 `axios`。更专业的方式是建立一个统一的 `request.js`。

### 1. 封装工具类 (`src/utils/request.js`)
```javascript
import axios from 'axios'

// 创建实例
const service = axios.create({
  baseURL: 'https://api.example.com', // 统一的基础路径
  timeout: 5000 // 超时时间
})

// ... 这里加上上面提到的拦截器代码 ...

export default service
```

### 2. 统一管理接口 (`src/api/user.js`)
```javascript
import request from '@/utils/request'

export const login = (data) => {
  return request({
    url: '/login',
    method: 'post',
    data
  })
}
```

### 3. 组件中引用
```javascript
import { login } from '@/api/user'

const handleLogin = async () => {
  const res = await login({ username: 'GW', password: '123' })
  console.log('登录成功：', res)
}
```

---

## 四、 避坑指南：Axios 的那些“坑”

1. **多写了一个 .data**：
   默认情况下，Axios 的返回结果包裹在 `res.data` 中。如果你在拦截器里做了解构 `response => response.data`，那组件里就**千万别再多写一次**了。
2. **跨域问题 (CORS)**：
   这是浏览器处于安全考虑的限制。解决办法通常是：
   - 后端配置 CORS。
   - 开发环境下在 `vite.config.js` 中配置 `proxy`（代理）。
3. **POST 请求传参**：
   - `params`：拼在 URL 后面（如 `?id=1`）。
   - `data`：放在请求体里（用于发送 JSON）。**大部分 POST 接口用 data。**

---

## 五、 总结

Axios 是 Vue 3 项目的生命线：
- **安装简单**，语义化强。
- **拦截器** 解决了重复劳动（Token、错误处理）。
- **统一封装** 让代码更易维护。

掌握了 Axios 的封装，你就能写出结构漂亮、逻辑清晰的企业级前端代码。

> （注：本文由 GW 整理。数据搬运工，也要搬得优雅！）
