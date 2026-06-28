
---
title: "Linux ps 命令终极指南：从零基础到进程管理高手"
date: 2026-06-24T20:00:00+08:00
draft: false
tags: ["Linux", "ps", "进程管理", "运维", "命令行"]
categories: ["运维技术", "Linux"]
series: ["Linux 学习系列"]
author: "Will"
summary: "ps（Process Status）是 Linux 中查看进程信息的核心命令。本文从零基础出发，全面拆解 ps 命令的所有参数、输出字段与实战用法，带你真正掌握 Linux 进程管理。"
---

`ps`（Process Status）是 Linux 系统中**查看当前系统进程状态**的核心命令。无论你是排查服务故障、定位资源占用，还是日常查看"谁在跑、跑了啥"，`ps` 都是你绕不开的第一利器。

很多人用了多年 Linux，却只会 `ps aux` 这一板斧。实际上 `ps` 的参数体系极其庞大，输出信息丰富到可以当作一本"进程体检报告"来读。

本文将从**最基础的概念**出发，**逐个参数、逐个字段**地深入讲解，配合大量真实示例，让你读完就能成为 Linux 进程管理的行家。所有命令均在 Rocky Linux 9 中实测，同样适配 CentOS、Ubuntu、Debian 等主流发行版。

---

## 一、前置知识：理解 Linux 进程

在学 `ps` 之前，先搞懂几个核心概念，否则后面看输出会一头雾水。

### 1. 什么是进程？

**进程 = 正在运行的程序**。你在终端敲一个命令，系统就会创建一个进程来执行它。比如你运行 `vim /etc/hosts`，系统就会创建一个 `vim` 进程。

每个进程都有一个**唯一编号**，叫做 **PID**（Process ID）。系统启动后的第一个进程是 `systemd`（或老系统的 `init`），PID 固定为 **1**，是所有进程的"老祖宗"。

### 2. 进程之间的"家族关系"

Linux 中的进程是**树形结构**的——每个进程都有一个"父进程"（Parent Process），父进程的 PID 叫 **PPID**。

```
systemd (PID 1)
├── sshd (PID 800)
│   └── bash (PID 1234)      ← 你登录后的 Shell
│       └── vim (PID 1567)   ← 你在 Shell 里启动的 vim
├── nginx (PID 900)
│   ├── nginx worker (PID 901)
│   └── nginx worker (PID 902)
└── mysqld (PID 1100)
```

### 3. 进程的 5 种核心状态

| 状态码 | 状态名称 | 大白话解释 |
| :---: | :--- | :--- |
| **R** | Running（运行中） | 正在 CPU 上执行，或者排队等着用 CPU |
| **S** | Sleeping（可中断睡眠） | 正在等某个事件（比如等用户输入、等网络数据），随时可以被唤醒 |
| **D** | Disk Sleep（不可中断睡眠） | 正在等磁盘 I/O 完成，**连 kill -9 都杀不掉**，必须等 I/O 结束 |
| **T** | Stopped（已停止） | 被信号暂停了（比如你按了 Ctrl+Z），可以用 `fg` 恢复 |
| **Z** | Zombie（僵尸进程） | 进程已经跑完了，但父进程还没来"收尸"（没调用 wait()），残留在进程表里 |

> 💡 **小贴士**：状态码后面还可能跟着修饰符，比如 `Ss`（S 状态 + 会话领导者）、`R+`（R 状态 + 前台进程组），后文会详细讲解。

---

## 二、ps 命令的三大参数风格

`ps` 命令有一个**非常独特的设计**：它同时支持三种完全不同的参数风格！这是很多初学者困惑的根源——为什么有时候加 `-`，有时候不加？

| 风格 | 来源 | 特征 | 举例 |
| :--- | :--- | :--- | :--- |
| **UNIX 风格** | System V 系统 | 参数前面**有**短横线 `-` | `ps -ef`、`ps -aux` |
| **BSD 风格** | BSD 系统 | 参数前面**没有**短横线 | `ps aux`、`ps lax` |
| **GNU 长选项** | GNU 扩展 | 参数前面有**两个**短横线 `--` | `ps --forest`、`ps --sort` |

> ⚠️ **特别注意**：`ps aux`（BSD 风格，无横线）和 `ps -aux`（UNIX 风格，有横线）的含义**完全不同**！前者表示"显示所有用户的所有进程"，后者会被解析为 `-a -u -x`，在某些场景下结果可能有差异。**建议初学者养成好习惯：BSD 风格不加横线，UNIX 风格加横线，不要混用。**

---

## 三、默认输出字段含义详解

在不加任何参数时，直接执行 `ps`，只会显示**当前终端**启动的进程：

