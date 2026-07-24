---
title: "第二十四章：SCL 处理工业通讯数据与大厂级多协议报文解析器"
date: 2026-07-24T12:53:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们手写了一套高度安全的食品配方管理系统，体验了 UDT 与三温区隔离的工程魅力。"
---


在上一章中，我们手写了一套高度安全的食品配方管理系统，体验了 UDT 与三温区隔离的工程魅力。

今天，我们要去攻克现代化智能工厂数字化网络建设中的生命线——**工业通讯数据解析（Industrial Communication Parsing）**。

在当今工业 4.0 时代，PLC 绝不是孤立运行的。你的控制器必须化身为“沟通大师”，高频地与各类第三方设备交互：
*   通过 **Modbus RTU/TCP** 读取温度仪表、智能电量仪表的寄存器数据。
*   通过 **PROFINET 非周期数据块（RDREC / WRREC）** 动态读取变频器、伺服驱动器的非周期能耗诊断数据或参数。
*   通过 **原生态以太网 TCP/IP 套接字（Socket）** 直接读取扫码枪、AGV 小车、激光测距仪发回的自由口自定义 ASCII / 二进制流式报文。

然而，通讯解析是现场调试中最容易翻车的地方。**西门子 CPU 底层是标准的 大端模式（Big-Endian），而 80% 的第三方设备采用的是 小端模式（Little-Endian）甚至奇特的高低字节对调（Byte Swap）。**

如果你尝试用传统的 梯形图（LAD）去写高低字节对调、CRC16 校验码计算、以及流式 TCP 粘包拆包解析，程序会极其臃肿。

今天，师父带你理清“大端与小端的二进制战役”，剖析 PROFINET 异步非周期数据访问的 CASE 状态机机理，并手写一个生产级的**“万能多协议通讯报文解析与 CRC16 高速自检系统（SCL）”**。

---

## 1. 大端与小端的二进制战役：S7 字节序的物理真相

在计算机和 PLC 物理芯片中，对于一个占用多个字节的数据（如 32 位的 REAL 或 DINT），在物理内存里的排列顺序存在两大学派：

```
                    32位浮点数 16#41480000 (12.5) 的物理存储对比
                    
 1. 大端模式 (Big-Endian) - 西门子 S7-1200/1500 原生物理结构 (高位字节存放在低地址)
    物理内存地址:     Byte 0      Byte 1      Byte 2      Byte 3
    数据内容(Hex):  [  16#41  ]  [  16#48  ]  [  16#00  ]  [  16#00  ]
    
 2. 小端模式 (Little-Endian) - 绝大多数英特尔芯片、Modbus 仪表默认 (低位字节存放在低地址)
    物理内存地址:     Byte 0      Byte 1      Byte 2      Byte 3
    数据内容(Hex):  [  16#00  ]  [  16#00  ]  [  16#48  ]  [  16#41  ]
    
 3. 字节对调模式 (Byte-Swapped / CDAB) - 部分 Modbus RTU 仪表的特色混排
    物理内存地址:     Byte 0      Byte 1      Byte 2      Byte 3
    数据内容(Hex):  [  16#00  ]  [  16#00  ]  [  16#41  ]  [  16#48  ]
```

### 1.1 SCL 底层对调武器
如果我们在 Modbus 通信中读到了一个 `12.5` 浮点数，读到西门子 PLC 里变成了一堆不可读的乱码，这说明字节序对调了。

在 SCL 中，我们不需要繁琐地去用逻辑位移，西门子为我们配备了高效的底层汇编级转换指令：
*   **`SWAP(<变量>)`**：对输入变量进行高低字节对调。
*   **`ROR` / `ROL`**：循环移位，可用于更复杂的 4 字节混排处理。
*   **Slice 访问（`.B0`、`.B1`）**：对一个字直接进行底层字节级别的重组：
    ```scl
    #wDest.B0 := #wSource.B1; // 底层瞬间交换，零算力开销！
    #wDest.B1 := #wSource.B0;
    ```

---

## 2. Modbus 数据处理与 CRC16 高速算法

Modbus 寄存器是标准的 **`WORD`（16位）**。当读取 32 位数据（如 DINT 脉冲计数）时，它占用了 2 个寄存器（如 `Reg[0]` 和 `Reg[1]`）。

在 SCL 中，拼接并对齐这两个寄存器的数据极其优雅：

