---
title: "SignalR 实时通讯全攻略：打破“请求-响应”的传统枷锁"
date: 2026-05-30T18:00:00+08:00
draft: false
tags: ["SignalR", ".NET", "实时通讯", "WebSocket", "前端开发"]
categories: ["全栈技术"]
series: ["现代 Web 通讯系列"]
author: "GW"
summary: "还在用不停的轮询（Polling）来检查新消息吗？SignalR 让服务器能够主动向客户端推数据。本文将带你通俗掌握 SignalR 的工作原理、服务端与客户端的完整实现，以及如何处理断线重连等高级技巧。"
---

# SignalR 实时通讯全攻略：打破“请求-响应”的传统枷锁

在传统的 Web 开发中，浏览器总是“主动”的一方：它发一个请求，服务器回一个响应。如果服务器有新数据（比如有人给你发了消息），浏览器如果不问，服务器就没法说。

**SignalR** 彻底改变了这种局面。它让服务器拥有了“主动权”，一旦有新动向，服务器能瞬间推送到你的屏幕上。

---

## 一、 原理：它不是一种协议，而是一个“指挥官”

很多人误以为 SignalR 就是 WebSocket。其实，SignalR 是一个**高级库**，它在底层指挥着三种协议：

1. **WebSockets** (最快)：双向透明通道，像打长途电话，双方随时能说话。
2. **Server-Sent Events (SSE)**：服务器单向推，像听广播。
3. **长轮询 (Long Polling)** (保底)：如果上面两个都不行，浏览器就发个请求死等，服务器有消息了才回。

**SignalR 最聪明的地方在于**：它会自动探测浏览器和服务器支持什么，优先选最快的。

---

## 二、 核心概念：Hub（中心）

你可以把 **Hub** 想象成一个“聊天室管理员”。所有的客户端都连到这个 Hub 上，Hub 负责：
- 接收客户端发来的消息。
- 把消息转发给特定的人、特定的群组，或者所有人。

---

## 三、 服务端实现 (.NET 示例)

### 1. 定义 Hub 类
创建一个 `ChatHub.cs`：
```csharp
using Microsoft.AspNetCore.SignalR;

public class ChatHub : Hub
{
    // 客户端调用此方法发送消息
    public async Task SendMessage(string user, string message)
    {
        // 广播给所有连线的客户端，触发他们本地的 "ReceiveMessage" 函数
        await Clients.All.SendAsync("ReceiveMessage", user, message);
    }
}
```

### 2. 注册服务 (Program.cs)
```csharp
var builder = WebApplication.CreateBuilder(args);

builder.Services.AddSignalR(); // 1. 添加 SignalR 服务

var app = builder.Build();

app.MapHub<ChatHub>("/chathub"); // 2. 映射访问路径
```

---

## 四、 客户端实现 (JavaScript/Vue 示例)

### 1. 安装库
```bash
npm install @microsoft/signalr
```