```bash
$ ps
  PID TTY          TIME CMD
 1234 pts/0    00:00:00 bash
 5678 pts/0    00:00:00 ps
```

各字段含义如下：

| 字段 | 英文全称 | 含义 |
| :--- | :--- | :--- |
| **PID** | Process ID | 进程的唯一编号，在整个系统中不重复 |
| **TTY** | Teletype（终端设备） | 进程关联的终端。`pts/0` 表示第一个远程伪终端，`tty1` 表示本地第一个虚拟控制台，`?` 表示没有关联终端（守护进程） |
| **TIME** | CPU Time | 进程累计占用 CPU 的时间（不是运行了多久，是真正消耗 CPU 的时间） |
| **CMD** | Command | 启动进程的命令名称 |

---

## 四、核心参数大全（分类详解）

### 4.1 进程选择参数 —— "看谁的进程"

这组参数决定 `ps` 显示哪些进程，是最基础、最常用的参数。

#### BSD 风格（不带横线）

| 参数 | 功能说明 | 通俗解释 |
| :--- | :--- | :--- |
| `a` | 显示所有终端上的进程 | 默认只看自己终端的，加了 `a` 就能看到**所有终端**用户的进程 |
| `x` | 显示没有关联终端的进程 | 很多后台服务（nginx、mysql）没有终端，加 `x` 才能看到它们 |
| `ax` / `aux` | 二者组合 | 显示系统上**所有进程**——这就是为什么 `ps aux` 是最常用的命令 |

#### UNIX 风格（带横线）

| 参数 | 功能说明 | 通俗解释 |
| :--- | :--- | :--- |
| `-e` | 显示所有进程 | 等同于 `-A`，效果和 BSD 的 `ax` 类似 |
| `-A` | 显示所有进程 | 和 `-e` 完全相同，只是另一种写法 |
| `-a` | 显示所有终端上的进程（排除会话领导者） | 和 BSD 的 `a` 类似，但会排除会话领导者进程 |
| `-d` | 显示所有进程（排除会话领导者） | 和 `-a` 类似，但包含没有终端的进程 |
| `-N` / `--deselect` | 反向选择 | 和其他选择参数配合使用，显示"不满足条件"的进程 |

#### 按条件筛选

| 参数 | 功能说明 | 示例 |
| :--- | :--- | :--- |
| `-p PID` | 按 PID 查看指定进程 | `ps -p 1234` — 只看 PID 为 1234 的进程 |
| `--pid PID` | 同上（GNU 长选项写法） | `ps --pid 1234` |
| `-C 命令名` | 按命令名筛选 | `ps -C nginx` — 只看命令名为 nginx 的进程 |
| `-u 用户名` | 按**有效用户**（effective user）筛选 | `ps -u root` — 只看 root 用户的进程 |
| `-U 用户名` | 按**真实用户**（real user）筛选 | `ps -U nginx` — 只看真实用户为 nginx 的进程 |
| `U 用户名` | BSD 风格，按用户筛选 | `ps U root` |
| `-g 组名/GID` | 按**有效组**筛选 | `ps -g wheel` |
| `-G 组名/GID` | 按**真实组**筛选 | `ps -G root` |
| `-t 终端` | 按终端筛选 | `ps -t pts/0` — 只看 pts/0 终端的进程 |
| `-s SID` | 按会话 ID 筛选 | `ps -s 1234` — 只看会话 ID 为 1234 的进程 |
| `--ppid PPID` | 按父进程 ID 筛选 | `ps --ppid 1` — 查看所有由 systemd 直接启动的子进程 |
| `-q PID` | 快速模式按 PID 查看 | `ps -q 1234` — 比 `-p` 更快，跳过部分信息采集 |

> 💡 **有效用户 vs 真实用户**：举个例子，普通用户执行 `passwd` 修改密码时，`passwd` 程序的真实用户是你自己，但有效用户是 root（因为 passwd 有 SUID 权限），所以 `-u root` 能看到它，`-U root` 看不到。

---

### 4.2 输出格式参数 —— "显示哪些列"

`ps` 最强大的地方之一就是你可以**精准控制**它输出哪些信息。

#### 预设格式（一键切换）

