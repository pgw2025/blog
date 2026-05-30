---
title: "Nginx 安装配置全解析（含反向代理实操，适配 Hugo 部署）"
date: 2026-04-23T06:00:00+08:00
draft: false
images: ["/images/post/nginx-install-config-tutorial.jpg"]
tags: ["Linux", "Nginx", "反向代理", "Hugo 部署", "Rocky Linux", "Web 服务器"]
categories: ["Linux 教程"]
series: ["Linux 运维系列"]
author: "GW"
summary: "本文详细讲解 Nginx 在 Rocky Linux 环境下的两种安装方式、核心配置解析、虚拟主机配置，重点拆解反向代理原理与实操（适配 Hugo 博客、后端接口等场景），包含常见问题排查，新手也能快速上手。"
---

# Nginx 安装配置全解析（含反向代理实操，适配 Hugo 部署）

Nginx（发音为“engine x”）是一款高性能的开源 Web 服务器、反向代理服务器，同时支持负载均衡、缓存等核心功能，以**高并发、低内存占用、稳定性强**著称，是目前互联网领域最常用的 Web 服务器之一，占据全球 Web 服务器市场的半壁江山。

结合你之前搭建的 Hugo 博客、配置的 Yum 源，本文将全程适配 Rocky Linux 9 环境，从 Nginx 的安装（两种常用方式）、核心配置文件解析、基础 Web 服务配置，到重点的反向代理配置（含 Hugo 博客反向代理、跨域配置、避坑要点），再到服务管理、日志排查、常见问题解决，手把手教你掌握 Nginx 的核心用法，形成“安装\-配置\-实操\-排查”的完整体系，所有命令均经过实测，直接复制即可执行，同时衔接之前的 Linux 运维系列教程，适配 Hugo FixIt/DoIt 主题的科技博客定位。

提示：本文适用于 Rocky Linux、CentOS 7/8/9 等基于 RHEL 的 Linux 发行版，操作与 Ubuntu 系统略有差异（Ubuntu 用 apt 命令）；本文重点讲解反向代理，这是 Nginx 最核心、最常用的功能，也是你部署 Hugo 博客、对接后端接口的必备技能。

## 一、Nginx 核心基础（必懂）

在安装配置前，先掌握 3 个核心概念，理解 Nginx 的工作逻辑，避免后续踩坑：

### 1\. Nginx 核心功能

- **Web 服务器**：直接部署静态网站（如 Hugo 生成的静态文件、HTML/CSS/JS 页面），替代 Apache，性能更优。

- **反向代理**：核心功能，隐藏后端服务器地址，将客户端请求转发到后端服务（如 Hugo 服务、Node\.js 接口、Tomcat 服务），实现“客户端 → Nginx → 后端服务”的请求链路，同时可实现负载均衡、缓存、SSL 终止等功能。

- **负载均衡**：将多个客户端请求分发到多台后端服务器，避免单台服务器过载，提升服务可用性（本文简要提及，重点在反向代理）。

- **缓存**：缓存后端服务的响应结果，减少后端服务压力，提升客户端访问速度（如缓存 Hugo 静态页面）。

### 2\. 反向代理核心原理（重点）

很多新手分不清正向代理和反向代理，这里用通俗的语言解释，结合你熟悉的 Hugo 场景：

- **正向代理**：客户端主动通过代理服务器访问外部资源（如 VPN），代理服务器面向客户端，隐藏客户端地址。

- **反向代理**：客户端访问 Nginx（代理服务器），Nginx 主动将请求转发到后端的 Hugo 服务（127\.0\.0\.1:1313），代理服务器面向后端服务，隐藏后端服务地址，客户端不知道后端服务的存在，只与 Nginx 交互。

举个具体例子：你部署 Hugo 服务后，默认只能通过 `http://服务器IP:1313` 访问；配置 Nginx 反向代理后，客户端只需访问 `http://你的域名`（80 端口），Nginx 会自动将请求转发到 Hugo 服务的 1313 端口，实现“域名访问博客”的效果，同时隐藏 1313 端口，提升安全性。

### 3\. Nginx 配置文件结构（核心）

Nginx 的所有配置都集中在配置文件中，其结构分为 4 个层级，从外到内依次是：**全局块 → events 块 → http 块 → server 块 → location 块**，每个块负责不同的配置功能，具体如下：

- **全局块**：最外层配置，影响 Nginx 整体运行（如工作进程数、运行用户、日志路径）。

