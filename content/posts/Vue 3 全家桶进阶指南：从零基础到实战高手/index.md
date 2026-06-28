---
title: "Vue 3 全家桶进阶指南：从零基础到实战高手"
date: 2026-05-30T12:30:00+08:00
draft: false
images: ["/images/post/vue3-complete-guide.jpg"]
tags: ["Vue3", "JavaScript", "前端框架", "Composition API"]
categories: ["前端开发", "Vue"]
series: ["前端开发系列"]
author: "GW"
summary: "Vue 3 已经成为前端开发的主流选择。本文将带你从零开始，系统掌握 Vue 3 的核心概念、Composition API、组件通信、生命周期，以及 Vue Router 和 Pinia 等全家桶工具，助你快速上手现代前端开发。"
---

# Vue 3 全家桶进阶指南：从零基础到实战高手

Vue 3 带来了更快的性能、更小的体积，以及最激动人心的 **Composition API (组合式 API)**。如果你以前觉得 Vue 的代码太分散，那么 Vue 3 将让你体验到像写纯 JS 一样组织代码的快感。

---

## 一、 快速起步：安装与环境

在现代开发中，我们不再推荐使用 CDN，而是使用超快的构建工具 **Vite**。

### 1. 创建项目
打开终端，运行以下命令：
```bash
npm create vite@latest my-vue-app -- --template vue
cd my-vue-app
npm install
npm run dev
```
几秒钟后，你的 Vue 3 项目就跑起来了！

---

## 二、 核心灵魂：Composition API

Vue 3 与 Vue 2 最大的区别就是舍弃了 `data/methods` 的碎片化写法，改用统一的 `setup`。

### 1. `setup` 语法糖
在 `<script setup>` 中定义的变量和函数，在模板中可以直接使用。

### 2. 响应式核心：`ref` 与 `reactive`
- **`ref`**：用于定义**基本类型**（数字、字符串、布尔）或简单对象。访问时需加 `.value`。
- **`reactive`**：用于定义**深层对象**或数组。直接访问，无需 `.value`。

```vue
<script setup>
import { ref, reactive } from 'vue'

const count = ref(0) // 基本类型
const user = reactive({ name: 'GW', age: 25 }) // 对象类型

const increment = () => {
    count.value++ // ref 需要 .value
    user.age++    // reactive 直接改
}
</script>

<template>
    <button @click="increment">{{ count }} - {{ user.name }} ({{ user.age }})</button>
</template>
```

---

## 三、 常用指令 (Directives)

指令是 Vue 操纵 DOM 的魔法棒：
- **`v-bind` (简写 `:`)**：绑定属性（如 `:src`, `:class`）。
- **`v-on` (简写 `@`)**：绑定事件（如 `@click`, `@submit`）。
- **`v-if / v-else`**：条件渲染（真正销毁/创建 DOM）。
- **`v-show`**：显示隐藏（仅切换 `display: none`）。
- **`v-for`**：循环遍历。
- **`v-model`**：**双向绑定**，常用于表单。

---

## 四、 组件通信：数据如何传递？

### 1. 父传子：`defineProps`
父组件通过属性传值，子组件通过 `defineProps` 接收。

### 2. 子传父：`defineEmits`
子组件通过 `emit` 触发事件，父组件监听。

```vue
<!-- 子组件 Child.vue -->
<script setup>
const props = defineProps(['msg'])
const emit = defineEmits(['change'])

const sendToParent = () => emit('change', '来自子的问候')
</script>
```

---

## 五、 计算属性与侦听器

- **`computed`**：具有**缓存性**。只有依赖项变了，它才会重新计算。适合做数据过滤、格式化。
- **`watch`**：用于执行**副作用**。比如当 ID 变了，去发请求拿数据。

```javascript
import { computed, watch } from 'vue'

const fullName = computed(() => firstName.value + lastName.value)

watch(count, (newVal, oldVal) => {
    console.log(`计数器从 ${oldVal} 变到了 ${newVal}`)
})
```

---

## 六、 生命周期钩子

Vue 3 的钩子函数名字前面都加了 `on`，且需要从 `vue` 中引入：
- `onMounted`：组件挂载完成（请求数据的黄金位置）。
- `onUpdated`：数据更新后。
- `onUnmounted`：组件销毁前（清理定时器、解绑事件）。

---

## 七、 进阶全家桶：Router 与 Pinia

### 1. Vue Router (路由)
负责页面跳转，不刷新浏览器实现单页应用 (SPA)。
- `<router-link to="/">`：跳转链接。
- `<router-view>`：页面展示区域。

### 2. Pinia (状态管理)
Vue 3 的官方状态管理库，取代了 Vuex。它极其轻量，且对 TypeScript 支持极好。

---

## 八、 高级技巧：自定义 Hooks (组合式函数)

这是 Vue 3 真正的杀手锏。你可以把逻辑封装成以 `use` 开头的函数，实现真正的代码复用。

```javascript
// useMouse.js
import { ref, onMounted, onUnmounted } from 'vue'

export function useMouse() {
    const x = ref(0)
    const y = ref(0)
    const update = e => { x.value = e.pageX; y.value = e.pageY }
    
    onMounted(() => window.addEventListener('mousemove', update))
    onUnmounted(() => window.removeEventListener('mousemove', update))
    
    return { x, y }
}
```

---

## 九、 总结

Vue 3 是一次巨大的飞跃。掌握了 **Composition API**，你就掌握了 Vue 3 的精髓。它不再仅仅是一个框架，而是一个能让你随心所欲组织业务逻辑的利器。

从 `ref` 到 `setup`，再到 `Pinia` 状态管理，希望这篇笔记能陪你走完从新手到高手的进阶之路！

> （注：本文由 GW 整理。Vue 3 的世界很大，一起去探索吧！）