| 参数 | 格式名 | 显示的列 | 适用场景 |
| :--- | :--- | :--- | :--- |
| `u`（BSD） | 用户格式 | USER, PID, %CPU, %MEM, VSZ, RSS, TTY, STAT, START, TIME, COMMAND | **最常用**，信息全面 |
| `-f` | 完整格式 | UID, PID, PPID, C, STIME, TTY, TIME, CMD | 需要看**父子关系**时用 |
| `-F` | 超完整格式 | UID, PID, PPID, C, SZ, RSS, PSR, STIME, TTY, TIME, CMD | 比 `-f` 多了内存和 CPU 核心信息 |
| `l`（BSD） | 长格式 | F, UID, PID, PPID, PRI, NI, VSZ, RSS, WCHAN, STAT, TTY, TIME, COMMAND | 需要看**优先级**和**等待通道**时用 |
| `-l` | UNIX 长格式 | F, S, UID, PID, PPID, C, PRI, NI, ADDR, SZ, WCHAN, TTY, TIME, CMD | 和 BSD `l` 类似 |
| `-j` | 作业格式 | PID, PGID, SID, TTY, TIME, CMD | 需要看**进程组**和**会话**信息时用 |
| `j`（BSD） | BSD 作业格式 | PPID, PID, PGID, SID, TTY, TPGID, STAT, UID, TIME, COMMAND | 同上，略有不同 |
| `s` | 信号格式 | UID, PID, PENDING, BLOCKED, IGNORED, CAUGHT, STAT, TTY, TIME, COMMAND | 需要分析**信号处理**时用 |
| `v` | 虚拟内存格式 | PID, STAT, TIME, MAJFL, TRS, DRS, RSS, %MEM, COMMAND | 需要深入分析**内存使用**时用 |
| `X` | 旧 Linux 格式 | PID, STACKP, ESP, EIP, TMOUT, ALARM, STAT, TTY, TIME, COMMAND | 极少使用 |

#### 自定义输出（最灵活）

| 参数 | 功能说明 | 示例 |
| :--- | :--- | :--- |
| `-o 字段列表` | **自定义输出列**，用逗号分隔 | `ps -eo pid,user,%cpu,%mem,cmd` |
| `o 字段列表`（BSD） | 同上的 BSD 写法 | `ps axo pid,user,%cpu,%mem,cmd` |
| `--format 字段列表` | GNU 长选项写法 | `ps --format pid,user,%cpu` |
| `-O 字段列表` | 在默认输出的基础上**插入**额外列 | `ps -eO %cpu,%mem` — 在默认列的 PID 后面插入 CPU 和内存占比 |

---

### 4.3 输出修饰参数 —— "怎么显示"

| 参数 | 功能说明 | 通俗解释 |
| :--- | :--- | :--- |
| `--forest` | **树形显示**进程的父子关系 | 用缩进和连线画出进程家族树，一目了然 |
| `f`（BSD） | BSD 风格树形显示 | 和 `--forest` 效果相同 |
| `-H` | 显示进程层级（缩进） | 和 `--forest` 类似，但用空格缩进而不是 ASCII 画线 |
| `--headers` | **每一页都重复显示表头** | 输出很长的进程列表时，翻屏后也能看到列名 |
| `--no-headers` | **不显示表头** | 写脚本解析输出时非常有用，避免表头干扰 |
| `-w` / `w` | **加宽输出**，不截断长命令 | 默认输出会按终端宽度截断，加 `w` 可以放宽；加 `ww` 则完全不限制宽度 |
| `e`（BSD） | 在命令后面**追加显示环境变量** | 调试程序启动参数时有用，可以看到程序运行时的完整环境 |
| `c` | 只显示**可执行文件名**，不显示完整命令行参数 | 比如只显示 `nginx` 而非 `nginx: master process /usr/sbin/nginx` |
| `-n namelist` | 指定 System.map 文件用于 WCHAN 解析 | 很少用到，内核开发者才需要 |
| `n` | WCHAN 和 USER 字段用数字而非名称显示 | 脚本处理时可能用到 |
| `--cols N` | 设置输出的最大列宽 | `ps aux --cols 200` |
| `--lines N` | 设置输出的最大行数 | `ps aux --lines 50` |

---

### 4.4 排序参数 —— "按什么排"

| 参数 | 功能说明 | 示例 |
| :--- | :--- | :--- |
| `--sort 字段` | 按指定字段**升序排列** | `ps aux --sort %cpu` — 按 CPU 占用率从小到大排列 |
| `--sort -字段` | 按指定字段**降序排列** | `ps aux --sort -%mem` — 按内存占用率从大到小排列 |
| `--sort 字段1,-字段2` | **多字段排序** | `ps aux --sort -%cpu,-%mem` — 先按 CPU 降序，CPU 相同再按内存降序 |
| `k 字段`（BSD） | BSD 风格的排序写法 | `ps auxk -%cpu` |

常用的排序字段包括：