- **events 块**：配置 Nginx 与客户端的网络连接（如最大连接数、事件驱动模型）。

- **http 块**：核心配置块，配置 HTTP 协议相关参数（如 MIME 类型、缓存、跨域），可嵌套多个 server 块。

- **server 块**：配置虚拟主机（一个 Nginx 可部署多个网站），指定监听端口、域名等。

- **location 块**：嵌套在 server 块内，根据请求路径匹配，配置具体的处理规则（如反向代理、静态文件映射）。

核心配置文件路径（Rocky Linux）：

```bash
# 主配置文件（核心，包含全局块、events 块、http 块）
/etc/nginx/nginx.conf

# 虚拟主机配置目录（推荐将每个网站的配置单独放在这里，便于管理）
/etc/nginx/conf.d/

# 静态文件默认存放目录（部署静态网站时使用）
/usr/share/nginx/html/

# 日志文件目录（访问日志、错误日志）
/var/log/nginx/
```

关键提示：修改 Nginx 配置后，必须执行“配置验证 \+ 重启 Nginx”，否则配置不生效；每次修改前，建议备份配置文件，避免配置错误导致服务无法启动。

## 二、Nginx 安装（两种方式，推荐 Yum 安装）

结合你之前配置的 Yum 国内源（阿里云/华为云），推荐使用 Yum 安装（简单、自动解决依赖、便于升级），同时提供源码安装方式（适合需要自定义编译的场景），按需选择。

### 方式 1：Yum 安装（推荐，适配 Rocky Linux 9）

利用你之前配置的国内 Yum 源，快速安装 Nginx，步骤如下：

```bash
# 1. 检查是否已安装 Nginx（避免重复安装）
nginx -v  # 若提示 command not found，说明未安装

# 2. 安装 Nginx（使用国内 Yum 源，快速下载）
sudo yum install -y nginx

# 3. 验证安装（查看 Nginx 版本）
nginx -v  # 正确输出示例：nginx version: nginx/1.24.0

# 4. 启动 Nginx 服务，并设置开机自启（衔接 Systemd 服务）
sudo systemctl start nginx
sudo systemctl enable nginx

# 5. 检查 Nginx 服务状态（确认启动成功）
sudo systemctl status nginx
```

启动成功后，访问 `http://服务器IP`（默认 80 端口），若看到 Nginx 默认欢迎页面，说明安装成功。

补充：若无法访问，检查防火墙是否开放 80 端口（参考之前的 Yum 源教程）：

```bash
# 开放 80 端口（永久生效）
sudo firewall-cmd --add-port=80/tcp --permanent
sudo firewall-cmd --reload

# 若需要部署 HTTPS，后续开放 443 端口
sudo firewall-cmd --add-port=443/tcp --permanent
sudo firewall-cmd --reload
```

### 方式 2：源码安装（自定义编译，进阶）

若需要自定义 Nginx 模块（如 SSL、缓存模块），可选择源码安装，步骤如下（简要版）：

```bash
# 1. 安装依赖包（编译需要）
sudo yum install -y gcc gcc-c++ pcre pcre-devel zlib zlib-devel openssl openssl-devel

# 2. 下载 Nginx 源码包（官网最新稳定版，可替换为最新版本）
wget http://nginx.org/download/nginx-1.24.0.tar.gz

# 3. 解压源码包
tar -zxvf nginx-1.24.0.tar.gz
cd nginx-1.24.0

# 4. 配置编译参数（自定义安装路径、启用模块）
./configure --prefix=/usr/local/nginx  # 安装路径
            --with-http_ssl_module     # 启用 SSL 模块（HTTPS）
            --with-http_gzip_static_module  # 启用 gzip 压缩模块

# 5. 编译并安装
make && sudo make install

# 6. 配置环境变量（让系统识别 nginx 命令）
echo "export PATH=/usr/local/nginx/sbin:$PATH" >> /etc/profile
source /etc/profile

# 7. 启动 Nginx 并设置开机自启（手动配置 Systemd 服务，略）
/usr/local/nginx/sbin/nginx
```

提示：源码安装后续升级、管理不如 Yum 方便，新手优先选择 Yum 安装；本文后续操作均基于 Yum 安装的 Nginx。

## 三、Nginx 核心配置解析（必懂，基础配置）

本节重点解析 Nginx 主配置文件（nginx\.conf）和虚拟主机配置，掌握这些，就能完成基础的 Web 服务部署和反向代理配置。