```scl
// 将 2 个 Word 寄存器拼装为一个 32 位 DWord，并处理高低字对调（CDAB 格式）
#dwTemp := SHL(IN := WORD_TO_DWORD(#arrRegs[1]), N := 16) OR WORD_TO_DWORD(#arrRegs[0]);
#rActualValue := DWORD_TO_REAL(#dwTemp); // 强转输出
```

### 2.1 ⚠️ 工业级核心算法：CRC16 校验码 SCL 计算器
在非标 Modbus RTU 串口自由口通信中，你必须在报文末尾附加 2 个字节的 **CRC16（循环冗余校验）**。
如果用梯形图写这个查表和位移循环，会画满好几页。而在 SCL 中，我们可以用一个精炼的 `FOR` 循环完美闭环：

```scl
// 工业级标准 CRC16（多项式 16#A001）计算算法
#wCRC := 16#FFFF; // 初始化寄存器为全 1
FOR #i := 0 TO #iBufferLen - 1 DO
    #wCRC := #wCRC XOR BYTE_TO_WORD(#arrBuffer[#i]); // 字节与 CRC 低位异或
    
    FOR #j := 1 TO 8 DO // 循环 8 次判定每一个 Bit
        IF (#wCRC AND 16#0001) <> 0 THEN
            #wCRC := SHR(IN := #wCRC, N := 1) XOR 16#A001; // 右移并与多项式 16#A001 异或
        ELSE
            #wCRC := SHR(IN := #wCRC, N := 1); // 仅右移
        END_IF;
    END_FOR;
END_FOR;
// 最终得到的 #wCRC 就是完美的 2 字节校验码
```

---

## 3. PROFINET 非周期数据访问：RDREC & WRREC 的状态机调度

PROFINET 除了进行毫秒级的循环 I/O 通信外，还支持 **非周期通信（Acyclic Communication）**。
例如：你需要动态读取一个能耗仪表中的“历史累计电能数据块”，或者修改变频器的内部非周期配置参数。

这需要调用系统专用功能块（SFB）：
*   **`RDREC` (Read Record / SFB52)**：读取非周期数据记录。
*   **`WRREC` (Write Record / SFB53)**：写入非周期数据记录。

### 3.1 异步状态机调度机制
由于非周期访问需要跨越 PROFINET 网络，耗时较长，所以 `RDREC` / `WRREC` 属于 **异步非同步函数（Asynchronous Function）**。
你绝对不能在一个周期内干等着它执行完，你必须使用 **SCL 的 CASE 状态机**，多周期守候它的状态：

```scl
// 异步状态机伪代码模型
CASE #iStep OF
    0:  // 启动读请求
        #rdrecInstance(REQ := TRUE, ...);
        #iStep := 10;
        
    10: // 守候响应
        #rdrecInstance(REQ := FALSE, ...); // 复位 REQ 
        
        IF #rdrecInstance.BUSY THEN
            ; // 网络正忙，继续在当前状态等待
        ELSIF #rdrecInstance.DONE THEN
            #iStep := 20; // 成功拿到数据，跳转至解析状态
        ELSIF #rdrecInstance.ERROR THEN
            #iStep := 90; // 通信报错
        END_IF;
END_CASE;
```

---

## 4. 原生态 TCP/IP 自由口流式解析（粘包与拆包）

TCP/IP（如通过 `TRCV` 接收）是一种 **面向字节流的协议（Stream-Oriented）**。
它在物理底层不保证数据包的边界：
*   **粘包**：扫码枪连扫两次，发回来的数据粘连在一起。
*   **拆包**：一次完整的报文被网卡拆成了两次发送到 PLC。

### 4.1 工业自由口解析黄金法则（帧头帧尾拦截法）
我们必须在 SCL 中对接收缓冲字节数组（Array of Byte）进行“动态滑动窗口扫描”：
1.  寻找帧头（例如 `16#AA`，`16#55`）。
2.  确认帧头后，提取长度字节（判定报文是否接收完整）。
3.  提取核心 Body 载荷。
4.  校验帧尾（例如 `16#0D`，`16#0A`）及 Checksum。

---

## 5. 统一通讯报文解析与校验功能块 (FB_CommBufferParser)

现在，我们把本章讲的大端小端转换、Slice 字节对调、CRC16 校验码计算、以及 TCP 缓冲区动态扫描全部融合成一个高强度的功能块 —— **`FB_CommBufferParser`**。