| 排序字段 | 含义 |
| :--- | :--- |
| `%cpu` / `pcpu` | CPU 占用百分比 |
| `%mem` / `pmem` | 内存占用百分比 |
| `rss` | 实际使用的物理内存（KB） |
| `vsz` | 虚拟内存大小（KB） |
| `pid` | 进程 ID |
| `time` / `cputime` | CPU 累计使用时间 |
| `etime` | 进程运行至今的经过时间 |
| `start` / `start_time` | 进程启动时间 |
| `user` | 用户名 |
| `comm` / `cmd` | 命令名 |
| `ni` | Nice 值（优先级调整值） |

---

### 4.5 线程显示参数

| 参数 | 功能说明 | 通俗解释 |
| :--- | :--- | :--- |
| `-L` | 显示线程，增加 **LWP**（轻量级进程 ID）和 **NLWP**（线程总数）列 | 排查多线程程序（如 Java）时必备 |
| `-T` | 显示线程，增加 **SPID**（系统线程 ID）列 | 和 `-L` 类似，用不同的列名 |
| `H` | 将线程当作独立进程来显示 | 每个线程一行，不区分主线程和子线程 |
| `-m` / `m` | 在进程行下方显示该进程的所有线程 | 进程和线程的层级关系更清晰 |

---

## 五、输出字段完全词典

当你使用 `-o` 自定义输出，或者看到不认识的列名时，这张表就是你的速查词典。

### 5.1 进程标识类

| 字段名 | 含义 | 说明 |
| :--- | :--- | :--- |
| `pid` | 进程 ID | 系统中唯一标识一个进程的数字 |
| `ppid` | 父进程 ID | 创建本进程的那个进程的 PID |
| `pgid` / `pgrp` | 进程组 ID | 同一管道中的进程共享一个 PGID |
| `sid` | 会话 ID | 同一个登录会话中的所有进程共享一个 SID |
| `tpgid` | 前台进程组 ID | 当前终端的前台进程组。如果为 -1，表示进程没有关联终端 |
| `lwp` / `spid` | 线程 ID（轻量级进程 ID） | 线程在内核中的唯一编号 |
| `nlwp` | 线程数 | 该进程包含的线程总数 |
| `tgid` | 线程组 ID | 等同于主线程的 PID |

### 5.2 用户与权限类

| 字段名 | 含义 | 说明 |
| :--- | :--- | :--- |
| `user` / `euser` | 有效用户名 | 决定进程当前**实际拥有的权限** |
| `ruser` | 真实用户名 | 启动进程的那个人 |
| `uid` / `euid` | 有效用户 ID | user 的数字形式 |
| `ruid` | 真实用户 ID | ruser 的数字形式 |
| `group` / `egroup` | 有效组名 | 进程当前有效所属的组 |
| `rgroup` | 真实组名 | 启动进程的用户所属的组 |
| `gid` / `egid` | 有效组 ID | group 的数字形式 |
| `rgid` | 真实组 ID | rgroup 的数字形式 |
| `suid` | 保存的用户 ID | SUID 相关，进程切换身份时记住原始权限 |
| `sgid` | 保存的组 ID | SGID 相关 |
| `fuid` | 文件系统用户 ID | Linux 特有，用于文件系统权限判断 |
| `fgid` | 文件系统组 ID | 同上 |
| `supgid` | 附加组 ID 列表 | 进程所属的所有附加组 |
| `supgrp` | 附加组名称列表 | supgid 的名称形式 |

### 5.3 CPU 与调度类

| 字段名 | 含义 | 说明 |
| :--- | :--- | :--- |
| `%cpu` / `pcpu` | CPU 占用百分比 | 进程生命周期内 CPU 使用时间的百分比（非实时瞬时值） |
| `c` | CPU 利用率（整数） | 类似 `%cpu` 的整数简化版 |
| `time` / `cputime` | 累计 CPU 时间 | 格式 `[DD-]HH:MM:SS`，进程总共消耗的 CPU 时间 |
| `etime` | 经过时间 | 进程从启动到现在的**墙钟时间**（不是 CPU 时间） |
| `etimes` | 经过时间（秒数） | `etime` 的纯数字版本，方便脚本计算 |
| `pri` | 优先级 | 内核调度优先级（数字越大优先级越高）|
| `ni` | Nice 值 | 用户可调整的优先级，范围 **-20（最高优先）到 19（最低优先）** |
| `cls` / `class` / `policy` | 调度策略 | `TS`（普通时间片）、`FF`（FIFO 实时）、`RR`（轮转实时）等 |
| `rtprio` | 实时优先级 | 实时调度策略下的优先级（0-99） |
| `psr` | 处理器编号 | 进程当前运行在哪个 CPU 核心上（从 0 开始编号） |

### 5.4 内存类