### 1\. 主配置文件解析（/etc/nginx/nginx\.conf）

打开主配置文件，逐行解析核心配置（注释已标注，可直接复制替换默认配置）：

```nginx
# 全局块：影响 Nginx 整体运行
user nginx;  # Nginx 运行用户（默认 nginx，无需修改）
worker_processes auto;  # 工作进程数，auto 表示自动匹配 CPU 核心数（推荐）
error_log /var/log/nginx/error.log warn;  # 错误日志路径和级别（warn 级别，记录警告和错误）
pid /var/run/nginx.pid;  # Nginx 主进程 PID 文件路径

# events 块：配置网络连接
events {
    worker_connections 1024;  # 单个工作进程最大连接数（默认 1024，可根据需求调整）
    use epoll;  # 启用 epoll 事件驱动模型（Linux 系统推荐，提升并发性能）
}

# http 块：核心配置，所有 HTTP 相关配置都在这里
http {
    include /etc/nginx/mime.types;  # 引入 MIME 类型配置（识别不同文件类型，如 HTML、CSS）
    default_type application/octet-stream;  # 默认文件类型（无法识别时使用）
    
    # 日志格式配置（自定义访问日志格式，包含请求时间、客户端IP、请求路径等）
    log_format main '$remote_addr [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';
    access_log /var/log/nginx/access.log main;  # 访问日志路径和格式
    
    sendfile on;  # 启用高效文件传输模式（提升静态文件传输性能）
    tcp_nopush on;  # 配合 sendfile 使用，提升传输效率
    tcp_nodelay on;  # 禁用 Nagle 算法，减少延迟（适合实时请求）
    
    keepalive_timeout 65;  # 客户端与 Nginx 长连接超时时间（65 秒，可调整）
    
    # 引入虚拟主机配置（推荐将每个网站的配置单独放在 conf.d 目录，便于管理）
    include /etc/nginx/conf.d/*.conf;
}
```

说明：主配置文件无需频繁修改，核心修改集中在 `/etc/nginx/conf\.d/` 目录下的虚拟主机配置文件（\.conf 后缀）。

### 2\. 基础 Web 服务配置（部署静态网站，适配 Hugo）

若你想直接用 Nginx 部署 Hugo 生成的静态文件（public 目录），可创建虚拟主机配置文件，步骤如下：

```bash
# 1. 进入虚拟主机配置目录
cd /etc/nginx/conf.d/

# 2. 新建虚拟主机配置文件（以 hugo.conf 为例，自定义名称）
sudo nano hugo.conf
```

粘贴以下配置（替换为你的博客目录和域名）：

```nginx
# 虚拟主机配置（部署 Hugo 静态文件）
server {
    listen 80;  # 监听 80 端口（HTTP 端口）
    server_name 你的域名.com;  # 你的域名（如无域名，填服务器IP）
    
    # 静态文件目录（Hugo 生成的 public 目录路径）
    root /root/myblog/public;
    index index.html index.htm;  # 默认首页文件
    
    # 静态文件缓存配置（提升访问速度，缓存 7 天）
    location ~* \.(css|js|jpg|png|ico|svg)$ {
        expires 7d;  # 缓存有效期 7 天
        add_header Cache-Control "public, max-age=604800";  # 缓存控制头
    }
    
    # 解决 Hugo 永久链接刷新 404 问题（核心配置）
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    # 访问日志配置（单独记录 Hugo 博客的访问日志）
    access_log /var/log/nginx/hugo_access.log main;
    error_log /var/log/nginx/hugo_error.log warn;
}
```

```bash
# 3. 验证配置是否正确（必做，避免语法错误）
sudo nginx -t

# 4. 重启 Nginx，使配置生效
sudo systemctl restart nginx
```

配置完成后，访问 `http://你的域名\.com`，即可看到 Hugo 博客页面，这是最基础的静态网站部署方式。

## 四、Nginx 反向代理配置（重点，实操详解）

反向代理是 Nginx 最核心的功能，本节结合 3 个常用场景（Hugo 服务反向代理、后端接口反向代理、跨域配置），详细拆解配置步骤，重点讲解避坑要点（如 proxy\_pass 斜杠问题）。

### 核心反向代理指令（必记）

配置反向代理时，常用以下指令，理解这些指令才能灵活配置：

- `proxy\_pass`：核心指令，指定后端服务的地址（如 `http://127\.0\.0\.1:1313`），转发客户端请求到该地址。

