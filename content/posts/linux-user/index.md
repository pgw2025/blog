---
title: "Linux 用户与用户组管理详解"
date: 2026-06-26T13:00:00+08:00
draft: false
tags: ["Linux", "系统管理", "用户权限"]
categories: ["运维技术"]
author: "Will"
summary: "Linux 作为多用户多任务操作系统，其权限控制基于用户和用户组。本文将深度剖析 /etc/passwd、/etc/shadow 和 /etc/group 等核心配置文件，系统介绍用户与用户组的增删改查命令，并分享多用户协作中的安全最佳实践。"
---

在 Linux 操作系统中，所有的资源（文件、进程、网络连接等）都必须归属于特定的**用户（User）**和**用户组（Group）**。这是 Linux 系统实现进程隔离和权限控制的基石。

无论是部署 Web 服务、限制开发人员的访问权限，还是排查应用程序运行时的权限受阻，都需要对 Linux 的用户与用户组管理有清晰的认识。

---

## 一、 用户与用户组的基本概念

### 1. 用户的分类
Linux 系统通过 **UID（User ID，用户标识符）** 来识别用户，而非用户名。用户主要分为三类：
* **超级用户（root）**：UID 为 `0`。拥有系统的最高权限，不受常规权限限制。
* **系统用户**：UID 范围通常为 `1 - 999`（不同发行版略有差异）。这些用户不用于人工登录，而是专门给系统服务或后台进程（如 `nginx`、`mysql`、`bin` 等）使用，以此实现权限隔离。
* **普通用户**：UID 范围通常从 `1000` 开始。由管理员创建，用于日常操作，权限受限。

### 2. 用户组的分类
用户组（Group）是具有相同权限特征的用户的集合。Linux 通过 **GID（Group ID）** 来识别用户组。
* **初始组（Primary Group）**：每个用户在创建时**必须且只能有一个**初始组，通常默认与用户名同名。
* **附加组/次要组（Supplementary Group）**：用户可以同时加入多个附加组，以此获得这些组所拥有的额外权限。

---

## 二、 核心系统配置文件解析

Linux 用户的基本信息、密码规则和组关系，都保存在特定的系统配置文件中。理解这些文件有助于直接进行低级调试。

### 1. `/etc/passwd` —— 用户基本信息文件
每行代表一个用户，字段之间用冒号 `:` 分隔：
```text
root:x:0:0:root:/root:/bin/bash
will:x:1000:1000:Will's PC:/home/will:/bin/bash
nginx:x:995:993:Nginx web server:/var/lib/nginx:/sbin/nologin
```
**字段详细拆解（以 `will` 为例）**：
1. `will`：**用户名**。
2. `x`：**密码占位符**。实际加密后的密码存储在 `/etc/shadow` 中。
3. `1000`：**UID**。
4. `1000`：**初始组 GID**。
5. `Will's PC`：**注释/描述信息**。
6. `/home/will`：**家目录（Home Directory）**。用户登录后的默认工作路径。
7. `/bin/bash`：**登录 Shell**。若为 `/sbin/nologin`，表示该用户无法登录系统，通常用于系统服务用户。

### 2. `/etc/shadow` —— 用户密码与安全控制文件
保存经过加密算法哈希后的密码以及密码有效期等信息。由于其包含敏感数据，该文件仅对 root 用户可读。

### 3. `/etc/group` —— 用户组信息文件
每行代表一个组，同样用 `:` 分隔：
```text
wheel:x:10:will,jack
www-data:x:33:
```
**字段拆解**：
1. `wheel`：**组名**。
2. `x`：**组密码占位符**（一般不设置）。
3. `10`：**GID**。
4. `will,jack`：**附加用户列表**。表明 `will` 和 `jack` 将此组作为附加组。

---

## 三、 用户管理常用命令

### 1. 创建用户：`useradd`
```bash
# 示例 1：创建普通用户 will，并自动创建其家目录（默认使用 /bin/bash）
sudo useradd -m will

# 示例 2：创建一个专门运行 Nginx 服务的系统用户（无家目录，不允许登录系统）
sudo useradd -r -s /sbin/nologin nginx

# 示例 3：创建用户并指定 UID 路径和初始组
sudo useradd -u 1500 -g developers -m developer01
```
*常用参数说明*：
* `-m`：强制建立家目录。
* `-r`：创建系统用户（UID 在系统用户范围内，且默认不建家目录）。
* `-s`：指定用户登录的 Shell。
* `-g`：指定用户的初始组（主组）。