| 字段名 | 含义 | 说明 |
| :--- | :--- | :--- |
| `%mem` / `pmem` | 内存占用百分比 | 进程 RSS 占系统总物理内存的百分比 |
| `vsz` / `vsize` | 虚拟内存大小（KB） | 进程**申请的**全部虚拟内存空间，包含还没真正用到的部分 |
| `rss` / `rssize` | 常驻内存大小（KB） | 进程**实际占用的**物理内存（不含 swap），**最能反映真实内存消耗** |
| `sz` | 物理页数 | 进程核心映像的物理页面数量 |
| `trs` | 文本段常驻大小 | 可执行代码占用的物理内存 |
| `drs` | 数据段常驻大小 | 数据+堆+栈占用的物理内存 |
| `size` | 交换空间估算 | 进程如果全部需要换出到 swap，大约需要多少空间 |
| `majflt` | 主缺页次数 | 进程发生的"硬缺页"（需要从磁盘读入数据）次数，数值高说明内存不够用 |
| `minflt` | 次缺页次数 | "软缺页"次数（数据在内存中但页表未映射），通常不用太关注 |

> 💡 **VSZ vs RSS 大白话**：VSZ 好比你**申请了 100 平米的房子**，RSS 是你**实际住了 60 平米**。看内存占用要看 RSS，VSZ 可能虚高。

### 5.5 状态与控制类

| 字段名 | 含义 | 说明 |
| :--- | :--- | :--- |
| `stat` / `state` | 进程状态 | 前文介绍的 R/S/D/T/Z 状态码，加上修饰符 |
| `s` | 简化状态 | 只显示单字母状态，不显示修饰符 |
| `f` / `flag` | 进程标志（十六进制） | 内核标志位，极少日常使用 |
| `wchan` | 等待通道 | 进程正在等待的内核函数名。如果进程在运行则显示 `-` |
| `blocked` | 被阻塞的信号掩码 | 十六进制显示哪些信号被进程阻塞了 |
| `caught` | 被捕获的信号掩码 | 哪些信号被进程注册了处理函数 |
| `ignored` | 被忽略的信号掩码 | 哪些信号被进程主动忽略 |
| `pending` | 等待处理的信号 | 当前已发送但尚未被进程处理的信号 |

#### 状态码修饰符详解

当你看到 `STAT` 列显示 `Ss`、`R+`、`Sl` 这样的组合时，第一个字母是主状态，后面的字母是修饰符：

| 修饰符 | 含义 |
| :--- | :--- |
| `<` | 高优先级进程（Nice 值 < 0） |
| `N` | 低优先级进程（Nice 值 > 0） |
| `L` | 进程有页面锁定在内存中（实时进程或 AIO 操作） |
| `s` | 会话领导者（Session Leader）—— 通常是 Shell 或服务主进程 |
| `l` | 多线程进程（使用 CLONE_THREAD） |
| `+` | 进程在前台进程组中（你在终端正在交互的进程） |

---

## 六、十大经典用法（实战演练）

掌握了参数和字段，下面通过**真实场景**来演练，学完就能直接上手。

### 场景 1：查看系统所有进程（最常用的两条命令）

```bash
# BSD 风格（推荐，信息最全面）
ps aux

# UNIX 风格（推荐需要看父子关系时用）
ps -ef
```

**`ps aux` 输出解读**：

```bash
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.3 171540 13236 ?        Ss   Jun20   0:05 /usr/lib/systemd/systemd
root         2  0.0  0.0      0     0 ?        S    Jun20   0:00 [kthreadd]
nginx      900  0.0  0.1  55432  5120 ?        S    Jun20   0:02 nginx: worker process
mysql     1100  0.5  5.2 1283456 212480 ?      Sl   Jun20  12:35 /usr/sbin/mysqld
will      1234  0.0  0.1  25768  4560 pts/0    Ss   10:30   0:00 -bash
```

### 场景 2：找出最吃 CPU 的前 10 个进程

```bash
# 方法一：ps 自带排序
ps aux --sort=-%cpu | head -n 11

# 方法二：自定义输出，更清晰
ps -eo pid,user,%cpu,%mem,comm --sort=-%cpu | head -n 11
```

### 场景 3：找出最吃内存的前 10 个进程

```bash
ps -eo pid,user,rss,%mem,comm --sort=-rss | head -n 11
```

> 💡 这里用 `rss`（实际物理内存）排序比 `%mem` 更精确，因为 `%mem` 是百分比可能精度不够。

### 场景 4：查看某个服务的进程状态

```bash
# 按命令名查找（精确匹配）
ps -C nginx -o pid,user,%cpu,%mem,stat,start,cmd

# 按用户查找
ps -u mysql -o pid,%cpu,%mem,rss,cmd

# 用 grep 模糊查找（万能方法，但注意排除 grep 自身）
ps aux | grep "[n]ginx"
```

