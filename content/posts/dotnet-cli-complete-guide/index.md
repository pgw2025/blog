---
title: ".NET CLI 全攻略：从入门到精通，让你的开发效率翻倍"
date: 2026-06-03T10:00:00+08:00
draft: false
tags: [".NET", "CLI", "Dotnet", "编程工具"]
categories: ["后端开发", ".NET"]
author: "Will"
summary: "还在为记不住 .NET 复杂的命令行参数发愁吗？本文用最通俗易懂的语言，为你详细拆解 dotnet 命令的常用参数和实战技巧，让你像大神一样玩转终端开发。"
---

# .NET CLI 全攻略：让你的开发效率翻倍

对于 .NET 开发者来说，虽然 Visual Studio 的图形界面很强大，但 **.NET CLI（命令行界面）** 才是真正的“效率神器”。无论是自动化部署、快速创建项目，还是在 Linux 服务器上排查问题，CLI 都是不可或缺的。

今天，我们就用最通俗的语言，把 `dotnet` 命令及其常用参数彻底讲清楚！

---

## 1. 基础入门：这是什么？

简单来说，`dotnet` 命令就像是你的“全能管家”。你只需要在终端（Terminal 或 PowerShell）里对他下令，他就能帮你完成从新建项目到发布上线的所有工作。

**通用语法结构：**
```bash
dotnet [command] [arguments] [options]
```
*   **Command**: 你想让管家做什么（比如 `new` 是新建，`build` 是编译）。
*   **Arguments**: 命令的操作对象（比如项目名称）。
*   **Options**: 具体的额外要求（比如 `-o` 指定输出目录）。

---

## 2. 核心命令详解

### 🚀 dotnet new —— “管家，帮我建个新项目”
这是你开始一段新代码旅程的第一步。

*   **常用用法：**
    *   `dotnet new console`: 创建一个控制台程序。
    *   `dotnet new webapi`: 创建一个 Web API 项目。
    *   `dotnet new mvc`: 创建一个经典的 MVC 项目。
*   **常用参数：**
    *   `-n, --name`: 给你的项目起个名字。例：`dotnet new webapi -n MyAwesomeApi`
    *   `-o, --output`: 指定项目放在哪个文件夹。例：`dotnet new console -o ./src/MyProject`
    *   `-f, --framework`: 指定 .NET 版本。例：`dotnet new console -f net8.0`

### 🏗️ dotnet build —— “检查一下代码有没有写错”
写完代码，总得编译一下看看能不能跑通。

*   **常用参数：**
    *   `-c, --configuration`: 编译模式。常用 `Debug`（调试）或 `Release`（正式发布）。
        *   例：`dotnet build -c Release`
    *   `--no-restore`: 跳过“还原依赖”步骤（如果你已经还原过了，加这个能快一点）。

### ▶️ dotnet run —— “跑起来给我看看”
直接运行你的项目。它会自动包含 `build` 的过程。

*   **常用参数：**
    *   `--project`: 指定要运行的项目文件（如果有多个项目）。
    *   `-- <args>`: 传递给程序本身的参数。
        *   例：`dotnet run -- MyParameter1`（这里的参数会被你的 `Main` 函数接收）。

### 📦 dotnet publish —— “打包发货！”
当你准备把项目部署到服务器（比如 Linux 或 Docker）时，用这个。

*   **常用参数：**
    *   `-r, --runtime`: 指定目标平台（比如 `linux-x64`, `win-x64`）。
    *   `-p:PublishSingleFile=true`: 打包成一个独立的执行文件，不再有一堆 DLL。
    *   `--self-contained`: 把运行时也打进去，目标服务器不需要装 .NET 也能跑。

---

## 3. 依赖管理：给项目“买零件”

### ➕ dotnet add package —— 添加 NuGet 包
*   **用法：** `dotnet add package Newtonsoft.Json`
*   **参数：** `-v, --version` 指定版本。

### ➕ dotnet add reference —— 项目引用
如果你想让 A 项目引用 B 项目。
*   **用法：** `dotnet add ProjectA.csproj reference ProjectB.csproj`

---

## 4. 进阶技巧：你的秘密武器

### 🛠️ dotnet tool —— 安装全局小工具
.NET 社区有很多好用的命令行工具，比如生成代码的、分析性能的。
*   **用法：** `dotnet tool install -g <ToolName>`

### 🔍 dotnet list —— 查看项目详情
*   `dotnet list package`: 查看你都装了哪些 NuGet 包，有没有版本过旧的。

### 📜 dotnet help —— 哪里不会点哪里
如果你忘了某个命令怎么用，直接在后面加个 `-h` 或 `--help`。
*   例：`dotnet publish -h`

---

## 5. 常见问题 Q&A

**Q: 为什么我的命令报错“找不到 dotnet”？**
A: 请确认你安装了 .NET SDK，并且它的路径已经加入了系统的环境变量（Path）。

**Q: `dotnet restore` 有什么用？**
A: 它负责根据你的配置文件（.csproj）去网上下载所有的依赖包。现代的 `build` 和 `run` 命令会自动执行它，所以一般不需要手动运行。

---

## 总结

.NET CLI 并不冷冰冰，它是你开发路上的得力助手。掌握了这些常用参数，你就能在 Linux 运维、CI/CD 自动化以及日常开发中游刃有余。

**建议收藏这篇短文，下次手生了，翻出来看看参数表即可！**
