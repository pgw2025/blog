---
title: "AntV X6 在 Vue 3 中的应用：从入门到进阶指南"
date: 2026-05-31T08:30:00+08:00
draft: false
categories: ["前端开发", "Vue"]
series: ["前端开发系列"]
author: "GW"
tags: ["Vue3", "AntV X6", "数据可视化", "图引擎"]
summary: "本文介绍了如何在 Vue 3 项目中集成并使用 AntV X6 图编辑引擎。内容涵盖基础画布初始化、使用 @antv/x6-vue-shape 渲染自定义 Vue 组件节点、响应式数据绑定、连线规则校验以及性能优化实践。"
---



AntV X6 是一个强大的图编辑引擎，而 Vue 3 是当前主流的前端框架。将两者结合时，最核心的课题是**如何让 X6 的画布生命周期与 Vue 3 的组件生命周期同步**，以及**如何在节点中渲染 Vue 3 组件**。

本文将由浅入深，通过具体的代码示例，带你掌握在 Vue 3 (Composition API / `<script setup>`) 中使用 AntV X6 的核心技能。


### 一、 基础入门：在 Vue 3 中初始化画布

在 Vue 3 中，我们不能直接操作 DOM。我们需要通过 `ref` 获取画布容器，并在 `onMounted` 钩子中初始化 X6 画布，同时在 `onUnmounted` 中销毁画布以防内存泄漏。

#### 1.1 安装依赖
首先，安装 X6 核心库：
```bash
npm install @antv/x6 --save
```

#### 1.2 基础画布组件示例
创建一个名为 `BaseGraph.vue` 的组件：

```vue
<template>
  <div class="graph-wrapper">
    <!-- 画布容器，使用 ref 绑定 -->
    <div ref="containerRef" class="graph-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { Graph } from '@antv/x6';

const containerRef = ref(null);
let graph = null;

// 在组件挂载后初始化画布
onMounted(() => {
  if (!containerRef.value) return;

  // 1. 初始化 Graph 实例
  graph = new Graph({
    container: containerRef.value,
    width: 800,
    height: 500,
    grid: {
      size: 10,
      visible: true,
    },
    panning: true, // 开启拖拽平移
  });

  // 2. 添加测试节点
  const source = graph.addNode({
    x: 100,
    y: 150,
    width: 100,
    height: 40,
    label: '起点',
  });

  const target = graph.addNode({
    x: 400,
    y: 150,
    width: 100,
    height: 40,
    label: '终点',
  });

  // 3. 添加连接线
  graph.addEdge({
    source,
    target,
  });
});

// 组件卸载时销毁画布，避免内存泄漏
onUnmounted(() => {
  if (graph) {
    graph.dispose();
  }
});
</script>

<style scoped>
.graph-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}
.graph-container {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}
</style>
```

---

### 二、 进阶：在节点中渲染自定义 Vue 3 组件

在实际业务中，节点的样式往往非常复杂（比如包含输入框、下拉菜单、状态指示灯等）。使用 SVG 属性编写这类节点效率较低。X6 提供了 `@antv/x6-vue-shape` 工具包，允许你**直接将 Vue 3 组件渲染为画布中的节点**。

#### 2.1 安装 Vue 节点适配器
```bash
npm install @antv/x6-vue-shape --save
```

#### 2.2 第一步：定义你的 Vue 3 节点组件
创建一个普通的 Vue 组件 `CustomNode.vue`，作为节点外观：

```vue
<!-- CustomNode.vue -->
<template>
  <div class="custom-node" :class="{ active: isSelected }">
    <div class="header">
      <span class="status-dot"></span>
      {{ title }}
    </div>
    <div class="body">
      <p>数据量: {{ nodeData.count }}</p>
      <button @click="increment">点击自增</button>
    </div>
  </div>
</template>

<script setup>
import { computed, inject } from 'vue';

// X6 会将当前节点的实例通过 provide 注入到组件中
const getNode = inject('getNode');
const node = getNode();

// 获取节点上传递的数据
const nodeData = computed(() => node.getData() || { count: 0 });
const title = computed(() => node.label || '默认节点');

// 获取节点的选中状态
const isSelected = computed(() => node.store.data.selected || false);

// 触发数据更新
const increment = () => {
  const currentCount = nodeData.value.count;
  node.setData({
    count: currentCount + 1,
  });
};
</script>

<style scoped>
.custom-node {
  width: 100%;
  height: 100%;
  border: 1px solid #303133;
  border-radius: 8px;
  background-color: #ffffff;
  overflow: hidden;
  font-family: sans-serif;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.custom-node.active {
  border-color: #409eff;
  box-shadow: 0 0 8px rgba(64,158,255,0.5);
}
.header {
  background-color: #f2f6fc;
  padding: 6px 10px;
  font-size: 12px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #67c23a;
  margin-right: 6px;
}
.body {
  padding: 10px;
  font-size: 12px;
}
button {
  background: #409eff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  padding: 4px 8px;
}
</style>
```

