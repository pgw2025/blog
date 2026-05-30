
---
title: "journalctl 命令使用完整教程（Linux 日志排查必备）"
date: 2026-04-22T12:30:00+08:00
draft: false
images: ["/images/post/journalctl-tutorial.jpg"]
tags: ["Linux", "journalctl", "日志排查", "Systemd", "运维"]
categories: ["Linux 教程"]
series: ["Linux 运维系列"]
author: "GW"
summary: "本文详细讲解 journalctl 命令的使用方法，涵盖日志查看、筛选、过滤、导出等核心操作，结合 Systemd 服务日志排查实操，新手也能快速掌握 Linux 日志排查技巧。"
---

# journalctl 命令使用完整教程（Linux 日志排查必备）


journalctl 是 Systemd 自带的日志管理工具，用于查看和管理 Systemd 系统及各类服务的日志，替代了传统的 /var/log 目录下的日志文件（如 /var/log/messages、/var/log/secure），核心优势是**日志集中管理、支持按服务/时间/优先级筛选、无需手动切割日志**。

本文将从基础用法、核心参数、实操场景、常见问题四个维度，手把手教你掌握 journalctl 命令，结合之前配置的 Systemd 服务（如 Hugo 服务）进行实操，所有命令均在 Rocky Linux 9 中测试，适配 Hugo v0\.160\.1 环境，其他主流 Linux 发行版（CentOS、Ubuntu 等）操作完全通用。

提示：journalctl 依赖 Systemd，只有使用 Systemd 作为系统管理器的 Linux 发行版（CentOS 7\+、Ubuntu 16\.04\+、Rocky Linux 等）才能使用，传统 SysVinit 系统（CentOS 6 及以下）不支持。

## 一、journalctl 核心基础（必懂）

在使用 journalctl 前，先掌握 3 个核心概念，避免后续踩坑：

- **日志存储位置**：默认日志存储在 `/var/log/journal/` 目录（二进制格式），无法直接用 cat、vi 查看，必须通过 journalctl 命令访问；若该目录不存在，日志会临时存储在内存中，重启后丢失。

- **日志优先级**：从低到高分为 7 级，排查问题时可按优先级筛选关键日志（常用前 4 级）：
        

    - 0 \(emerg\)：系统紧急状态，无法正常运行

    - 1 \(alert\)：必须立即处理的警报

    - 2 \(crit\)：严重错误

    - 3 \(err\)：普通错误（最常用，排查服务启动失败）

    - 4 \(warning\)：警告信息

    - 5 \(notice\)：普通通知

    - 6 \(info\)：普通信息

    - 7 \(debug\)：调试信息（用于深度排查）

- **核心关联**：journalctl 与 Systemd 服务深度绑定，可直接通过服务名筛选日志（如查看 Hugo 服务日志），这是排查 Systemd 服务启动失败的核心方法。

关键提示：journalctl 命令默认需要 root 权限（或 sudo），否则可能无法查看完整日志，建议全程使用 sudo 执行命令。

## 二、journalctl 基础用法（必记）

以下是 journalctl 最基础、最常用的用法，覆盖日志查看、分页、退出等核心操作，直接复制执行即可。

### 1\. 查看所有日志（默认分页）

查看系统所有日志，按时间倒序排列（最新日志在最后），默认进入分页模式：

```bash
# 查看所有日志（sudo 必加，否则日志不完整）
sudo journalctl
```

分页操作技巧（进入分页模式后使用）：

- 按 `空格键`：向下翻一页

- 按 `Enter 键`：向下翻一行

- 按 `b 键`：向上翻一页

- 按 `/ 关键词`：搜索日志中的关键词（按 n 键下一个，N 键上一个）

- 按 `q 键`：退出分页模式（最常用）

### 2\. 查看所有日志（不分页，一次性显示）

适合导出日志或快速浏览，避免分页操作：

```bash
# 不分页显示所有日志
sudo journalctl --no-pager
```

### 3\. 实时查看日志（最常用，排查实时问题）

实时监控日志输出，类似 tail \-f 命令，适合排查服务启动、运行中的实时错误：

```bash
# 实时查看所有日志
sudo journalctl -f

# 简化写法（效果同上）
sudo journalctl --follow
```

提示：按 `Ctrl \+ C` 停止实时监控。

### 4\. 查看日志时间范围（精准筛选）

排查特定时间段的日志，避免无关日志干扰，支持多种时间格式：

