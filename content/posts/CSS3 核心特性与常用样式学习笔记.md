---
title: "CSS3 核心特性与常用样式学习笔记"
date: 2026-05-30T11:50:00+08:00
draft: false
images: ["/images/post/css3-features-guide.jpg"]
tags: ["CSS3", "前端开发", "学习笔记", "样式设计"]
categories: ["CSS"]
series: ["前端开发系列"]
author: "GW"
summary: "本文系统整理了 CSS3 的核心特性，包括盒子模型、浮动与定位、Flex 布局、Grid 布局，以及 CSS3 新增的过渡、动画、变形及变量等现代开发必备技巧。"
---

# CSS3 核心特性与常用样式学习笔记

CSS (Cascading Style Sheets) 负责网页的视觉呈现。CSS3 是 CSS 技术的最新演进，引入了许多强大的特性，极大地减少了对图片的依赖，并提升了页面的交互体验。

---

## 一、 CSS 基础概念

### 1. 引入方式
- **行内样式**：`<div style="color: red;"></div>`
- **内部样式**：写在 `<style>` 标签内。
- **外部样式**：通过 `<link rel="stylesheet" href="style.css">` 引入（推荐）。

### 2. 选择器
- **基础选择器**：标签选择器、类选择器 (`.class`)、ID 选择器 (`#id`)、通配符 (`*`)。
- **层级选择器**：后代选择器 (`space`)、子代选择器 (`>`)、并集选择器 (`,`)。
- **伪类选择器**：`:hover`、`:active`、`:focus`、`:nth-child(n)`。
- **伪元素选择器**：`::before`、`::after`（常用于装饰性元素）。

---

## 二、 盒子模型 (Box Model)

所有 HTML 元素都可以看作盒子。
- **内容 (Content)**：实际文本或图像。
- **内边距 (Padding)**：内容与边框之间的区域。
- **边框 (Border)**：包围在内边距和内容外的线。
- **外边距 (Margin)**：盒子与其他元素之间的距离。

**标准盒模型 vs 怪异盒模型：**
```css
/* 标准盒模型 (默认)：width = 内容宽度 */
box-sizing: content-box;

/* 怪异盒模型 (推荐)：width = 内容 + padding + border */
box-sizing: border-box;
```

---

## 三、 现代布局方案

### 1. Flex 布局 (弹性盒子)
Flex 是目前最主流的一维布局方案。
- **容器属性**：
    - `display: flex;`
    - `justify-content`: 水平对齐（`center`, `space-between`, `space-around`）。
    - `align-items`: 垂直对齐（`center`, `flex-start`）。
    - `flex-direction`: 主轴方向（`row`, `column`）。
- **项目属性**：
    - `flex: 1;`（自动撑开剩余空间）。

### 2. Grid 布局 (网格布局)
Grid 是强大的二维布局方案。
```css
.container {
    display: grid;
    grid-template-columns: repeat(3, 1fr); /* 三列等宽 */
    grid-gap: 10px; /* 网格间距 */
}
```

---

## 四、 CSS3 视觉特效

### 1. 圆角与阴影
- `border-radius: 50%;`：创建圆形。
- `box-shadow: 5px 5px 10px rgba(0,0,0,0.5);`：外阴影。
- `text-shadow`：文本阴影。

### 2. 渐变 (Gradients)
- **线性渐变**：`background: linear-gradient(to right, red, yellow);`
- **径向渐变**：`background: radial-gradient(circle, red, yellow);`

---

## 五、 过渡、变形与动画

### 1. 过渡 (Transition)
让属性变化平滑进行。
```css
.btn {
    transition: all 0.3s ease;
}
.btn:hover {
    background-color: blue;
}
```

### 2. 变形 (Transform)
- `translate(x, y)`：位移。
- `rotate(deg)`：旋转。
- `scale(n)`：缩放。
- `skew(deg)`：倾斜。

### 3. 动画 (Animation)
通过 `@keyframes` 定义关键帧。
```css
@keyframes move {
    0% { transform: translateX(0); }
    100% { transform: translateX(100px); }
}

.box {
    animation: move 2s infinite alternate;
}
```

---

## 六、 响应式设计

### 1. 媒体查询 (Media Queries)
根据设备屏幕尺寸应用不同的样式。
```css
@media screen and (max-width: 768px) {
    .sidebar {
        display: none; /* 在手机端隐藏侧边栏 */
    }
}
```

### 2. 常用单位
- `px`：像素（绝对单位）。
- `em`：相对于父元素字体大小。
- `rem`：相对于根元素 (`html`) 字体大小（推荐用于响应式）。
- `vw / vh`：视口宽度/高度的百分比。

---

## 七、 CSS 变量 (Custom Properties)

变量可以提高代码的复用性和可维护性。
```css
:root {
    --main-color: #3498db;
    --padding-base: 15px;
}

.header {
    background-color: var(--main-color);
    padding: var(--padding-base);
}
```

---

## 八、 总结

CSS3 不仅提升了网页的颜值，更通过 Flex、Grid 等布局方式彻底解决了传统浮动布局带来的痛苦。同时，原生 CSS 变量和动画特性也让我们在不依赖大型框架的情况下，依然能写出高质量、可维护的代码。

> （注：本文档由 GW 整理，学习 CSS 是一场对美感的持续追求！）