> 💡 **`grep "[n]ginx"` 的小技巧**：正则 `[n]` 匹配字母 `n`，但 grep 命令自己的进程显示为 `grep [n]ginx`，不包含字面的 `nginx` 所以不会被匹配到，就不用再加 `grep -v grep` 了。

### 场景 5：查看进程的父子关系（进程树）

```bash
# 方法一：森林视图
ps -ef --forest

# 方法二：只看某个服务的进程树
ps -ef --forest | grep -E "nginx|PID"

# 方法三：BSD 风格
ps auxf
```

输出效果：

```bash
UID        PID  PPID  C STIME TTY      TIME     CMD
root       900     1  0 Jun20 ?        00:00:00 nginx: master process /usr/sbin/nginx
nginx      901   900  0 Jun20 ?        00:00:02  \_ nginx: worker process
nginx      902   900  0 Jun20 ?        00:00:01  \_ nginx: worker process
```

### 场景 6：查看进程的线程信息

```bash
# 查看某个进程的所有线程
ps -Lp 1100

# 输出线程 ID 和线程数
ps -eo pid,lwp,nlwp,comm | grep mysqld

# 查看 Java 应用的线程数（排查线程泄漏）
ps -o pid,nlwp,cmd -p $(pgrep java)
```

### 场景 7：查看进程运行了多久

```bash
# 显示进程的启动时间和已运行时长
ps -eo pid,lstart,etime,cmd | grep nginx

# lstart：完整启动时间（Wed Jun 20 08:30:00 2026）
# etime：已运行时长（4-11:30:00 表示 4 天 11 小时 30 分钟）
```

### 场景 8：查看进程运行在哪个 CPU 核心

```bash
ps -eo pid,psr,%cpu,comm --sort=-psr | head -n 20
```

> 💡 在多核 CPU 服务器上，可以用这个来检查负载是否均匀分布在各个核心上。

### 场景 9：监控僵尸进程

```bash
# 查找所有僵尸进程
ps aux | awk '$8 ~ /Z/'

# 或者更精确的方式
ps -eo pid,ppid,stat,cmd | grep "^.*Z"

# 找到僵尸进程的父进程（需要杀父进程来清理僵尸）
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/ {print "僵尸PID:"$1, "父PID:"$2, "命令:"$4}'
```

### 场景 10：实时监控进程（配合 watch）

```bash
# 每 2 秒刷新一次，实时监控 CPU 占用前 10 的进程
watch -n 2 'ps -eo pid,user,%cpu,%mem,comm --sort=-%cpu | head -n 11'

# 每秒刷新，监控特定服务
watch -n 1 'ps -C nginx -o pid,%cpu,%mem,stat,etime'
```

---

## 七、`-o` 自定义输出常用字段速查表

`-o` 是 `ps` 最灵活的参数，下面列出最常用的字段组合，可以直接复制使用：

```bash
# 通用排查组合（推荐日常使用）
ps -eo pid,user,%cpu,%mem,rss,vsz,stat,start,time,comm --sort=-%cpu

# 内存深度分析
ps -eo pid,user,rss,vsz,%mem,majflt,minflt,comm --sort=-rss

# 进程关系分析
ps -eo pid,ppid,pgid,sid,tpgid,user,comm --forest

# 调度与优先级分析
ps -eo pid,user,ni,pri,rtprio,cls,psr,%cpu,comm --sort=-pri

# 线程分析
ps -eLo pid,lwp,nlwp,user,%cpu,%mem,comm --sort=-nlwp

# 信号分析
ps -eo pid,user,pending,blocked,ignored,caught,comm

# 进程启动信息
ps -eo pid,user,lstart,etime,etimes,comm --sort=-etimes

# 安全审计（权限分析）
ps -eo pid,euser,ruser,egroup,rgroup,comm
```

---

## 八、ps 与其他命令的黄金搭档

`ps` 虽然强大，但和其他命令搭配使用才能发挥最大威力。

### 1. ps + grep：模糊搜索进程

```bash
# 查找包含 "python" 的所有进程
ps aux | grep "[p]ython"

# 查找监听 8080 端口的进程（配合 ss）
ss -tlnp | grep 8080
```

### 2. ps + awk：数据提取与计算

```bash
# 计算所有进程的总内存占用
ps -eo rss | awk '{sum+=$1} END {printf "总内存占用: %.2f MB\n", sum/1024}'

# 统计每个用户的进程数
ps -eo user | sort | uniq -c | sort -rn | head -n 10

# 找出 CPU 占用超过 50% 的进程
ps -eo pid,user,%cpu,comm | awk '$3 > 50'
```