```bash
# 1. 查看最近 n 分钟的日志（最常用，如最近 30 分钟）
sudo journalctl --since "30min ago"

# 2. 查看最近 n 小时的日志（如最近 2 小时）
sudo journalctl --since "2h ago"

# 3. 查看指定时间段的日志（精准到分钟）
sudo journalctl --since "2026-04-22 10:00:00" --until "2026-04-22 11:00:00"

# 4. 查看今天的日志
sudo journalctl --since today

# 5. 查看昨天的日志
sudo journalctl --since yesterday --until today
```

## 三、journalctl 核心参数（重点，日志筛选）

journalctl 的核心价值的是“精准筛选日志”，以下是高频使用的核心参数，结合实操场景说明，重点掌握服务筛选、优先级筛选。

### 1\. 按 Systemd 服务筛选日志（最常用）

结合之前配置的 Systemd 服务（如 Hugo、Nginx），直接筛选指定服务的日志，排查服务启动失败、运行异常的核心方法：

```bash
# 查看指定服务的所有日志（以 Hugo 服务为例）
sudo journalctl -u hugo

# 实时查看指定服务的日志（排查服务启动/运行中的错误）
sudo journalctl -u hugo -f

# 查看指定服务最近 1 小时的日志
sudo journalctl -u hugo --since "1h ago"

# 查看指定服务的日志（不分页）
sudo journalctl -u hugo --no-pager

# 查看多个服务的日志（如 Hugo + Nginx）
sudo journalctl -u hugo -u nginx
```

重点：排查 Systemd 服务启动失败（如 hugo 服务显示 failed）时，优先执行 `sudo journalctl \-u hugo \-f`，实时查看错误日志，能快速定位问题（如路径错误、权限不足）。

### 2\. 按日志优先级筛选（过滤错误日志）

只查看指定优先级的日志，过滤无关的通知、调试信息，专注排查错误：

```bash
# 查看所有错误级别（err，优先级 3）及以上的日志（最常用）
sudo journalctl -p err

# 查看严重错误（crit，优先级 2）及以上的日志
sudo journalctl -p crit

# 查看警告（warning）及以上的日志
sudo journalctl -p warning

# 按优先级数字筛选（0=emerg，7=debug），如查看错误及以上（3及以下）
sudo journalctl -p 3

# 结合服务筛选：查看 Hugo 服务的错误日志
sudo journalctl -u hugo -p err
```

### 3\. 按进程/PID 筛选日志

查看指定进程或 PID 相关的日志，适合排查特定进程的运行问题：

```bash
# 查看指定 PID 的日志（如 PID 为 1234）
sudo journalctl _PID=1234

# 查看指定进程名的日志（如 hugo 进程）
sudo journalctl _COMM=hugo
```

### 4\. 按用户/组筛选日志

查看指定用户或用户组相关的日志，适合排查用户权限相关问题：

```bash
# 查看指定用户（如 user 用户，UID 为 1000）的日志
sudo journalctl _UID=1000
sudo journalctl _USER=user

# 查看指定用户组（如 user 组，GID 为 1000）的日志
sudo journalctl _GID=1000
sudo journalctl _GROUP=user
```

### 5\. 日志导出与保存（便于分析/分享）

将筛选后的日志导出到文件，方便后续分析或提交问题排查：

```bash
# 导出 Hugo 服务的所有日志到文件
sudo journalctl -u hugo --no-pager > hugo-log.txt

# 导出 Hugo 服务最近 1 小时的错误日志到文件
sudo journalctl -u hugo -p err --since "1h ago" --no-pager > hugo-error-log.txt

# 导出日志时保留时间戳（默认已保留，可显式指定）
sudo journalctl -u hugo --no-pager --output=short > hugo-log.txt
```

### 6\. 其他实用参数

```bash
# 查看日志的时间戳（精确到毫秒）
sudo journalctl --output=short-precise

# 查看日志的详细信息（包含进程、用户、优先级等）
sudo journalctl --output=verbose

# 清理日志（释放磁盘空间，默认保留7天日志）
sudo journalctl --vacuum-time=7d  # 保留最近7天日志
sudo journalctl --vacuum-size=100M  # 保留日志大小不超过100MB

# 查看日志统计信息（日志数量、时间范围等）
sudo journalctl --statistics
```

## 四、实操场景（结合 Systemd 服务，必练）

结合之前配置的 Hugo Systemd 服务，模拟 3 个常见排查场景，手把手练习 journalctl 的使用，快速掌握实操技巧。

### 场景 1：Hugo 服务启动失败，排查原因