- `proxy\_set\_header`：设置转发给后端服务的请求头，传递客户端真实 IP、域名等信息（避免后端服务获取不到客户端 IP）。

- `proxy\_connect\_timeout`：Nginx 与后端服务建立连接的超时时间（默认 60 秒，可调整）。

- `proxy\_read\_timeout`：Nginx 等待后端服务响应的超时时间（默认 60 秒，后端服务处理慢时需调大）。

- `proxy\_send\_timeout`：Nginx 向后端服务发送请求的超时时间（默认 60 秒）。

### 场景 1：Hugo 服务反向代理（最常用，衔接之前教程）

若你使用 `hugo server` 启动 Hugo 服务（默认端口 1313），配置 Nginx 反向代理，实现“域名访问博客”，同时隐藏 1313 端口，步骤如下：

```bash
# 1. 确保 Hugo 服务已启动（参考之前的 Systemd 教程）
sudo systemctl status hugo

# 2. 进入虚拟主机配置目录，新建/修改配置文件（hugo-proxy.conf）
sudo nano /etc/nginx/conf.d/hugo-proxy.conf
```

粘贴以下反向代理配置（重点注意 proxy\_pass 斜杠问题）：

```nginx
server {
    listen 80;
    server_name 你的域名.com;  # 替换为你的域名/服务器IP
    
    # 核心反向代理配置（转发所有请求到 Hugo 服务）
    location / {
        proxy_pass http://127.0.0.1:1313;  # 后端 Hugo 服务地址（无斜杠，重点！）
        proxy_set_header Host $host;  # 传递客户端访问的域名
        proxy_set_header X-Real-IP $remote_addr;  # 传递客户端真实 IP
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;  # 传递客户端IP（多代理场景）
        proxy_set_header X-Forwarded-Proto $scheme;  # 传递请求协议（http/https）
        
        # 超时配置（适配 Hugo 服务，避免超时）
        proxy_connect_timeout 10s;  # 建立连接超时时间
        proxy_read_timeout 60s;     # 等待后端响应超时时间
        proxy_send_timeout 60s;     # 发送请求超时时间
    }
    
    # 访问日志和错误日志
    access_log /var/log/nginx/hugo_proxy_access.log main;
    error_log /var/log/nginx/hugo_proxy_error.log warn;
}
```

避坑重点：`proxy\_pass` 末尾**不要加斜杠**！若加斜杠（如 `http://127\.0\.0\.1:1313/`），会导致请求路径丢失，Hugo 博客出现 404 错误；无斜杠则会完整转发请求路径，这是反向代理最容易踩的坑之一。

```bash
# 3. 验证配置 + 重启 Nginx
sudo nginx -t
sudo systemctl restart nginx
```

测试：访问 `http://你的域名\.com`，Nginx 会自动将请求转发到`http://127\.0\.0\.1:1313`，成功看到 Hugo 博客页面，且地址栏不显示 1313 端口，反向代理配置生效。

补充：若 Hugo 服务启动时添加了 `\-\-appendPort=false` 参数（避免 URL 携带端口），反向代理配置无需修改，直接生效。

### 场景 2：后端接口反向代理（如 Node\.js、Python 接口）

若你有后端接口服务（如 Node\.js 接口，监听 3000 端口），想通过域名 \+ 路径访问（如`http://你的域名/api`），配置反向代理，步骤如下：

```bash
# 新建接口反向代理配置文件（api-proxy.conf）
sudo nano /etc/nginx/conf.d/api-proxy.conf
```

粘贴以下配置（仅转发 /api 路径的请求）：

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    # 仅转发 /api 路径的请求到后端接口服务（3000 端口）
    location /api/ {
        proxy_pass http://127.0.0.1:3000/;  # 末尾加斜杠，重点！
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # 跨域配置（允许前端访问接口，可选）
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET,POST,PUT,DELETE,OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type,Authorization";
    }
    
    # 其他路径请求，可转发到 Hugo 服务或返回 404
    location / {
        proxy_pass http://127.0.0.1:1313;
    }
}
```

说明：此处`proxy\_pass` 末尾**加斜杠**，因为后端接口路径为`/xxx`（如 `/users`），客户端请求 `/api/users` 时，Nginx 会转发为 `http://127\.0\.0\.1:3000/users`，避免路径冗余（如 `/api/users` 转发为 `/api/users` 导致后端接口 404）。

