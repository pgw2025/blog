---
title: "Linux 常用命令汇总（新手必备）"  # 文章标题
date: 2026-04-21T17:00:00+08:00        # 发布时间
draft: false                             # 设为 false 才会发布
tags: ["Linux", "运维", "命令行"]        # 标签（科技博客分类用）
categories: ["技术教程"]                 # 分类
series: ["Linux 学习系列"]               # 系列文章（FixIt 推荐，DoIt 也支持）
---
# Linux 常用命令用法汇总（新手必备）

在 Linux 学习和使用过程中，掌握常用命令是提升效率的核心。本文整理了日常开发、运维中高频使用的 Linux 命令，涵盖文件操作、权限管理、进程控制、系统查看等场景，结合具体示例说明，新手也能快速上手。所有命令均经过实际测试，适配 Rocky Linux、CentOS、Ubuntu 等主流发行版。

本文使用 **LoveIt 主题** 排版，支持代码高亮、提示框、目录导航，阅读体验更佳。文章末尾附命令速查表，方便快速检索。

## 一、基础文件操作命令（最常用）

文件操作是 Linux 最基础的操作，以下命令覆盖创建、删除、查看、复制、移动等核心场景，必记！

### 1\. ls \- 列出目录内容

功能：列出当前目录或指定目录下的文件和文件夹，常用参数可快速筛选内容。

```bash
# 基础用法：列出当前目录内容
ls

# 常用参数（组合使用）
ls -l  # 详细列表形式（显示权限、大小、修改时间等）
ls -a  # 显示隐藏文件（以 . 开头的文件）
ls -h  # 大小以人性化单位显示（KB、MB、GB）
ls -lh # 组合参数，详细列表+人性化大小（最常用）
ls /opt # 列出指定目录 /opt 下的内容
```

提示：ls \-lh 是日常最常用的组合，能清晰看到文件的权限、所有者、大小和修改时间，排查文件问题时首选。

### 2\. cd \- 切换工作目录

功能：切换到指定目录，是所有操作的基础前提。

```bash
# 切换到指定绝对路径（推荐，不易出错）
cd /home/user

# 切换到相对路径（相对于当前目录）
cd ../  # 切换到上一级目录（最常用）
cd ./docs # 切换到当前目录下的 docs 文件夹

# 快速切换到用户主目录
cd ~  # 等价于 cd /home/当前用户
cd    # 不跟参数，默认切换到主目录
```

### 3\. touch \- 创建空文件

功能：创建一个或多个空文件，也可用于修改文件的修改时间。

```bash
# 创建单个空文件
touch test.txt

# 创建多个空文件
touch file1.txt file2.txt file3.txt

# 修改文件修改时间（不改变文件内容）
touch -m test.txt
```

### 4\. mkdir \- 创建目录

功能：创建单个或多级目录，常用参数 \-p 可递归创建多级目录。

```bash
# 创建单个目录
mkdir docs

# 递归创建多级目录（最常用，避免手动创建父目录）
mkdir -p /home/user/blog/docs

# 创建多个目录
mkdir dir1 dir2 dir3
```

### 5\. rm \- 删除文件/目录

功能：删除文件或目录，**注意：rm 命令删除后无法恢复，慎用！**

```bash
# 删除单个文件（需确认）
rm test.txt

# 强制删除文件（不提示，慎用）
rm -f test.txt

# 删除空目录
rm -d docs

# 强制删除目录及所有内容（最常用，递归删除）
rm -rf /home/user/tmp  # 注意路径，避免误删系统文件
```

警告：rm \-rf / 是极其危险的命令，会删除系统所有文件，导致系统崩溃，绝对禁止执行！

### 6\. cp \- 复制文件/目录

功能：复制文件或目录到指定位置，常用参数 \-r 用于复制目录。

