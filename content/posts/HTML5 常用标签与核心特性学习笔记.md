---
title: "HTML5 常用标签与核心特性学习笔记"
date: 2026-05-30T11:30:00+08:00
draft: false
images: ["/images/post/html5-tags-guide.jpg"]
tags: ["HTML5", "前端开发", "学习笔记", "网页开发"]
categories: ["前端开发", "HTML"]
series: ["前端开发系列"]
author: "GW"
summary: "本文详细整理了 HTML5 常用标签及其使用说明，重点介绍了表单基础（含文件上传）、新增语义化标签、多媒体标签及表单增强特性，适合前端初学者及开发者查阅复习。"
---

# HTML5 常用标签与核心特性学习笔记

HTML (HyperText Markup Language) 是构建万维网的核心语言。HTML5 不仅仅是 HTML 的第五次重大修改，更是一套包含了 CSS3 和 JavaScript API 的完整技术堆栈。

本文将系统梳理 HTML 的常用基础标签，并重点解析 HTML5 引入的新特性。

---

## 一、 HTML 基础结构

每个标准的 HTML 文档都包含以下基础骨架：

```html
<!DOCTYPE html> <!-- 声明文档类型为 HTML5 -->
<html lang="zh-CN"> <!-- 根标签，指定语言 -->
<head>
    <meta charset="UTF-8"> <!-- 字符编码 -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0"> <!-- 适配移动端 -->
    <title>页面标题</title>
</head>
<body>
    <!-- 网页内容在此处编写 -->
</body>
</html>
```

---

## 二、 常用基础标签

### 1. 文本标题与段落
- `<h1>` ~ `<h6>`：定义六级标题，`<h1>` 重要性最高。
- `<p>`：定义段落。
- `<br>`：强制换行（单标签）。
- `<hr>`：水平分隔线。

### 2. 文本格式化
- `<strong>` 或 `<b>`：加粗（`<strong>` 具语义重要性）。
- `<em>` 或 `<i>`：倾斜（`<em>` 具语义强调）。
- `<ins>` 或 `<u>`：下划线。
- `<del>` 或 `<s>`：删除线。

### 3. 链接与图片
- `<a href="URL" target="_blank">链接文本</a>`：超链接。`target="_blank"` 表示在新窗口打开。
- `<img src="图片路径" alt="替换文本" title="悬停文字">`：图像。`alt` 是图片加载失败时的文本，对 SEO 友好。

### 4. 列表标签
- **无序列表**：`<ul>` 配合 `<li>`。
- **有序列表**：`<ol>` 配合 `<li>`。

---

## 三、 表单基础 (Form)

表单用于收集用户输入。一个完整的表单通常包含 `<form>` 容器、表单控件及提交按钮。

### 1. 表单容器 `<form>`
- `action`：数据提交的服务器地址。
- `method`：提交方式（`get` 或 `post`）。
- `enctype`：**上传文件时必须设置**为 `multipart/form-data`。

### 2. 常用控件
- `<label>`：定义控件标注。通过 `for` 属性绑定输入框的 `id`，点击标注可聚焦输入框。
- `<input type="text">`：单行文本输入框。
- `<input type="password">`：密码输入框（掩码显示）。
- `<textarea>`：多行文本域。
- `<select>` 与 `<option>`：下拉列表。
- `<input type="radio">`：单选框（需设置相同的 `name`）。
- `<input type="checkbox">`：复选框。

### 3. 文件上传
要实现文件上传，必须配合 `type="file"` 的 input 标签。
```html
<form action="/upload" method="post" enctype="multipart/form-data">
    <label for="avatar">选择头像：</label>
    <input type="file" id="avatar" name="avatar" accept="image/*">
    <button type="submit">提交上传</button>
</form>
```
- `accept`：限制可选文件类型（如 `image/*` 表示只接受图片）。
- `multiple`：允许一次选择多个文件。

---

## 四、 HTML5 新增语义化标签（重点）

HTML5 引入了语义化标签，让搜索引擎和开发者能更清晰地理解网页结构。

| 标签 | 说明 |
| :--- | :--- |
| `<header>` | 定义页面或区域的头部。 |
| `<nav>` | 定义导航链接部分。 |
| `<main>` | 定义文档的主要内容（每个页面唯一）。 |
| `<article>` | 定义独立的文章内容（如博客文章）。 |
| `<section>` | 定义文档中的节或区域。 |
| `<aside>` | 定义侧边栏内容。 |
| `<footer>` | 定义页面或区域的底部。 |

---

## 五、 HTML5 多媒体标签

### 1. 视频标签 `<video>`
```html
<video src="movie.mp4" controls width="600" poster="cover.jpg">
    您的浏览器不支持 video 标签。
</video>
```

### 2. 音频标签 `<audio>`
```html
<audio src="music.mp3" controls>
    您的浏览器不支持 audio 标签。
</audio>
```

---

## 六、 HTML5 表单增强

### 1. 新增输入类型 (`type`)
- `type="email"`：验证邮箱格式。
- `type="url"`：验证网址。
- `type="number"`：数值输入。
- `type="range"`：滑块。
- `type="date" / "time"`：日期时间选择。
- `type="color"`：颜色选择器。

### 2. 新增属性
- `placeholder`：占位提示。
- `required`：必填。
- `autofocus`：自动聚焦。
- `autocomplete`：自动补全。

---

## 七、 总结

HTML5 的核心目标是**语义化**、**多媒体支持**和**更强大的交互能力**。掌握表单的基础使用（尤其是文件上传的配置）以及 HTML5 的新特性，是编写现代网页的基础。

希望这份笔记能帮助你快速回顾 HTML5 的核心知识！

> （注：本文档由 GW 整理，部分内容参考了 MDN Web Docs）