### 2. 修改用户密码：`passwd`
新建用户后，必须为其设置密码才能登录：
```bash
# 修改当前登录用户的密码
passwd

# 由管理员修改指定用户的密码
sudo passwd will
```

### 3. 修改用户属性：`usermod`
`usermod` 用于变更已存在用户的各项配置：
```bash
# 示例 1：修改用户名
sudo usermod -l new_name old_name

# 示例 2：修改用户家目录
sudo usermod -d /data/home/will will

# 示例 3：锁定用户（禁止其登录）/ 解锁用户
sudo usermod -L will   # Lock
sudo usermod -U will   # Unlock
```

### 4. 删除用户：`userdel`
```bash
# 仅删除用户账号，保留其家目录下的文件
sudo userdel will

# 连同家目录及系统中的邮件缓冲池一并删除（最常用）
sudo userdel -r will
```

---

## 四、 用户组管理常用命令

### 1. 创建与删除组
```bash
# 创建一个名为 developers 的组
sudo groupadd developers

# 删除组（只有在组内没有用户将其作为初始组时，才能删除该组）
sudo groupdel developers
```

### 2. 组员管理：`gpasswd` 与 `usermod` 的配合
如何将一个用户加入到某个组中，是权限协作中最常见的操作。

#### 方法 A：使用 `usermod`（最常用）
```bash
# 将用户 will 添加到 docker 组作为其附加组
sudo usermod -aG docker will
```
> **极其重要的安全警告**：
> 在使用 `usermod` 修改附加组时，必须使用 **`-a` (append，追加)** 参数。如果只写 `-G` 而漏掉了 `-a`（即 `usermod -G group_name user`），系统会**清除该用户之前所有的附加组**，只保留当前设置的这一个。这经常导致管理员不小心将自己从 `sudo` 或 `wheel` 组中移除。

#### 方法 B：使用 `gpasswd`（对组本身进行操作）
```bash
# 将用户 will 添加到 developers 组
sudo gpasswd -a will developers

# 将用户 will 从 developers 组中移除
sudo gpasswd -d will developers
```

---

## 五、 实战场景与排查技巧

### 1. 检查当前用户的身份与所属组
如果你在执行某项操作时权限受阻，可以使用 `id` 或 `whoami` 查看当前用户的状态：
```bash
id
# 输出示例：uid=1000(will) gid=1000(will) groups=1000(will),10(wheel),991(docker)
```
通过输出，可以清晰地看到自己的 UID、初始组（gid）以及所有加入的附加组（groups）。

### 2. 授权普通用户执行 `sudo`（提权）
在 Centos/RHEL 或 Ubuntu/Debian 系统中，可以通过将普通用户加入特定的管理员附加组，来赋予其通过 `sudo` 执行系统级命令的权限：
```bash
# 在 CentOS / RHEL / Fedora 中（加入 wheel 组）
sudo usermod -aG wheel will

# 在 Ubuntu / Debian 中（加入 sudo 组）
sudo usermod -aG sudo will
```

### 3. 多人协作共享目录的规范配置
假设开发团队有多个成员，他们需要共同往 `/var/www/project` 目录下写入代码，并且能够互相修改。

**最佳实践配置步骤**：
1. 创建一个公共的开发用户组：
   ```bash
   sudo groupadd webdev
   ```
2. 将开发人员（如 `will` 和 `jack`）加入该组：
   ```bash
   sudo usermod -aG webdev will
   sudo usermod -aG webdev jack
   ```
3. 将项目目录的所有者修改为 root，所属组修改为 `webdev`：
   ```bash
   sudo chown -R root:webdev /var/www/project
   ```
4. 将目录权限设为 2775（所有者和组可读写，且**设置 SGID**）：
   ```bash
   sudo chmod -R 2775 /var/www/project
   ```
   *说明：设置了 2 位的 SGID 权限后，未来任何组员在 `/var/www/project` 中创建的新文件，其所属组都会自动强制设定为 `webdev`，从而彻底避免了“因为其他人创建的文件默认属于个人主组而导致别人无法编辑”的尴尬局面。*