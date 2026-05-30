---
title: "CSS Grid 布局完全指南：构建复杂的二维网格"
date: 2026-05-30T12:01:00+08:00
draft: false
images: ["/images/post/grid-layout-guide.jpg"]
tags: ["CSS", "Grid", "布局", "前端开发"]
categories: ["CSS"]
series: ["前端开发系列"]
author: "GW"
summary: "如果说 Flex 是排队（一维），那么 Grid 就是下棋（二维）。CSS Grid 是网页布局中最强大的系统，它能让你轻松搞定复杂的网格结构。本文将带你从零开始，掌握网格布局的核心奥秘。"
---

# CSS Grid 布局完全指南：构建复杂的二维网格

在网页布局的演进过程中，如果说 Flex 布局解决了“线”的问题（一维布局），那么 **CSS Grid** 则解决了“面”的问题（二维布局）。

它就像是在网页上铺设了一张透明的“坐标网格”，你可以精确地决定元素占据哪几行、哪几列。

---

## 一、 核心概念：网格的构成

要学好 Grid，首先要在大脑里建立这几个概念：

1. **Grid 容器 (Container)**：设置了 `display: grid;` 的父元素。
2. **Grid 项目 (Item)**：容器内部的直接子元素。
3. **网格线 (Grid Line)**：构成网格结构的线（水平和垂直）。
4. **网格轨道 (Grid Track)**：相邻两条网格线之间的空间（即“行”或“列”）。
5. **网格单元格 (Grid Cell)**：网格的最小单位（类似 Excel 的单元格）。
6. **网格区域 (Grid Area)**：由一个或多个单元格组成的矩形区域。

---

## 二、 容器属性（给父元素设置）

### 1. 开启网格
```css
.container {
    display: grid; /* 块级网格 */
    /* 或者 display: inline-grid; 行内网格 */
}
```

### 2. 定义行列（核心）
- **`grid-template-columns`**：定义每一列的宽度。
- **`grid-template-rows`**：定义每一行的高度。

**常用单位：**
- `px`, `%`：绝对或相对单位。
- **`fr`**：弹性系数单位（fraction）。`1fr` 代表占据剩余空间的一份。
- **`repeat(次数, 大小)`**：简化重复写法。例如 `repeat(3, 1fr)` 表示 3 列等宽。
- **`minmax(最小值, 最大值)`**：定义范围。

```css
.container {
    grid-template-columns: 200px 1fr 1fr; /* 第一列固定，后两列平分剩余空间 */
    grid-template-rows: repeat(3, 100px); /* 3行，每行100px高 */
}
```

### 3. 间距 (Gap)
- `row-gap`：行间距。
- `column-gap`：列间距。
- **`gap`**：缩写（行间距 列间距）。

### 4. 单元格内容对齐
- `justify-items`：水平对齐（`start`, `end`, `center`, `stretch`）。
- `align-items`：垂直对齐（`start`, `end`, `center`, `stretch`）。
- **`place-items`**：缩写（垂直对齐 水平对齐）。

---

## 三、 项目属性（给子元素设置）

你可以通过指定**网格线**的编号来决定项目占据的位置。

### 1. 指定位置与跨度
- `grid-column-start` / `grid-column-end`
- `grid-row-start` / `grid-row-end`

**简写形式：**
- **`grid-column: [开始线] / [结束线];`**
- **`grid-row: [开始线] / [结束线];`**

> **提示**：你可以使用 `span` 关键字表示“跨越几个单元格”。

```css
.item-1 {
    grid-column: 1 / 3;  /* 从第1根线开始，到第3根线结束（占据2列） */
    grid-row: 1 / span 2; /* 从第1根线开始，跨越2行 */
}
```

### 2. 网格区域定义 (`grid-area`)
这是一种更直观的布局方式，通过名字来布局。

**父元素设置：**
```css
.container {
    display: grid;
    grid-template-areas: 
        "header header header"
        "sidebar main main"
        "footer footer footer";
}
```

**子元素对应：**
```css
.header { grid-area: header; }
.main { grid-area: main; }
.sidebar { grid-area: sidebar; }
.footer { grid-area: footer; }
```

---

## 四、 Grid vs Flex：我该选哪个？

这是一道面试高频题，其实逻辑很简单：

- **选 Flex**：如果你只需要控制元素在**一个方向**（行或列）上的排列（如导航栏、工具栏）。
- **选 Grid**：如果你需要控制元素在**两个方向**（行和列）上的复杂结构（如整个页面的大框架、不规则的照片墙）。

---

## 五、 实战案例：响应式图片墙

不需要媒体查询，就能实现自动换行的网格：

```css
.photo-wall {
    display: grid;
    /* 自动填充，每列最小200px，最大平分 */
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
}
```

---

## 六、 总结图表

| 属性 | 作用对象 | 核心作用 |
| :--- | :--- | :--- |
| `display: grid` | 容器 | 开启网格布局 |
| `grid-template-columns` | 容器 | 划分列（比如 3 列还是 5 列） |
| `gap` | 容器 | 设置格子之间的“缝隙” |
| `grid-area` | 项目 | 给项目取个名字，方便直接扔进模板区域 |
| `grid-column / row` | 项目 | 决定项目占据哪几个格子 |

---

## 七、 结语

Grid 布局初看属性很多，但只要你掌握了 `grid-template-columns` 和 `grid-column / row` 的基本用法，就能解决 80% 的布局难题。它是网页布局的“终极方案”，学会它，意味着你掌握了现代网页布局的最高生产力。

> （注：本文由 GW 整理。如果 Grid 让你感到强大，请把它分享给更多人！）