```bash
# 1. 先查看 Hugo 服务状态，确认启动失败
sudo systemctl status hugo

# 2. 实时查看 Hugo 服务的错误日志（核心排查步骤）
sudo journalctl -u hugo -f -p err

# 3. 查看 Hugo 服务最近 30 分钟的所有日志，全面排查
sudo journalctl -u hugo --since "30min ago" --no-pager

# 4. 若日志过多，搜索关键词（如 "error"、"failed"）
sudo journalctl -u hugo --no-pager | grep -i "error"
```

示例错误排查：若日志提示“ExecStart=/usr/bin/hugo: No such file or directory”，说明 Hugo 路径错误，需用 `which hugo` 查看正确路径，修改服务配置文件。

### 场景 2：实时监控 Nginx 服务日志，排查访问异常

```bash
# 1. 实时查看 Nginx 服务的所有日志（含访问日志、错误日志）
sudo journalctl -u nginx -f

# 2. 只实时查看 Nginx 的错误日志
sudo journalctl -u nginx -f -p err

# 3. 筛选 Nginx 日志中包含 "404" 的访问记录（排查页面不存在问题）
sudo journalctl -u nginx --no-pager | grep "404"
```

### 场景 3：导出日志，用于问题反馈

```bash
# 导出 Hugo 服务最近 1 小时的所有日志，便于分享排查
sudo journalctl -u hugo --since "1h ago" --no-pager > hugo-recent-log.txt

# 导出系统所有错误日志，排查系统级问题
sudo journalctl -p err --since yesterday --no-pager > system-error-log.txt
```

## 五、常见问题排查（新手避坑）

使用 journalctl 时，新手容易遇到以下问题，给出具体解决方案，直接对照排查即可。

### 问题 1：执行 journalctl 提示“No journal files were found”

原因：1\. 日志目录 `/var/log/journal/` 不存在，日志临时存储在内存中，重启后丢失；2\. 没有 root 权限，无法访问日志。

解决：

```bash
# 1. 确保使用 sudo 执行
sudo journalctl

# 2. 若日志目录不存在，手动创建并重启 systemd-journald 服务
sudo mkdir -p /var/log/journal
sudo systemctl restart systemd-journald
```

### 问题 2：日志显示不完整，部分服务日志缺失

原因：1\. 未使用 sudo 执行，权限不足；2\. 服务未使用 Systemd 管理（如手动启动的服务，日志不会被 journalctl 捕获）。

解决：1\. 全程使用 sudo 执行 journalctl 命令；2\. 将服务配置为 Systemd 服务（参考之前的 Systemd 教程），确保日志被正常捕获。

### 问题 3：实时查看日志无输出，或日志延迟

原因：1\. 服务未运行，无新日志产生；2\. 日志缓存未刷新。

解决：1\. 确认服务正在运行（`sudo systemctl status 服务名`）；2\. 重启服务，触发新日志产生；3\. 执行 `sudo journalctl \-\-flush` 刷新日志缓存。

### 问题 4：日志占用磁盘空间过大

原因：journalctl 日志默认不会自动清理，长期运行会占用大量磁盘空间。

解决：清理旧日志，设置日志保留策略：

```bash
# 保留最近 7 天日志，删除更早的日志
sudo journalctl --vacuum-time=7d

# 保留日志大小不超过 100MB，自动删除多余日志
sudo journalctl --vacuum-size=100M

# 手动删除所有日志（谨慎使用，会丢失所有历史日志）
sudo journalctl --rotate
sudo journalctl --vacuum-time=1s
```

## 六、总结

journalctl 是 Linux 运维中**日志排查的核心工具**，尤其适合管理 Systemd 服务的日志，掌握“按服务筛选”“按时间筛选”“按优先级筛选”三个核心技巧，就能快速定位服务启动失败、系统异常等问题。

本文结合之前的 Systemd 服务实操，覆盖了 journalctl 的基础用法、核心参数和常见场景，新手建议先掌握 `sudo journalctl \-u 服务名 \-f`（实时查看服务日志）和 `sudo journalctl \-u 服务名 \-p err`（查看服务错误日志）这两个最常用命令，再逐步学习其他参数。

关键技巧：排查问题时，优先按“服务 \+ 优先级 \+ 时间”筛选日志，减少无关日志干扰；日志导出后，可使用 grep 命令进一步搜索关键词，提高排查效率。后续无论你配置任何 Systemd 服务，journalctl 都是排查问题的首选工具。

> （注：文档部分内容可能由 AI 生成）
