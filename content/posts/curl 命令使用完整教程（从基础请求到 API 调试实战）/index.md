---
title: "curl 命令使用完整教程（从基础请求到 API 调试实战）"
date: 2026-06-13T10:00:00+08:00
draft: false
tags: ["Linux", "curl", "命令行", "网络调试"]
categories: ["运维技术", "Linux"]
series: ["Linux 学习系列"]
---

# curl 命令使用完整教程

在开发者和运维工程师的工具箱里，`curl` 绝对是出镜率最高的“瑞士军刀”之一。无论是简单的网页内容抓取、文件下载，还是复杂的 API 接口调试、模拟用户登录，`curl` 都能轻松胜任。

本文将通过通俗易懂的语言，带你从零开始掌握 `curl` 的核心用法，并分享一些实用的实战技巧。

---

## 一、什么是 curl？

`curl` 的全称是 **Client URL**，是一个利用 URL 语法在命令行下工作的文件传输工具。它支持几乎所有的网络协议，包括 HTTP、HTTPS、FTP、SFTP、SMTP 等。

**简单来说：** 它就是一个“没有界面的浏览器”，你可以在终端里指挥它去访问任何网址。

---

## 二、基础入门：最简单的请求

### 1. 抓取网页源码
直接在 `curl` 后面加上 URL，它就会把网页的 HTML 源码打印在终端里。
```bash
curl https://www.example.com
```

### 2. 保存访问内容
如果你想把网页保存成一个文件，可以使用 `-o`（小写）或 `-O`（大写）。
- **`-o` (小写)**：指定保存的文件名。
- **`-O` (大写)**：使用 URL 中的默认文件名。

```bash
# 保存为 test.html
curl -o test.html https://www.example.com

# 下载一张图片，保存名为 logo.png
curl -O https://example.com/images/logo.png
```

---

## 三、常用进阶参数（必会）

### 1. 查看响应头信息 (`-I`)
当你只想检查网站的状态码（如 200, 404）或查看服务器版本时，使用 `-I` 参数。
```bash
curl -I https://www.google.com
```

### 2. 显示详细过程 (`-v`)
如果你在排查网络问题，`-v` (verbose) 会显示整个连接过程，包括握手、请求头、响应头。
```bash
curl -v https://www.example.com
```

### 3. 自动重定向 (`-L`)
有些网址会自动跳转（比如从 http 跳到 https），默认情况下 `curl` 不会跟随跳转，使用 `-L` 强制它跟随。
```bash
curl -L http://google.com
```

### 4. 断点续传 (`-C -`)
下载大文件中途断了？加上 `-C -` 接着下。
```bash
curl -C - -O http://example.com/big-file.zip
```

---

## 四、API 调试：发送不同类型的请求

对于后端开发者来说，这是 `curl` 最强大的地方。

### 1. 发送 POST 请求 (`-d`)
默认情况下 `curl` 发送的是 GET 请求，使用 `-d` 即可发送 POST 数据。
```bash
curl -d "name=will&age=25" https://api.example.com/user
```

### 2. 发送 JSON 数据
发送 JSON 是目前最常见的场景。你需要配合 `-H` 参数指定内容类型。
```bash
curl -H "Content-Type: application/json" \
     -d '{"id": 1, "title": "Hello Curl"}' \
     https://api.example.com/posts
```

### 3. 指定请求方法 (`-X`)
除了 GET 和 POST，你可能还需要 PUT、DELETE 等方法。
```bash
# 修改数据
curl -X PUT -d "status=published" https://api.example.com/post/1

# 删除数据
curl -X DELETE https://api.example.com/post/1
```

---

## 五、身份认证与 Header 管理

### 1. 自定义 Header (`-H`)
有时候你需要传递特定的 API Key 或 User-Agent。
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     -H "User-Agent: MyCustomBrowser/1.0" \
     https://api.example.com/secure-data
```

### 2. 用户认证 (`-u`)
如果网站使用了 Basic Auth 认证。
```bash
curl -u username:password https://api.example.com/admin
```

---

## 六、实战技巧：一些“骚操作”

### 1. 快速查询你的公网 IP
不需要打开浏览器搜“我的 IP”，终端一行搞定：
```bash
curl ifconfig.me
# 或者
curl cip.cc
```

### 2. 模拟手机访问
通过修改 User-Agent 来查看移动版网页。
```bash
curl -A "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1" https://www.baidu.com
```

### 3. 使用代理服务器
```bash
curl -x http://127.0.0.1:7890 https://www.github.com
```

---

## 七、高手进阶：网络性能分析（时间统计）

如果你是运维人员或后端开发者，经常需要分析“为什么接口请求这么慢？”。`curl` 的 `-w`（write-out）参数可以让你精准地看到每一个环节耗时。

### 1. 核心耗时参数
你可以通过 `-w` 配合特定的变量来获取时间数据：
- `time_namelookup`：DNS 解析耗时。
- `time_connect`：TCP 三次握手耗时。
- `time_appconnect`：SSL/TLS 握手耗时（针对 HTTPS）。
- `time_starttransfer`：从请求开始到收到第一个字节的时间（TTFB）。
- `time_total`：整个请求的总耗时。

### 2. 实战：一键分析网站性能
我们可以将这些参数组合成一个模板，直接在终端输出漂亮的分析结果：

```bash
curl -o /dev/null -s -w '
HTTP 状态码:  %{http_code}\n
DNS 解析耗时: %{time_namelookup}s\n
TCP 连接耗时: %{time_connect}s\n
SSL 握手耗时: %{time_appconnect}s\n
首字节时间:   %{time_starttransfer}s\n
-------------------------\n
总耗时:       %{time_total}s\n' \
https://www.google.com
```

**参数说明：**
- `-o /dev/null`：不打印网页内容，只看统计结果。
- `-s`：静默模式，不显示下载进度条。
- `-w`：后面跟着你想自定义输出的格式字符串。

---

## 八、常用参数速查表

| 参数 | 说明 |
| :--- | :--- |
| `-o` / `-O` | 下载文件（自定义名/原始名） |
| `-I` | 仅查看响应头 (HEAD 请求) |
| `-L` | 跟随重定向 |
| `-v` | 显示详细调试信息 |
| `-u` | 设置用户认证 (Basic Auth) |
| `-H` | 自定义 HTTP Header |
| `-d` | 发送 POST 数据 |
| `-X` | 指定 HTTP 请求方法 (GET, POST, PUT, DELETE) |
| `-F` | 模拟表单上传文件 |
| `-w` | 按照自定义格式输出请求统计信息 |
| `-k` | 忽略 SSL 证书校验（慎用） |

---

## 结语

`curl` 的功能远不止于此，它还有几百个参数可以挖掘。但掌握了上面这些，你已经能应付 90% 的日常工作了。

**建议：** 把这篇文章收藏起来，下次写 API 调试脚本或者写爬虫时拿出来翻一翻，绝对能帮你省掉不少查文档的时间！