### 5.1 工业报文格式定义
假设我们通过原生 TCP（TRCV_C）从一个非标的智能温度遥测网关接收到了一个 **64 字节的原始数据帧**。
**报文二进制规约如下**：
*   **Byte 0 & 1**：帧头固定为 `16#AA` 与 `16#55`。
*   **Byte 2**：命令类型（`16#01` 代表传感器数据帧）。
*   **Byte 3 - 4**：传感器 1 的温度整型值（Int，大端格式，单位 0.1°C）。
*   **Byte 5 - 8**：传感器 2 的压力浮点数值（Real，**小端混排字节对调格式 CDAB**）。
*   **Byte 9 - 10**：前 9 字节的 CRC16 校验码。
*   **安全要求**：必须在 SCL 内部动态计算前 9 字节的真实 CRC16，并与 Byte 9 & 10 接收到的校验码进行对齐比对。只有校验通过，才允许解析输出，否则报警并拒绝数据更新。

---

### 5.2 步骤一：块接口声明（FB_CommBufferParser）

（我们创建 FB 块，局部临时区定义各种过渡中间双字和校验变量）：

```
VAR_INPUT
    bTriggerParse : Bool;       // 触发解析清洗脉冲
    arrRxBuffer : Array[0..63] of Byte; // 64 字节 TCP 物理接收缓冲区
END_VAR

VAR_OUTPUT
    bParseSuccess : Bool;       // 解析与 CRC16 校验通过
    bCheckFault : Bool;         // 校验失败故障（数据受损或帧头错误）
    rSensor1_Temp : Real;       // 解析标定后的传感器 1 温度值 (°C)
    rSensor2_Press : Real;      // 解析标定后的传感器 2 压力值 (bar)
END_VAR

VAR
    // 静态变量
    bTrigger_FP : Bool;         // 边沿锁存
END_VAR

VAR_TEMP
    wCalcCRC : Word;            // 计算出的 CRC16
    wRecvCRC : Word;            // 报文里携带的真实 CRC16
    i : Int;                    // CRC 循环变量 1
    j : Int;                    // CRC 循环变量 2
    
    // 临时拼装变量
    tempWord : Word;
    tempDWord : DWord;
    tempReal : Real;
END_VAR
```

---

### 5.3 步骤二：SCL 代码实现

```scl
FUNCTION_BLOCK "FB_CommBufferParser"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 触发边沿捕捉与安全防御
	// ==========================================
	IF #bTriggerParse AND NOT #bTrigger_FP THEN
	    
	    // 初始化输出，防尘底牌
	    #bParseSuccess := FALSE;
	    #bCheckFault := FALSE;
	    
	    // ------------------------------------------
	    // A. 帧头校验 (Byte 0 必须为 16#AA, Byte 1 必须为 16#55)
	    // ------------------------------------------
	    IF #arrRxBuffer[0] <> 16#AA OR #arrRxBuffer[1] <> 16#55 THEN
	        #bCheckFault := TRUE; // 帧头错误，拒绝解析
	        RETURN;
	    END_IF;
	    
	    // ------------------------------------------
	    // B. 命令类型校验 (Byte 2 必须为 16#01)
	    // ------------------------------------------
	    IF #arrRxBuffer[2] <> 16#01 THEN
	        #bCheckFault := TRUE; // 命令类型不对
	        RETURN;
	    END_IF;
	    
	    // ==========================================
	    // 2. 核心：前 9 字节（Byte 0..8）的 CRC16 校验码计算
	    // ==========================================
	    #wCalcCRC := 16#FFFF; // 校验初始值
	    
	    FOR #i := 0 TO 8 DO
	        #wCalcCRC := #wCalcCRC XOR BYTE_TO_WORD(#arrRxBuffer[#i]);
	        
	        FOR #j := 1 TO 8 DO
	            IF (#wCalcCRC AND 16#0001) <> 0 THEN
	                #wCalcCRC := SHR(IN := #wCalcCRC, N := 1) XOR 16#A001; // 异或多项式 16#A001
	            ELSE
	                #wCalcCRC := SHR(IN := #wCalcCRC, N := 1);
	            END_IF;
	        END_FOR;
	    END_FOR;
	    
	    // ------------------------------------------
	    // C. 提炼报文中自带的 CRC 校验码 (Byte 9 & 10)
	    // 假设仪表的 CRC 也是低字节在前，高字节在后
	    // ------------------------------------------
	    #wRecvCRC.B0 := #arrRxBuffer[9];
	    #wRecvCRC.B1 := #arrRxBuffer[10];
	    
	    // 进行 CRC16 严格比对
	    IF #wCalcCRC <> #wRecvCRC THEN
	        #bCheckFault := TRUE; // 校验失败！说明通信中发生了噪声干扰导致数据受损，拒绝解析
	        RETURN;
	    END_IF;
	    
	    // ==========================================
	    // 3. 校验完全通过！执行高安全性数据解码与重构
	    // ==========================================
	    
	    // ------------------------------------------
	    // A. 解析传感器 1 的温度 (Byte 3 & 4)
	    // 大端格式（西门子原生）：高字节在低地址，直接物理合并
	    // ------------------------------------------
	    #tempWord.B1 := #arrRxBuffer[3]; // 高字节存放在 Byte 3
	    #tempWord.B0 := #arrRxBuffer[4]; // 低字节存放在 Byte 4
	    
	    // 标定还原 (INT 除以 10.0，得到 1 位小数的 Real)
	    #rSensor1_Temp := INT_TO_REAL(WORD_TO_INT(#tempWord)) / 10.0;
	    
	    // ------------------------------------------
	    // B. 解析传感器 2 的压力 (Byte 5 - 8)
	    // 目标小端混排 CDAB 格式，我们在西门子内部重排为 ABCD 格式
	    // 对应关系：
	    // 源 Byte 5 -> D (B0)
	    // 源 Byte 6 -> C (B1)
	    // 源 Byte 7 -> B (B2)
	    // 源 Byte 8 -> A (B3)
	    // ------------------------------------------
	    #tempDWord.B3 := #arrRxBuffer[8]; // A
	    #tempDWord.B2 := #arrRxBuffer[7]; // B
	    #tempDWord.B1 := #arrRxBuffer[6]; // C
	    #tempDWord.B0 := #arrRxBuffer[5]; // D
	    
	    // 一键强制解码转换
	    #rSensor2_Press := DWORD_TO_REAL(#tempDWord);
	    
	    // 宣布全面解析清洗并校验成功！
	    #bParseSuccess := TRUE;
	    
	END_IF;
	#bTrigger_FP := #bTriggerParse; // 边沿锁存
	
END_FUNCTION_BLOCK
```

