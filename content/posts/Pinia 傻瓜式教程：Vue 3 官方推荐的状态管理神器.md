---
title: "Pinia 傻瓜式教程：Vue 3 官方推荐的状态管理神器"
date: 2026-05-30T22:00:00+08:00
draft: false
images: ["/images/post/pinia-guide.jpg"]
tags: ["Vue3", "Pinia", "状态管理", "前端开发"]
categories: ["Vue"]
series: ["前端开发系列"]
author: "GW"
summary: "当组件之间传参让你头大时，你需要一个“共享大仓库”。Pinia 是 Vue 3 的官方状态管理库，它不仅极其轻量，而且用起来就像写普通的 Vue 组件一样简单。本文将带你从零开始，彻底玩转 Pinia。"
---

# Pinia 傻瓜式教程：Vue 3 官方推荐的状态管理神器

在开发大型项目时，我们经常会遇到：**多个组件需要共享同一份数据**（如：用户信息、购物车列表、全局主题）。

如果用父子传参，代码会变成一团乱麻。这时候，我们需要一个“超级大仓库”来存放这些公共数据，这个仓库就是 **Pinia**。

---

## 一、 为什么选 Pinia 而不是 Vuex？

如果你用过 Vue 2 时代的 Vuex，你会发现 Pinia 简直是天才的设计：
1. **去掉了 Mutation**：以前改数据非要写 `commit`，现在直接像改普通变量一样简单。
2. **极简 API**：只有 `State`、`Getters`、`Actions`，学习成本极低。
3. **完美的 TS 支持**：再也不用为了类型检查写一堆复杂的配置。
4. **极致轻量**：体积只有 1kb 左右。

---

## 二、 安装与初始化

### 1. 安装
```bash
npm install pinia
```

### 2. 在 main.js 中注册
```javascript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
const pinia = createPinia() // 创建实例

app.use(pinia) // 挂载到应用
app.mount('#app')
```

---

## 三、 创建你的第一个仓库 (Store)

通常我们在 `src/stores` 目录下创建仓库文件。例如：`counter.js`。

### 核心三要素：
- **State**：存放数据（相当于 `data`）。
- **Getters**：存放计算属性（相当于 `computed`）。
- **Actions**：存放修改数据的方法（相当于 `methods`），支持异步。

```javascript
import { defineStore } from 'pinia'

// 这里的 'counter' 是仓库的唯一 ID
export const useCounterStore = defineStore('counter', {
  // 1. 定义数据
  state: () => ({
    count: 0,
    name: 'GW'
  }),
  // 2. 定义计算属性
  getters: {
    doubleCount: (state) => state.count * 2,
  },
  // 3. 定义修改方法
  actions: {
    increment() {
      this.count++ // 直接通过 this 修改，爽不爽？
    },
    randomizeCounter() {
      this.count = Math.round(100 * Math.random())
    }
  }
})
```

---

## 四、 在组件中使用仓库

在组件里使用 Pinia 就像引用一个普通的 JS 函数一样。

```vue
<script setup>
import { useCounterStore } from '@/stores/counter'

const counter = useCounterStore() // 实例化仓库
</script>

<template>
  <div>
    <p>当前计数：{{ counter.count }}</p>
    <p>两倍计数：{{ counter.doubleCount }}</p>
    <button @click="counter.increment">加一</button>
  </div>
</template>
```

---

## 五、 进阶技巧：修改数据的几种方式

### 方式 1：直接修改（最简单）
```javascript
counter.count++
```

### 方式 2：批量修改 (`$patch`)
如果你想一次性改好几个数据，推荐用这个，性能更好：
```javascript
counter.$patch({
  count: 99,
  name: 'GW_NewName'
})
```

### 方式 3：Action 修改（最专业）
虽然直接改很方便，但为了代码清晰，建议把逻辑写在 `actions` 里，尤其是涉及接口请求时。

---

## 六、 避坑指南：解构丢失响应式

这是新手最容易犯的错！
如果你像下面这样写，数据变了页面是**不会更新**的：
```javascript
// ❌ 错误做法：直接解构
const { count } = useCounterStore() 
```

**正确做法**：使用 `storeToRefs`。
```javascript
import { storeToRefs } from 'pinia'
const store = useCounterStore()
// ✅ 正确做法：包裹后再解构
const { count } = storeToRefs(store)
```

---

## 七、 总结

Pinia 是 Vue 3 开发的“标配”。它解决了组件间数据共享的痛点，让你的项目结构更加清晰。

- **State**：存数据。
- **Getters**：加工数据。
- **Actions**：改数据（包括发请求）。
- **记住**：解构时要用 `storeToRefs`。

> （注：本文由 GW 整理。掌握了 Pinia，你离中高级前端又近了一步！）