```bash
# 复制文件到指定目录
cp test.txt /home/user/docs

# 复制文件并改名
cp test.txt /home/user/docs/new_test.txt

# 复制目录及所有内容（递归复制，最常用）
cp -r /home/user/docs /home/user/backup

# 复制时保留文件属性（权限、修改时间等）
cp -a /home/user/docs /home/user/backup
```

### 7\. mv \- 移动/重命名文件/目录

功能：移动文件/目录到指定位置，也可用于重命名文件/目录。

```bash
# 重命名文件（同一目录下）
mv test.txt new_test.txt

# 移动文件到指定目录
mv new_test.txt /home/user/docs

# 移动目录到指定目录
mv /home/user/docs /home/user/backup

# 强制移动（覆盖同名文件，不提示）
mv -f test.txt /home/user/docs
```

### 8\. cat \- 查看文件内容

功能：查看文件内容，适合查看小型文件（大型文件推荐用 less/more）。

```bash
# 查看文件全部内容
cat test.txt

# 查看多个文件内容，合并显示
cat file1.txt file2.txt

# 显示行号
cat -n test.txt

# 将内容追加到文件（不会覆盖原有内容）
cat test.txt >> new_file.txt

# 清空文件内容（快速清空，慎用）
cat /dev/null > test.txt
```

## 二、权限管理命令（重要）

Linux 是多用户系统，权限管理至关重要，以下命令用于设置文件/目录的访问权限，避免误操作或权限泄露。

### 1\. chmod \- 修改文件/目录权限

功能：修改文件/目录的读（r）、写（w）、执行（x）权限，有数字法和符号法两种用法，数字法更简洁常用。

权限数字对应：r=4，w=2，x=1；权限对象：所有者（u）、组用户（g）、其他用户（o）、所有用户（a）。

```bash
# 数字法（最常用）：所有者读写执行，组用户读执行，其他用户读
chmod 755 test.sh

# 所有者读写，组用户读，其他用户读（文件常用）
chmod 644 test.txt

# 所有者读写执行，组用户读写执行，其他用户读写执行（慎用）
chmod 777 test.txt

# 符号法：给所有者增加执行权限
chmod u+x test.sh

# 给所有用户增加读权限
chmod a+r test.txt

# 递归修改目录及所有内容的权限（常用）
chmod -R 755 /home/user/docs
```

### 2\. chown \- 修改文件/目录所有者

功能：修改文件/目录的所有者和所属组，常用于权限异常时修复。

```bash
# 修改所有者为 user
chown user test.txt

# 修改所有者和所属组为 user:user
chown user:user test.txt

# 递归修改目录及所有内容的所有者（常用）
chown -R user:user /home/user/docs
```

## 三、系统查看与管理命令

用于查看系统状态、进程、内存、磁盘等信息，排查系统问题时常用。

### 1\. top \- 查看系统进程与资源占用

功能：实时查看系统 CPU、内存、进程的占用情况，按 q 退出。

```bash
# 基础用法，实时监控
top

# 常用操作（top 界面内）
P：按 CPU 占用率排序（默认）
M：按内存占用率排序
k：终止指定进程（输入进程ID）
q：退出 top 界面
```

### 2\. free \- 查看内存使用情况

功能：查看系统总内存、已用内存、空闲内存等信息，常用参数 \-h 人性化显示。

```bash
# 人性化显示内存信息（最常用）
free -h

# 显示详细内存信息
free -m  # 以 MB 为单位显示
```

### 3\. df \- 查看磁盘空间使用情况

功能：查看各磁盘分区的空间占用、剩余空间等信息，排查磁盘满的问题。

```bash
# 人性化显示磁盘信息（最常用）
df -h

# 查看指定目录所在分区的空间使用
df -h /home
```

### 4\. ps \- 查看进程信息

功能：查看系统当前运行的进程，常用参数组合 aux 或 ef。