---

## 5. 深度解剖实战代码的“工业级通讯设计思维”

这段通讯解析程序，体现了我们在大型网络化工程中对“通信健壮性”的绝对把控。

### 5.1 零指针、零位移的高性能 Slice 重组（第 75~78 行）
在解析小端混排浮点数（Sensor 2 压力）时，我们写了这一段：
```scl
#tempDWord.B3 := #arrRxBuffer[8]; // A
#tempDWord.B2 := #arrRxBuffer[7]; // B
#tempDWord.B1 := #arrRxBuffer[6]; // C
#tempDWord.B0 := #arrRxBuffer[5]; // D
```
这是一个极其高级且高效的**“内存重组拼装器”**。
传统的 S7-300 写法，由于没有 Slice，你得写 4 次复杂的 `SHL` / `SHR` 逻辑移位，还要配合 `OR` 运算，CPU 需要执行十几条机器指令。
而在博途 S7-1500 优化块中，利用 Slice 语法（`.B0`..`.B3`），编译器会将它直接翻译为最底层的 **“寄存器一字节瞬时传送指令（Move Byte）”**。
**4 行代码，在一微秒内，以最快的硬件速度完成了小端到大端浮点数的数据重构。**

---

### 5.2 CRC16 容错防御（第 48 行）
在数据解码前，我们强制进行了 CRC16 比对：
`IF #wCalcCRC <> #wRecvCRC THEN ...`
在工业现场（尤其是大功率变频器群起、大电机高频启停的重度电磁噪声环境下），以太网或串口电缆会受到强烈的共模干扰。这会导致传送中的二进制位发生反转（比如 `1` 变成了 `0`）。
如果没有 CRC16 这道防线，PLC 就会把受损的数据误认为正常数据并输出，这可能会引发设备超速、机械撞击等重大工业事故。
**严格的通信校验，是自动化工业通讯的第一法则。**

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：误在 `TRCV` (TCP接收) 的“异步忙（BUSY）”状态下直接去解析缓冲区

TCP/IP 通信块 `TRCV` 在后台是异步运行的。它接收数据需要经历数个 PLC 扫描周期。