### 2. 建立连接并监听
```javascript
import * as SingnelR from '@microsoft/signalr';
import { onMounted, onUnmounted, ref } from 'vue';
// 定义一个函数useSingnelR，接受一个参数hubUrl，表示SignalR连接的URL
// 返回一个对象，包含connection和sendMessage方法
// connection是SignalR连接实例，sendMessage是发送消息到服务器的方法
// 在组件挂载时初始化SignalR连接，在组件卸载时停止连接
// 使用onMounted和onUnmounted生命周期钩子来管理SignalR连接的生命周期
export function useSingnelR(hubUrl: string) {
    // 创建一个ref来存储SignalR连接实例
    const connection = ref<SingnelR.HubConnection | null>(null);
    // 创建一个ref来存储接收到的消息数据数组
    const receivedData = ref<string | "">("");

    // 初始化SignalR连接的方法
    const initSignalR = async () => {
        // 创建SignalR连接
        connection.value = new SingnelR.HubConnectionBuilder()
            .withUrl(hubUrl, {
                // 跳过协商直接使用WebSocket
                skipNegotiation: true,
                transport: SingnelR.HttpTransportType.WebSockets
            })
            .withAutomaticReconnect()
            .build();
        // 连接成功后，监听消息事件
        //第一个参数'ReceiveMessage'是服务器端发送的消息放的的第一个参数名，data是接收到的消息数据
        connection.value.on('ReceiveMessage', (data) => {
            // 将接收到的消息数据存储到receivedData中
            // 并在控制台中输出接收到的消息数据
            receivedData.value = data;
            console.log('Received message:', data);
        });

        // 启动连接
        try {
            await connection.value.start();
            console.log('Connection Server:' + hubUrl + ' connected successfully');
        } catch (error) {
            console.error('Error starting connection:', error);

        }


    }
    // 在组件挂载时初始化SignalR连接，在组件卸载时停止连接
    // 使用onMounted和onUnmounted生命周期钩子来管理SignalR连接的生命周期
    onMounted(() => {
        console.log("已经挂载开始初始化SignalR...");

        initSignalR();
    });
    // 在组件卸载时停止SignalR连接，避免内存泄漏
    // 使用onUnmounted生命周期钩子来管理SignalR连接的生命周期
    onUnmounted(() => {
        console.log("已经卸载停止SignalR...");
        if (connection.value) {
            connection.value.stop();
            console.log('SignalR Connection stopped');
        }
    });
    // 提供一个方法来发送消息到服务器
    // 使用connection.value.invoke方法来调用服务器端的方法
    // 参数methodName是服务器端方法的名称，...args是服务器端方法的参数数组
    const sendMessage = async (methodName: string, ...args: any[]) => {
        if (connection.value) {
            await connection.value.invoke(methodName, ...args);
        }
    }

    // 返回一个对象，包含connection和sendMessage方法
    // 这样可以在组件中使用这些方法和属性
    return {
        receivedData,
        sendMessage
    };

}
```

### 3. 在组件中使用
```vue
<script setup lang="ts">
//引用SingnelR
import { useSingnelR } from '@/api/SingnelR'
import { ref } from 'vue';
//定义SingnelR的接收和发送方法
const { receivedData, sendMessage } = useSingnelR("http://localhost:5250/chat")
const message = ref('')

</script>

<template>
  <div>
    <h1>SingnelR Demo</h1>
    <input type="text" v-model="message" placeholder="Type a message" />
    <!-- 发送消息按钮  -->
    <button @click="sendMessage('SendMessage', message)">Send</button>
    <div v-if="receivedData">
      <h2>Received Data:</h2>
      <pre>{{ receivedData }}</pre>
    </div>
  </div>
</template>

<style scoped></style>
```

## 五、 使用技巧与高级玩法

### 1. 分组管理 (Groups) —— “只发给特定人群”
在 Hub 中，你可以把连接分配到不同的组（如：VIP组、101房间）。
```csharp
// 加入组
await Groups.AddToGroupAsync(Context.ConnectionId, "Room101");
// 只发给 Room101 组的人
await Clients.Group("Room101").SendAsync("ReceiveMessage", "系统", "欢迎加入房间");
```

### 2. 身份验证 —— “知道谁是谁”
你可以结合 JWT Token。在连接时，SignalR 会自动处理上下文中的 `Context.User`，让你能直接调用 `Clients.User(userId).SendAsync(...)` 发私信。

### 3. 自动重连逻辑
在创建连接时加上 `.withAutomaticReconnect()`，当用户进入电梯断网又出来后，SignalR 会自动尝试恢复连接，不需要你写复杂的重连代码。

---

## 六、 总结：什么时候该用它？

- **实时仪表盘**：工业现场的压力、转速实时显示。
- **即时通讯**：聊天室、通知中心。
- **协同编辑**：多个人同时改一个文档。
- **游戏**：多人在线对战。

SignalR 的出现，让实时 Web 开发变得异常简单。它屏蔽了底层复杂的协议切换，让你只需关注业务逻辑。

> （注：本文由 GW 整理。打破延迟，让你的数据快如闪电！）