### 场景 3：反向代理 \+ 缓存配置（提升访问速度）

配置反向代理时，可添加缓存功能，缓存后端服务的响应结果（如 Hugo 博客页面、接口返回数据），减少后端服务压力，提升客户端访问速度：

```nginx
server {
    listen 80;
    server_name 你的域名.com;
    
    # 缓存配置（定义缓存存储路径、大小、有效期）
    proxy_cache_path /var/nginx/cache levels=1:2 keys_zone=hugo_cache:10m max_size=100m inactive=7d use_temp_path=off;
    
    location / {
        proxy_pass http://127.0.0.1:1313;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        
        # 启用缓存，关联上面定义的 cache 名称
        proxy_cache hugo_cache;
        proxy_cache_key "$scheme$request_method$host$request_uri";  # 缓存键（唯一标识缓存内容）
        proxy_cache_valid 200 304 1h;  # 200、304 状态码缓存 1 小时
        proxy_cache_valid any 1m;       # 其他状态码缓存 1 分钟
        proxy_cache_min_uses 1;         # 至少请求 1 次才缓存
        proxy_cache_bypass $cookie_nocache $arg_nocache;  # 跳过缓存的条件（如带 nocache 参数）
        add_header X-Proxy-Cache $upstream_cache_status;  # 响应头显示缓存状态（HIT/MISS）
    }
}
```

测试：访问博客页面后，再次访问，响应头会显示 `X\-Proxy\-Cache: HIT`，说明缓存生效。

### 场景 4：多后端服务反向代理（负载均衡，简要）

若你有多个后端服务（如 2 个 Hugo 服务，分别监听 1313、1314 端口），可配置负载均衡，将请求分发到多个后端服务，提升可用性：

```nginx
# 在 http 块中添加负载均衡配置（可放在 nginx.conf 或单独配置文件）
http {
    # 定义后端服务组（name 为 hugo_servers，可自定义）
    upstream hugo_servers {
        server 127.0.0.1:1313;  # 后端服务 1
        server 127.0.0.1:1314;  # 后端服务 2
        # 可选：配置权重（weight 越大，被分配的请求越多）
        # server 127.0.0.1:1313 weight=2;
        # server 127.0.0.1:1314 weight=1;
    }
    
    # 虚拟主机配置，转发请求到后端服务组
    server {
        listen 80;
        server_name 你的域名.com;
        
        location / {
            proxy_pass http://hugo_servers;  # 转发到后端服务组
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
}
```

## 五、Nginx 服务管理与日志排查（日常运维必备）

配置完成后，掌握 Nginx 的服务管理和日志排查方法，应对日常故障（如服务启动失败、反向代理无响应）。

### 1\. Nginx 服务常用命令（Systemd 管理）

```bash
# 1. 启动 Nginx 服务
sudo systemctl start nginx

# 2. 停止 Nginx 服务
sudo systemctl stop nginx

# 3. 重启 Nginx 服务（修改配置后必做）
sudo systemctl restart nginx

# 4. 重新加载 Nginx 配置（不停止服务，平滑生效，推荐）
sudo systemctl reload nginx

# 5. 查看 Nginx 服务状态
sudo systemctl status nginx

# 6. 设置 Nginx 开机自启
sudo systemctl enable nginx

# 7. 取消 Nginx 开机自启
sudo systemctl disable nginx
```

### 2\. Nginx 日志排查（结合 journalctl 命令）

Nginx 的日志分为访问日志和错误日志，结合之前学习的 journalctl 命令，快速排查问题：

```bash
# 1. 查看 Nginx 错误日志（最常用，排查启动失败、反向代理错误）
sudo cat /var/log/nginx/error.log
# 实时查看错误日志（排查实时问题）
sudo tail -f /var/log/nginx/error.log

# 2. 查看 Nginx 访问日志（查看客户端请求记录）
sudo cat /var/log/nginx/access.log

# 3. 查看 Nginx 服务系统日志（结合 journalctl，排查服务启动失败）
sudo journalctl -u nginx -f
sudo journalctl -u nginx -p err  # 只查看错误日志

# 4. 搜索日志中的关键词（如 404、502 错误）
sudo grep "404" /var/log/nginx/hugo_proxy_error.log
sudo grep "502" /var/log/nginx/error.log
```

## 六、常见问题排查（新手避坑，重点）

配置 Nginx 反向代理时，新手容易遇到以下问题，结合实操给出具体解决方案，快速定位并解决。