### 3. ps + xargs：批量操作进程

```bash
# 杀掉所有 python 进程
ps -C python -o pid= | xargs kill -9

# 杀掉某用户的所有进程
ps -u testuser -o pid= | xargs kill -15
```

### 4. ps + sort + uniq：进程统计分析

```bash
# 统计各状态的进程数
ps -eo stat | cut -c1 | sort | uniq -c | sort -rn

# 输出示例：
#  150 S    ← 150 个在睡眠
#   12 R    ← 12 个在运行
#    3 D    ← 3 个在等待磁盘 I/O
#    1 Z    ← 1 个僵尸进程（需要关注！）
```

### 5. ps + pstree：更直观的进程树

```bash
# pstree 是 ps --forest 的增强版
pstree -p          # 显示 PID
pstree -u          # 显示用户
pstree -a          # 显示完整命令行
pstree -p 900      # 只看 PID 900 的子树
```

---

## 九、ps 与 top/htop 的区别

很多人会问：有了 `top` 和 `htop`，还需要 `ps` 吗？答案是：**当然需要，它们定位不同**。

| 对比维度 | ps | top / htop |
| :--- | :--- | :--- |
| **输出方式** | 一次性快照（拍照） | 实时持续刷新（录像） |
| **适用场景** | 脚本自动化、日志记录、精确筛选 | 交互式实时监控、观察趋势 |
| **自定义程度** | 极高（`-o` 可任意组合字段） | 有限 |
| **组合使用** | 可以和 grep/awk/sort 自由组合 | 独立运行，不易与其他工具组合 |
| **资源消耗** | 极低（运行完就退出） | 持续运行，有一定开销 |

> 💡 **经验之谈**：**排查问题用 `ps`，日常盯盘用 `top`**。写监控脚本必须用 `ps`，因为 top 的输出不方便被其他命令解析。

---

## 十、实战进阶：写一个进程健康巡检脚本

学以致用，下面这个脚本综合运用了本文讲到的各种 `ps` 技巧，可以直接部署到生产环境做巡检：

```bash
#!/bin/bash
# 进程健康巡检脚本 —— 基于 ps 命令
# 用法：chmod +x check_process.sh && ./check_process.sh

echo "=========================================="
echo "  Linux 进程健康巡检报告"
echo "  巡检时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "=========================================="

echo ""
echo "【1】进程总数统计"
echo "-------------------------------------------"
total=$(ps -e --no-headers | wc -l)
echo "当前系统进程总数：$total"

echo ""
echo "【2】各状态进程统计"
echo "-------------------------------------------"
ps -eo stat --no-headers | cut -c1 | sort | uniq -c | sort -rn | \
while read count state; do
    case $state in
        R) desc="运行中(Running)" ;;
        S) desc="可中断睡眠(Sleeping)" ;;
        D) desc="不可中断睡眠(Disk Sleep)" ;;
        T) desc="已停止(Stopped)" ;;
        Z) desc="僵尸进程(Zombie)" ;;
        I) desc="空闲内核线程(Idle)" ;;
        *) desc="其他($state)" ;;
    esac
    printf "  %-30s %d 个\n" "$desc" "$count"
done

echo ""
echo "【3】CPU 占用 TOP 10"
echo "-------------------------------------------"
ps -eo pid,user,%cpu,%mem,comm --sort=-%cpu --no-headers | head -n 10 | \
awk '{printf "  PID:%-8s 用户:%-10s CPU:%-6s 内存:%-6s 命令:%s\n", $1, $2, $3"%", $4"%", $5}'

echo ""
echo "【4】内存占用 TOP 10"
echo "-------------------------------------------"
ps -eo pid,user,rss,%mem,comm --sort=-rss --no-headers | head -n 10 | \
awk '{printf "  PID:%-8s 用户:%-10s RSS:%-8s 内存:%-6s 命令:%s\n", $1, $2, int($3/1024)"MB", $4"%", $5}'

echo ""
echo "【5】僵尸进程检查"
echo "-------------------------------------------"
zombie_count=$(ps -eo stat --no-headers | grep -c "^Z")
if [ "$zombie_count" -gt 0 ]; then
    echo "  ⚠️  发现 $zombie_count 个僵尸进程！详情如下："
    ps -eo pid,ppid,stat,user,comm --no-headers | awk '$3 ~ /^Z/ {printf "    PID:%-8s 父PID:%-8s 用户:%-10s 命令:%s\n", $1, $2, $4, $5}'
else
    echo "  ✅ 未发现僵尸进程"
fi

echo ""
echo "【6】D 状态进程检查（不可中断 I/O 等待）"
echo "-------------------------------------------"
d_count=$(ps -eo stat --no-headers | grep -c "^D")
if [ "$d_count" -gt 0 ]; then
    echo "  ⚠️  发现 $d_count 个 D 状态进程（可能存在 I/O 瓶颈）："
    ps -eo pid,user,stat,wchan,comm --no-headers | awk '$3 ~ /^D/ {printf "    PID:%-8s 用户:%-10s 等待函数:%-20s 命令:%s\n", $1, $2, $4, $5}'
else
    echo "  ✅ 未发现 D 状态进程"
fi

echo ""
echo "【7】运行超过 7 天的进程"
echo "-------------------------------------------"
ps -eo pid,user,etimes,etime,comm --no-headers | \
awk '$3 > 604800 {printf "  PID:%-8s 用户:%-10s 运行时长:%-15s 命令:%s\n", $1, $2, $4, $5}' | head -n 10

echo ""
echo "【8】每用户进程数量排行"
echo "-------------------------------------------"
ps -eo user --no-headers | sort | uniq -c | sort -rn | head -n 10 | \
awk '{printf "  %-15s %d 个进程\n", $2, $1}'

echo ""
echo "=========================================="
echo "  巡检完成"
echo "=========================================="
```