```scl
// ❌ 导致读取到半截报文、产生数据污染的严重错误写法
#trcvInstance(..., RCV_LEN => #iRcvLen);
// 致命：没有判断 NDR (数据接收完成) 信号，直接无脑解析外部缓冲区
"FC_PointerTelemetryParser"(arrRxBuffer := #arrCommBuffer, ...);
```
*致命后果*：
由于 TCP 会发生拆包。如果一包 64 字节的报文，当前周期只接收到了前 20 字节。由于你没有判断 `NDR`（New Data Received，数据接收完成脉冲），程序直接去解析 Byte 5-8 的浮点数。此时后面 44 字节全是 `16#00`（垃圾零数据）。温控系统会瞬间收到一个零值，导致设备误判发生剧烈控温抖动。
**防爆金律：在任何以太网通信中，必须以 `NDR` 信号（或者 `RCV_LEN` 完全等于期望值）作为启动解析的唯一安全触发源！**

---

### 6.2 错误二：高频频繁在线调用 `RDREC` 非周期读取导致 CPU 锁死
由于非周期读取（RDREC）需要消耗系统的异步通信队列通道。如果你在 OB1 中无脑地每个周期都去触发 `RDREC`。
*后果*：
这会把 PLC 的异步通信通道瞬间塞满（通信缓冲区溢出），导致触摸屏通信瞬间断开、PG/PC 无法在线连接。
**高级技巧：非周期读取，必须采用状态机定时触发（比如每 5s 读一次），或者只有在设备报警时才触发一次，绝不允许每个周期常态化在线呼叫。**

---

## 7. 课后练习

请独立思考并完成以下两个大型项目通讯架构级的练习：

### 练习 1：非标 Modbus RTU 仪表多通道整型数据 16 位 CRC 打包组帧器
我们要控制 5 台电子秤。PLC 需要向电子秤发送读取指令帧（Query Frame，占 6 字节）：
`arrTxBuffer : Array[0..7] of Byte;`
*   `Byte 0`：仪表站号（如 `1`）。
*   `Byte 1`：功能码 `16#03`。
*   `Byte 2 & 3`：起始寄存器地址 `16#0000`。
*   `Byte 3 & 4`：读取数量 `16#0002`。
*   `Byte 5 & 6`：整条报文前 6 字节的 CRC16 校验码（低字节在前，高字节在后）。
请编写一个 SCL FC，当操作员在 HMI 上点击“一键扫描”时：
*   **输入**：`iStationID : Int`。
*   **输出**：拼装完毕、带有高精度 CRC16 校验的完整的 8 字节 `arrTxBuffer`。

### 练习 2：基于 PROFINET 异步状态机的高精度变频器温度参数诊断器 (RDREC 应用)
我们需要读取一台大功率 PROFINET 变频器的非周期诊断数据块（数据记录号 Record Index = `16#0032`，硬件标识符 HW_ID = `264`）。
请编写一个 SCL **FB**，利用 `CASE` 状态机：
*   **输入**：`bTriggerRead : Bool` (读触发信号)。
*   **输出**：`rDriveTemp : Real` (读取出的变频器内部逆变桥温度，格式为 Real，存储在返回的 4 字节缓冲区中)。
*   **要求**：必须在内部安全多周期守候 `RDREC` 的 `BUSY`、`DONE`、`ERROR` 状态。如果通信超时或报错（通过 `STATUS` 诊断码输出，如 `16#80A0`），自动执行三次安全重试（Retry），三次失败后才正式抛出故障指示。

---

## 总结

这一章，我们彻底征服了西门子 SCL 编程、乃至整个工业物联网数字化大通道中最具挑战的阵地——**处理 Modbus 寄存器拼装、PROFINET 异步非周期数据访问、以及原生 TCP/IP 流式报文解析与校验**。

我们不仅在软件语法层级掌握了它，更从“大端与小端二进制排列对齐”的物理天机上，看透了高低字节对调在 CPU 寻址层面的物理机理；解剖了 PROFINET 异步 RDREC 通信函数在网络层多周期守候的状态机运行本质；掌握了利用 **Slice 位串片段技术** 极速拼装、解析小端浮点数（CDAB 格式）的绝活，并共同手写了一个拥有 16 位 CRC 严密校验、自适应多类型解析的“万能以太网通讯报文解析功能块（SCL）”。

请记住，**工业通讯是现代智能工厂的神经网络。在噪声重度的电磁环境下，用严密的校验和高效的移位算法去过滤、清洗和重构每一帧二进制字节，你写出的程序才能在工厂成千上万次的高频通信中，优雅、稳定、永不迷失。**

下一章，我们将正式攻克 SCL 在过程控制、模拟量滤波处理领域最核心、最经典，也是各大项目必用的物理算法阵地：**《SCL控制算法一阶低通滤波实现与动态时间常数补偿》**。届时，我将带你跨越离散时间与物理世界连续时间的鸿沟，手把手教你写出大师级的滤波控制算法。

加油，下期见！