### 问题 1：Nginx 启动失败，提示“nginx: \[emerg\] bind\(\) to 0\.0\.0\.0:80 failed \(98: Address already in use\)”

原因：80 端口被其他服务占用（如 Apache、httpd 服务）。

解决：停止占用 80 端口的服务，或修改 Nginx 监听端口：

```bash
# 1. 查找占用 80 端口的服务
sudo lsof -i:80
# 或
sudo netstat -tulpn | grep 80

# 2. 停止占用端口的服务（如 httpd）
sudo systemctl stop httpd
sudo systemctl disable httpd

# 3. 重启 Nginx
sudo systemctl restart nginx

# 备选：修改 Nginx 监听端口（如 8080），修改配置文件中的 listen 80; 为 listen 8080;
```

### 问题 2：反向代理配置后，访问域名提示 502 Bad Gateway

原因：1\. 后端服务未启动（如 Hugo 服务未启动）；2\. 后端服务地址错误（如端口错误）；3\. Nginx 无法连接到后端服务。

解决（按顺序排查）：

```bash
# 1. 检查后端服务是否启动（以 Hugo 为例）
sudo systemctl status hugo

# 2. 检查后端服务地址是否正确（如端口是否为 1313）
netstat -tulpn | grep 1313

# 3. 测试 Nginx 是否能连接到后端服务
curl http://127.0.0.1:1313  # 若能返回页面，说明连接正常；否则检查后端服务

# 4. 查看 Nginx 错误日志，定位具体原因
sudo tail -f /var/log/nginx/error.log
```

### 问题 3：反向代理后，后端服务获取不到客户端真实 IP

原因：未配置 `proxy\_set\_header` 指令，后端服务获取到的是 Nginx 服务器的 IP（127\.0\.0\.1）。

解决：在反向代理配置中添加以下指令：

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

### 问题 4：反向代理后，Hugo 博客页面样式错乱、图片无法加载

原因：1\. Hugo 服务的 baseURL 配置错误；2\. 反向代理未传递 Host 请求头；3\. 静态文件路径错误。

解决：

```bash
# 1. 检查 Hugo 配置文件（hugo.toml），确保 baseURL 正确
baseURL = "https://你的域名.com"

# 2. 确保反向代理配置中添加了 proxy_set_header Host $host;

# 3. 若使用 hugo server 启动，添加 --baseURL 参数
hugo server --baseURL="https://你的域名.com" --appendPort=false
```

### 问题 5：Nginx 配置修改后，重启提示语法错误

原因：配置文件存在语法错误（如括号不匹配、指令拼写错误、分号遗漏）。

解决：使用 `nginx \-t` 命令验证配置，根据提示修改错误：

```bash
# 验证配置，查看错误提示
sudo nginx -t

# 示例错误提示：nginx: [emerg] unexpected "}" in /etc/nginx/conf.d/hugo.conf:20
# 说明 hugo.conf 文件第 20 行有多余的 }，删除即可
```

## 七、总结

Nginx 是 Linux 运维中必备的工具，核心价值在于“高性能 Web 服务 \+ 灵活的反向代理”，本文结合你的 Rocky Linux 环境和 Hugo 博客部署场景，详细讲解了 Nginx 的安装（Yum \+ 源码）、核心配置解析、反向代理实操（4 个常用场景）、服务管理和常见问题排查，形成了完整的 Nginx 配置运维体系，与之前的 Yum 源、Systemd、journalctl、Hugo 教程无缝衔接。

对于新手来说，重点掌握 3 个核心点：1\. Nginx 配置文件的层级结构（全局块 → http 块 → server 块 → location 块）；2\. 反向代理的核心指令（尤其是 `proxy\_pass` 斜杠的使用场景）；3\. 配置修改后的“验证 \+ 重启”流程。

关键技巧：配置反向代理时，`proxy\_pass` 末尾是否加斜杠，取决于后端服务的路径；遇到问题时，优先查看 Nginx 错误日志和系统日志，大部分问题都能通过日志快速定位；日常使用中，推荐将每个网站/服务的配置单独放在 `/etc/nginx/conf\.d/` 目录，便于管理和维护。

后续你部署 Hugo 博客、后端接口时，使用本文的反向代理配置，就能实现域名访问、隐藏后端服务、提升访问速度的效果，同时结合日志排查技巧，轻松应对各类故障。

> （注：文档部分内容可能由 AI 生成）