---

## 十一、常见问题 FAQ

### Q1：ps aux 和 ps -ef 到底用哪个？

| | `ps aux` | `ps -ef` |
| :--- | :--- | :--- |
| 风格 | BSD | UNIX |
| CPU/内存占比 | ✅ 有 `%CPU`、`%MEM` | ❌ 没有 |
| 父进程 PPID | ❌ 没有 | ✅ 有 |
| 推荐场景 | 排查资源占用 | 排查进程关系 |

**结论**：查资源用 `ps aux`，查关系用 `ps -ef`，两个都要会。

### Q2：为什么 ps 显示的 %CPU 超过 100%？

这是多线程进程在多核 CPU 上的正常现象。比如一个 4 线程的 Java 程序，每个线程跑满一个核心，%CPU 就是 400%。

### Q3：如何杀掉一个进程？

```bash
# 优雅终止（发送 SIGTERM，让程序自己清理后退出）
kill PID

# 强制杀掉（发送 SIGKILL，立即终止，不给程序清理的机会）
kill -9 PID

# 按名称杀进程
pkill nginx
killall nginx
```

### Q4：ps 的输出能实时刷新吗？

`ps` 本身是快照命令，不支持实时刷新。但可以用 `watch` 包装：

```bash
watch -n 1 'ps -eo pid,%cpu,%mem,comm --sort=-%cpu | head -20'
```

如果需要真正的实时监控，建议使用 `top`、`htop` 或 `atop`。

### Q5：RSS 和 VSZ 看哪个才能反映真实内存使用？

**看 RSS**。VSZ 包含了大量还没有被加载到物理内存的部分（如共享库的未使用部分），会虚高。RSS 才是进程真正占用的物理内存。

### Q6：怎么找到占用某个端口的进程？

这其实不是 `ps` 的活儿，用 `ss` 或 `lsof` 更直接：

```bash
# 推荐方法
ss -tlnp | grep :8080

# 或者
lsof -i :8080
```

---

## 十二、一图速查：ps 命令参数速查表

| 需求 | 命令 |
| :--- | :--- |
| 查看所有进程 | `ps aux` 或 `ps -ef` |
| 按 CPU 排序 | `ps aux --sort=-%cpu` |
| 按内存排序 | `ps aux --sort=-rss` |
| 查看进程树 | `ps -ef --forest` |
| 查看某用户的进程 | `ps -u username` |
| 按进程名查找 | `ps -C nginx` |
| 按 PID 查看 | `ps -p 1234` |
| 查看线程 | `ps -Lp PID` |
| 自定义输出列 | `ps -eo pid,user,%cpu,%mem,cmd` |
| 查看进程启动时间 | `ps -eo pid,lstart,etime,cmd` |
| 找僵尸进程 | `ps aux | awk '$8=="Z"'` |
| 查看进程的父进程 | `ps -o pid,ppid,cmd -p PID` |
| 不显示表头 | `ps --no-headers -eo pid,cmd` |
| 完全不截断命令 | `ps auxww` |

---

**至此，你已经掌握了 `ps` 命令的完整知识体系。** 从基础的 `ps aux` 到自定义输出、排序、线程分析、进程树、信号排查，再到实战巡检脚本——你已经具备了 Linux 进程管理高手的全部技能。

最后的建议：**别光看，一定要在自己的 Linux 机器上把每条命令都敲一遍**。命令行工具的肌肉记忆，只有打出来才能真正记住。
