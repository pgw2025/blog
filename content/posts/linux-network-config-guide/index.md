---
title: "Linux 网络配置全攻略 手动设置 IP、子网掩码与网关"
date: 2026-06-03T12:00:00+08:00
draft: false
tags: ["Linux", "网络配置", "运维", "IP设置"]
categories: ["运维技术"]
author: "Will"
summary: "换了服务器连不上网？想给 Linux 设个固定 IP？本文手把手教你如何通过命令行设置 IP、子网掩码、网关和 DNS，涵盖临时生效与永久生效的多种方法。"
---

# Linux 网络配置全攻略：像高手一样玩转网络

在 Linux 的世界里，网络配置是每一位运维人员和开发者的必修课。无论你是刚租了一台云服务器，还是在家里折腾树莓派，掌握如何配置 **IP 地址、子网掩码、网关和 DNS** 都是至关重要的。

今天我们就用最直白的方式，把这些看似复杂的参数讲清楚，并教你几种常用的配置方法。

---

## 1. 核心概念：这四个参数是干啥的？

在动手之前，我们先打个比方。假设网络是一个巨大的邮政系统：
*   **IP 地址**：你家的“门牌号”。（如：`192.168.1.100`）
*   **子网掩码**：用来划分你家所在的“社区范围”。（如：`255.255.255.0`）
*   **网关 (Gateway)**：你家社区的“大门口”。想寄信到外地，必须先通过大门口。（如：`192.168.1.1`）
*   **DNS**：就像是“查号台”。你输入 `google.com`，它告诉你对应的 IP 是多少。

---

## 2. 第一步：看看你现在的网络

在修改之前，先得知道自己现在的状态。
*   输入 `ip addr`：查看所有的网卡信息和当前 IP。
*   输入 `ip route`：查看当前的路由表（能看到网关）。
*   注意网卡名称：通常叫 `eth0`、`ens33` 或 `enp0s3`，记好这个名字。

---

## 3. 临时配置：立马生效，重启失效

如果你只是临时想调通网络，用 `ip` 命令是最快的。

### 设置 IP 和子网掩码
```bash
# 语法：sudo ip addr add [IP/掩码位] dev [网卡名]
sudo ip addr add 192.168.1.100/24 dev eth0
```
*提示：`/24` 就等同于子网掩码 `255.255.255.0`。*

### 设置默认网关
```bash
sudo ip route add default via 192.168.1.1
```

---

## 4. 永久配置：重启也不怕

不同的 Linux 发行版，永久配置的方法不一样。目前主流的有两种：

### 方法 A：Ubuntu/Debian 推荐 (Netplan)
现在的 Ubuntu 基本都用 Netplan。配置文件通常在 `/etc/netplan/` 目录下（后缀是 `.yaml`）。

**编辑文件：** `sudo nano /etc/netplan/01-netcfg.yaml`
**填入内容：**
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses: [192.168.1.100/24]
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses: [8.8.8.8, 114.114.114.114]
```
**让它生效：** `sudo netplan apply`

---

### 方法 B：CentOS/Rocky/RHEL 推荐 (nmcli)
如果你在用红帽系的系统，`nmcli` 工具是首选。

```bash
# 1. 设置手动模式 (Static)
sudo nmcli con mod eth0 ipv4.method manual

# 2. 设置 IP 和掩码
sudo nmcli con mod eth0 ipv4.addresses 192.168.1.100/24

# 3. 设置网关
sudo nmcli con mod eth0 ipv4.gateway 192.168.1.1

# 4. 设置 DNS
sudo nmcli con mod eth0 ipv4.dns "8.8.8.8,114.114.114.114"

# 5. 重启网卡生效
sudo nmcli con up eth0
```

---

## 5. DNS 的终极修改位

如果 IP 没问题但打不开网页，通常是 DNS 的锅。
除了上面的永久设置，你也可以直接修改这个文件：
`sudo nano /etc/resolv.conf`
添加一行：
```text
nameserver 8.8.8.8
nameserver 114.114.114.114
```
*注意：在某些系统上，这个文件会被自动覆盖，建议优先使用 Netplan 或 nmcli 进行配置。*

---

## 6. 验证是否配置成功

配置完了，怎么知道通没通？
1.  **Ping 局域网**：`ping 192.168.1.1`（看看能不能连到路由器）。
2.  **Ping 外网**：`ping 8.8.8.8`（看看能不能出家门）。
3.  **Ping 域名**：`ping baidu.com`（看看 DNS 翻译正不正常）。

---

## 总结

配置网络并不难，关键是找准你的系统用的是哪套“管家”。
*   **临时调试**：用 `ip` 命令。
*   **Ubuntu 用户**：找 `netplan`。
*   **CentOS/Rocky 用户**：找 `nmcli`。

**下次服务器连不上网，先执行 `ip addr` 看看再说！**