```bash
# 查看所有进程（最常用，显示详细信息）
ps aux

# 查看指定进程（根据进程名筛选，如 mysql）
ps aux | grep mysql

# 查看进程树（显示进程间的父子关系）
ps -ef | grep -v grep | grep mysql
```

### 5\. kill \- 终止进程

功能：终止指定进程，常用参数 \-9 强制终止（无法恢复）。

```bash
# 先查看进程 ID（PID）
ps aux | grep mysql

# 终止进程（PID 为 1234，温柔终止，允许进程清理资源）
kill 1234

# 强制终止进程（最常用，无法恢复，用于进程卡死）
kill -9 1234

# 终止所有指定名称的进程（如 mysql）
kill -9 $(ps aux | grep mysql | grep -v grep | awk '{print $2}')
```

### 6\. uname \- 查看系统信息

功能：查看系统内核版本、操作系统类型等信息。

```bash
# 查看系统所有信息（最常用）
uname -a

# 查看内核版本
uname -r

# 查看操作系统类型
uname -s
```

## 四、其他高频命令

以下命令在日常使用中出现频率极高，补充说明，方便快速调用。

### 1\. ping \- 测试网络连通性

功能：测试与目标主机的网络连通性，常用于排查网络问题。

```bash
# 测试与百度的连通性
ping baidu.com

# 限制发送包的数量（避免一直 ping）
ping -c 4 baidu.com
```

### 2\. wget \- 下载文件

功能：从网络上下载文件，无需图形界面，适合服务器使用。

```bash
# 下载文件到当前目录
wget https://example.com/test.zip

# 下载文件并指定保存名称
wget -O new_test.zip https://example.com/test.zip

# 后台下载（断开连接后仍继续下载）
wget -b https://example.com/test.zip
```

### 3\. curl \- 发送 HTTP 请求/下载文件

功能：比 wget 更灵活，可发送 GET/POST 请求，也可用于下载文件。

```bash
# 查看网页内容（GET 请求）
curl https://baidu.com

# 下载文件
curl -O https://example.com/test.zip

# 发送 POST 请求（带参数）
curl -X POST -d "name=test" https://example.com/api
```

### 4\. history \- 查看命令历史

功能：查看之前执行过的命令，可快速复用。

```bash
# 查看所有命令历史
history

# 查看最近 10 条命令历史
history 10

# 执行历史中的第 123 条命令
!123

# 搜索包含 mysql 的命令历史
history | grep mysql
```

### 5\. clear \- 清空终端

```bash
# 清空终端屏幕（最常用）
clear

# 快捷键：Ctrl + L（效果与 clear 一致）
```

## 五、常用命令速查表（快速检索）

|命令|常用用法|功能说明|
|---|---|---|
|ls|ls \-lh|列出目录内容（详细\+人性化）|
|cd|cd \.\./、cd \~|切换工作目录|
|rm|rm \-rf 目录|强制删除目录及内容|
|cp|cp \-r 源目录 目标目录|递归复制目录|
|mv|mv 旧名 新名|重命名文件/目录|
|chmod|chmod 755 文件|修改文件权限|
|top|top|实时监控系统资源|
|free|free \-h|查看内存使用|
|ps|ps aux \| grep 进程名|查看指定进程|
|kill|kill \-9 进程ID|强制终止进程|

## 六、总结

以上命令是 Linux 日常使用中最核心、最高频的，新手建议先掌握基础文件操作和系统查看命令，再逐步熟悉权限管理和进程控制。实际使用中，可通过 `命令 \-\-help` 查看更多参数用法（如 `ls \-\-help`），也可结合 history 命令快速复用之前执行过的命令。

后续会持续更新 Linux 进阶命令（如 Shell 脚本、服务管理等），欢迎关注收藏～

提示：本文所有命令均在 Rocky Linux 9 中测试通过，其他发行版（如 Ubuntu）部分命令参数可能略有差异，可根据实际系统调整。

> （注：文档部分内容可能由 AI 生成）