#### 2.3 第二步：注册并使用该 Vue 节点
在主画布组件中，注册 `CustomNode.vue` 并将其添加到画布中：

```vue
<!-- VueNodeGraph.vue -->
<template>
  <div ref="containerRef" class="graph-container"></div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Graph } from '@antv/x6';
import { register } from '@antv/x6-vue-shape';
import CustomNode from './CustomNode.vue';

const containerRef = ref(null);

// 1. 注册自定义 Vue 节点类型
register({
  shape: 'my-vue-node',
  width: 180,
  height: 100,
  component: CustomNode, // 引入的 Vue 3 组件
});

onMounted(() => {
  const graph = new Graph({
    container: containerRef.value,
    width: 800,
    height: 500,
    grid: true,
  });

  // 2. 在画布中使用注册好的 'my-vue-node'
  graph.addNode({
    shape: 'my-vue-node',
    x: 150,
    y: 100,
    label: 'Vue 3 渲染节点',
    data: {
      count: 10, // 传递初始数据
    },
  });
});
</script>
```

---

### 三、 高级应用：响应式数据联动与交互规则

在企业级应用中，图表通常不仅是静态展示，还需要实现：**Vue 状态与画布节点双向绑定**、**连接桩管理**、以及**拖拽连接时的验证**。

#### 3.1 响应式数据绑定 (Vue -> X6 节点)
在实际开发中，你可能会通过外部表单修改某个节点的名称，并希望画布节点实时更新。

```vue
<!-- ReactiveGraph.vue -->
<template>
  <div class="demo">
    <div class="toolbar">
      <input v-model="nodeName" placeholder="输入节点名称" />
      <button @click="updateNodeName">更新节点名称</button>
    </div>
    <div ref="containerRef" class="graph-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Graph } from '@antv/x6';

const containerRef = ref(null);
const nodeName = ref('初始节点名称');
let targetNode = null;

const updateNodeName = () => {
  if (targetNode) {
    // 动态修改属性，X6 会自动重绘该节点
    targetNode.attr('label/text', nodeName.value);
  }
};

onMounted(() => {
  const graph = new Graph({
    container: containerRef.value,
    width: 600,
    height: 300,
    grid: true,
  });

  targetNode = graph.addNode({
    x: 100,
    y: 80,
    width: 150,
    height: 45,
    attrs: {
      body: { fill: '#f0f9eb', stroke: '#67c23a', strokeWidth: 1 },
      label: { text: nodeName.value, fill: '#333' }
    }
  });
});
</script>
```

#### 3.2 节点连线规则约束
在画布中，不能允许用户随意乱连线（比如不能将“输出节点”连接到“输出节点”，或者防止形成闭环）。我们可以在初始化画布时通过 `connecting` 属性配置校验规则。

```javascript
const graph = new Graph({
  container: containerRef.value,
  connecting: {
    // 自动吸附到临近的连接桩
    snap: { radius: 15 },
    // 是否允许连接到空白画布上
    allowBlank: false,
    // 是否允许连接到自身
    allowLoop: false,
    // 核心：自定义连线验证
    validateConnection({ sourceView, targetView, sourceMagnet, targetMagnet }) {
      // 1. 必须有连接桩才能连
      if (!sourceMagnet || !targetMagnet) {
        return false;
      }
      
      // 2. 限制连线方向：只能从 'out' 端口连入 'in' 端口
      const sourcePortGroup = sourceMagnet.getAttribute('port-group');
      const targetPortGroup = targetMagnet.getAttribute('port-group');
      
      if (sourcePortGroup !== 'out' || targetPortGroup !== 'in') {
        return false; // 规则不匹配，拒绝连接
      }

      // 3. 避免重复连接：如果两个连接桩之间已经存在连线，拒绝新建
      const edges = this.getEdges();
      const isExist = edges.some((edge) => {
        const s = edge.getSource();
        const t = edge.getTarget();
        return s.cell === sourceView.cell.id && t.cell === targetView.cell.id;
      });

      return !isExist;
    },
  },
});
```

---

### 四、 避坑与性能优化指南

1. **避免深层代理 X6 实例**：
   在 Vue 3 中，使用 `ref` 或 `reactive` 包装 X6 的 `Graph`、`Node`、`Edge` 实例，会导致 Vue 对其内部复杂的对象属性进行深度 Proxy 监听，从而导致**严重的渲染性能下降**。
   * **正确做法**：将 `graph` 对象声明为普通的全局局部变量（用 `let`），或者使用 `shallowRef`。
     ```javascript
     // 推荐：仅浅层响应式，或纯 JS 变量
     const graphRef = shallowRef(null); 
     ```

2. **注意局部数据的双向流动**：
   在自定义的 Vue 节点（如 `CustomNode.vue`）中修改数据时，应始终使用 `node.setData()` 将修改提交给 X6 管理，而不要直接操作 Vue 的内部私有 ref，以保证通过 `graph.toJSON()` 导出的数据是完整的。