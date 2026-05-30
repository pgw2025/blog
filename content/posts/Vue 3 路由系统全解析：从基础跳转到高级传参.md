---
title: "Vue 3 路由系统全解析：从基础跳转到高级传参"
date: 2026-05-30T12:50:00+08:00
draft: false
images: ["/images/post/vue-router-guide.jpg"]
tags: ["Vue3", "Vue Router", "前端开发", "单页应用"]
categories: ["前端开发", "Vue"]
series: ["前端开发系列"]
author: "GW"
summary: "单页应用 (SPA) 为什么能像原生 App 一样流畅跳转？这全靠路由系统。本文将深度解析 Vue Router 4 的安装创建、工作模式、嵌套路由设计，以及技巧与注意事项，助你构建复杂的页面结构。"
---

# Vue 3 路由系统全解析：从基础跳转到高级传参

在传统的网页中，点击链接会刷新页面。但在 Vue 这种 **单页应用 (SPA)** 中，页面并不会刷新，而是通过 **Vue Router** 动态地切换组件。

本文将带你通俗易懂地掌握 Vue Router 4 的核心逻辑。

---

## 一、 安装与创建：路由的第一步

在使用路由之前，我们需要先安装并完成基础配置。

### 1. 安装
在项目根目录下运行：
```bash
npm install vue-router@4
```

### 2. 创建路由实例 (router/index.js)
通常我们会新建一个 `src/router/index.js` 文件：
```javascript
import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/about', name: 'About', component: () => import('../views/About.vue') } // 路由懒加载
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

### 3. 在 main.js 中注册
```javascript
import { createApp } from 'vue'
import App from './App.vue'
import router from './router' // 引入路由配置

const app = createApp(App)
app.use(router) // 使用插件
app.mount('#app')
```

---

## 二、 路由的两种工作模式

当你创建路由器时，必须选择一种历史记录模式。

### 1. Hash 模式 (`createWebHashHistory`)
- **URL 特征**：带有 `#` 号，如 `http://abc.com/#/home`。
- **特点**：`#` 后面的内容不会发给服务器。兼容性极好，不需要服务器做额外配置。

### 2. History 模式 (`createWebHistory`) —— 【推荐】
- **URL 特征**：正常的路径，如 `http://abc.com/home`。
- **特点**：看起来更美观、更专业。
- **注意**：上线后需要后端（如 Nginx）做配置，防止用户刷新页面时出现 404。

---

## 三、 基础跳转与展示

在 `App.vue` 中，我们需要两个核心组件：
- **`<router-link to="/home">`**：相当于 `<a>` 标签，但不会刷新页面。
- **`<router-view>`**：占位符，告诉 Vue 匹配到的组件应该显示在哪里。

---

## 四、 嵌套路由 (Children)

在复杂的应用中，页面通常是多层嵌套的。比如“个人中心”页面下还有“我的订单”和“安全设置”。

```javascript
{
  path: '/user',
  component: User,
  children: [
    {
      path: 'orders', // 注意：嵌套路由路径前面不要加 /
      component: Orders
    },
    {
      path: 'settings',
      component: Settings
    }
  ]
}
```
**关键点**：在 `User.vue` 组件内部，必须再写一个 `<router-view>`，子路由的组件才会显示在里面。

---

## 五、 路由传参：Params 与 Query 的实战详解

这是开发中最常用的功能。我们要搞清楚：**如何发？如何收？**

### 1. Params (路径参数) —— 嵌入在路径中
就像身份证号一样，它是路径不可分割的一部分。

- **第一步：配置路由占位**
  ```javascript
  { path: '/user/:id', name: 'User', component: User }
  ```
- **第二步：发送参数**
  - **模板跳转**：`<router-link :to="{ name: 'User', params: { id: 123 } }">用户123</router-link>`
  - **JS 跳转**：`router.push({ name: 'User', params: { id: 123 } })`
- **第三步：接收参数 (User.vue)**
  ```vue
  <script setup>
  import { useRoute } from 'vue-router'
  const route = useRoute()
  console.log(route.params.id) // 输出 123
  </script>
  ```

### 2. Query (查询参数) —— 拼接在问号后
就像百度搜索一样，参数跟在 `?` 后面，如 `/user?id=123`。

- **第一步：配置路由 (无需占位)**
  ```javascript
  { path: '/user', name: 'User', component: User }
  ```
- **第二步：发送参数**
  - **模板跳转**：`<router-link :to="{ path: '/user', query: { id: 123 } }">查询用户123</router-link>`
  - **JS 跳转**：`router.push({ path: '/user', query: { id: 123 } })`
- **第三步：接收参数 (User.vue)**
  ```vue
  <script setup>
  import { useRoute } from 'vue-router'
  const route = useRoute()
  console.log(route.query.id) // 输出 123
  </script>
  ```

### 3. Params vs Query 总结对比

| 特性 | Params | Query |
| :--- | :--- | :--- |
| **URL 表现** | `/user/123` (更简洁) | `/user?id=123` (像搜索) |
| **路由配置** | 必须在 path 中写 `:id` 占位 | 不需要额外配置 |
| **刷新数据** | 参数保留 | 参数保留 |
| **适用场景** | 详情页、个人主页 | 搜索结果、筛选过滤 |

---

## 六、 编程式导航

除了 `<router-link>`，我们经常需要在 JS 代码中进行跳转（如：登录成功后跳转到首页）。

在 Vue 3 的 `setup` 中，我们需要使用 `useRouter` 钩子：

```vue
<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const login = () => {
  // 模拟登录逻辑
  router.push('/home') // 普通跳转
  // router.push({ name: 'User', params: { id: 123 } }) // 带参跳转
}
</script>
```

---

## 七、 使用技巧与注意事项

### 1. 命名路由 (Named Routes) —— 【技巧】
给路由起个名字，跳转时就不需要写长长的路径了：
```javascript
// 配置
{ path: '/very/long/path/user/profile', name: 'Profile', component: Profile }

// 跳转
router.push({ name: 'Profile' }) 
```

### 2. 路由懒加载 —— 【优化】
不要在开头就把所有组件都 `import`。使用 `() => import(...)` 方式引入，可以让项目首屏加载更快。

### 3. 路由高亮效果 —— 【技巧】
Vue Router 会自动给激活的链接添加 `.router-link-active` 类名。你只需要在 CSS 中给这个类写样式，就能实现导航菜单的高亮。

### 4. 404 页面的处理 —— 【注意事项】
在路由配置的**最后**添加一个捕获所有路径的配置，用于显示 404 页面：
```javascript
{ path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound }
```

### 5. History 模式的 Nginx 配置 —— 【注意事项】
上线后，必须在 Nginx 配置中加上这句，否则刷新页面会 404：
```nginx
location / {
  try_files $uri $uri/ /index.html;
}
```

---

## 八、 总结

Vue Router 是 SPA 应用的骨架。掌握了**安装创建**、**工作模式**、**嵌套路由**和**传参技巧**，你就能够构建出逻辑清晰、结构复杂的现代化 Web 应用。

- 想让项目飞快？用 **懒加载**。
- 想跳转不刷新？用 **router-link** 或 **push**。
- 想更专业？用 **命名路由** 和 **History 模式**。

> （注：本文由 GW 整理。路由在手，天下我有！）
