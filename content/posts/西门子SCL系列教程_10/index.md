---
title: "第十章：SCL 结构体 STRUCT 详解与设备数据模型设计"
date: 2026-07-24T10:30:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们一起攻克了“数组”这个强大的数据容器，并用它构建了一个管理 100 台电机的磨损均衡系统。你应该已经体会到了将同类型变量打包管理的威力。"
---



在上一章中，我们一起攻克了“数组”这个强大的数据容器，并用它构建了一个管理 100 台电机的磨损均衡系统。你应该已经体会到了将同类型变量打包管理的威力。

但是，在真实的项目现场，一个物理设备（如一台电机、一个电磁阀、一个变频器）所包含的数据，**绝对不可能全是同一种数据类型**。

以最简单的三相异步电机为例，它包含：
*   控制指令：`bStartCmd`（Bool，启动指令）
*   状态反馈：`bRunFeedback`（Bool，运行反馈）、`bFault`（Bool，故障报警）
*   模拟监控：`rCurrent`（Real，运行电流）、`rTemp`（Real，轴承温度）
*   通信参数：`wStatusWord`（Word，变频器状态字）

如果在 PLC 里依然使用零散的变量，或者强行用不同的数组去拼凑，你的变量表就会乱成一团，程序接口也会变得极其臃肿。

这就是为什么我们需要掌握 **结构体（STRUCT）**。

`STRUCT` 是将**不同数据类型**的变量，按照逻辑关系组合在一起形成的一个新型数据实体。它是我们在工业自动化中构建**设备数据模型（Device Data Model）**的最核心工具。

今天，师父带你彻底拆解 STRUCT 的物理本质、寻址对齐、嵌套设计，并带你手写一个符合现代工业标准的**“电机设备结构体及其智能控制功能块”**。

---

## 1. 为什么工业项目需要结构体？

很多刚入行的徒弟，写程序时喜欢“信手拈来”：
*   需要电机 1 启动，就建一个 `bMotor1_Start`；
*   需要电机 1 反馈，就建一个 `bMotor1_Fbk`；
*   需要电机 2 启动，再建一个 `bMotor2_Start`。

这种非结构化的编程方式，在软件工程中被称为 **“扁平化杂乱变量（Spaghetti Variables）”**。

### 1.1 面条变量的致命缺陷
1.  **丧失高内聚性（Cohesion）**：
    在人的大脑认知里，“电机 1”是一个独立的物理实体。但是，在 PLC 变量表中，它的启动信号、反馈信号、温度信号却散落各处，彼此之间在数据结构上没有任何强关联。
2.  **块接口臃肿（Interface Bloat）**：
    如果你写一个通用的电机控制 FC，因为没有结构体，你必须给这个 FC 声明 10 个输入参数、8 个输出参数。每次调用这个 FC，你的引脚就会塞满整个屏幕。

```
 ❌ 无结构体的臃肿接口调用:                 正确的结构体优雅调用:
 ┌───────────────────────────┐           ┌───────────────────────────┐
 │       FC_MotorControl     │           │       FC_MotorCtrl_New    │
 ├───────────────────────────┤           ├───────────────────────────┤
 ──> bStart                  │           ──> stMotorData             │
 ──> bStop                   │           └───────────────────────────┘
 ──> bAutoMode               │           (所有 10 几个参数全部打包在一根
 ──> bFbkRun                 │            线里传入，极度清爽！)
 ──> bFbkFault               │
 ──> rCurrent                │
 ──> rSpeedSet               │
 <── bOutRun                 │
 <── bOutFault               │
 └───────────────────────────┘
```

3.  **无法面向对象建模**：
    现代自动化设计极力推行 **“面向对象编程（OOP）”** 的思想。
    结构体 `STRUCT`，就是我们在 PLC 里将物理设备抽象为“数字对象”的第一步。有了 `STRUCT`，我们在 SCL 中写代码时，脑子里想的不再是零散的位和字节，而是：**`电机.控制`**、**`电机.状态`**、**`电机.参数`**。

---

## 2. STRUCT 结构体在 SCL 中的定义与物理内存

在 TIA 博途中，结构体 `STRUCT` 可以声明在：
*   FB/FC 的 `VAR`（静态区）、`VAR_TEMP`（临时区）、`VAR_INPUT/OUTPUT`（接口区）。
*   全局数据块（Global DB）中。

### 2.1 基础声明语法

在 SCL 的变量声明区中，结构体的定义方式如下：

```scl
VAR
    #stMotor : STRUCT
        bCmdStart : Bool;       // 启动指令
        bRunFeedback : Bool;    // 运行反馈
        rActualSpeed : Real;    // 实际速度
        iErrorCode : Int;       // 故障代码
    END_STRUCT;
END_VAR
```

---

### 2.2 结构体嵌套（Nested STRUCT）：大厂的标准架构

在开发中型及以上项目时，我们通常会按照 **“控制指令、状态反馈、配置参数”** 的经典三层架构，对设备进行结构体嵌套设计：

```scl
VAR
    #stFan : STRUCT
        Ctrl : STRUCT           // 1. 控制层 (PLC 发出的指令)
            bStart : Bool;
            bStop : Bool;
            bReset : Bool;
            rSpeedSet : Real;
        END_STRUCT;
        
        Sts : STRUCT            // 2. 状态层 (设备反馈的状态)
            bRunning : Bool;
            bFault : Bool;
            rCurrent : Real;
            rTemp : Real;
        END_STRUCT;
        
        Param : STRUCT          // 3. 参数层 (工艺配置参数)
            tStartDelay : Time := T#2s;  // 启动延时
            rOverCurrentLimit : Real := 15.0; // 额定电流报警上限
        END_STRUCT;
    END_STRUCT;
END_VAR
```

*为什么这样设计？*
这种分类结构能极大地提高代码自解释性。在 SCL 代码区中，你可以写出极具艺术感、完全不需要写注释的代码：
`#stFan.Ctrl.bStart := TRUE;`
`IF #stFan.Sts.rCurrent > #stFan.Param.rOverCurrentLimit THEN ...`

---

### 2.3 💡 结构体的物理内存布局与对齐（Alignment）

作为高级工程师，你必须时刻关注结构体在内存中的排列。这直接决定了通信协议打包和 CPU 执行速度。

#### 1) 在标准数据块（非优化 DB）中：
为了使 CPU 的 16 位或 32 位内部总线能够高效读取，编译器在存储结构体时，会进行 **“地址对齐（Address Alignment）”**。
*   `Bool` 占用 1 Bit，但如果紧跟着一个 `Real`（4 字节，需要 4 字节边界对齐），编译器会自动在 `Bool` 后面填补 **3 个字节（24 Bits）的空隙（Padding）**。
*   这导致：你以为结构体只占了 5 个字节，但在标准 DB 里它实际吞噬了 8 个字节的物理空间。

#### 2) 在博途优化数据块（Optimized DB）中：
西门子全新的编译器在后台自动重排了结构体成员的物理存放顺序，将空间压缩得严丝合缝，同时保证了 CPU 的寄存器级极速读取。
**因此，对于复杂的嵌套 STRUCT 结构，强烈建议使用博途优化块访问。**

---

## 3. STRUCT 结构体的高效访问与赋值

在 SCL 中，对结构体成员的访问采用 **点“.”运算符**。

```scl
#stFan.Ctrl.rSpeedSet := 1500.0; // 写入
#rSpeedTemp := #stFan.Sts.rCurrent; // 读取
```

### 3.1 战术一：结构体整体一键赋值（Bulk Copy）

在传统编程中，如果你想把一个设备的数据完全备份到另一个变量中，你得把里面的每个子成员挨个 `MOVE` 一遍。
而在 SCL 中，如果两个结构体的**内部成员结构和类型完全一致（即“同构”的）**，你可以直接进行整块一键复制！

```scl
// 声明两个完全同构的结构体
VAR
    #stMotor_Active : "UDT_MotorModel"; // 假设使用相同的 UDT
    #stMotor_Backup : "UDT_MotorModel";
END_VAR

// 在 SCL 中，一行代码，瞬间完成所有子成员的数据拷贝（包括里面的 Real、Bool、Int 等）
#stMotor_Backup := #stMotor_Active; 
```
*底层动作*：CPU 内部会通过高速的 `Block Move` 指令，直接按字节块拷贝整片物理内存，**执行效率极高**。

---

### 3.2 战术二：数组与结构体的完美合体（Array of STRUCT）

上一章我们学习了数组。当我们将数组和结构体结合起来时，我们就能构建出真正强大的“群控数据库”：

```scl
VAR
    // 声明一个包含 100 台电机的结构体数组
    #arrCompressors : Array[1..100] of STRUCT
        bStartCmd : Bool;
        rCurrent : Real;
    END_STRUCT;
END_VAR
```

访问方式：
```scl
#arrCompressors[5].bStartCmd := TRUE; // 启动 5 号压缩机
```

---

## 4. 设备数据模型设计：抽象的力量

在大型项目中，最核心的步骤就是**设备建模**。一个好的设备结构体设计，不仅能完全覆盖硬件的所有特性，还能无缝对接 HMI（触摸屏）和 MES 系统。

师父为你总结了一套**“标准工业设备三维抽象模型”**，任何物理执行机构（阀门、加热器、泵、切刀）都可以完美套用此模型进行结构体设计：

```
                    ┌──────────────────────────────────────────────┐
                    │            标准工业设备 STRUCT 模型          │
                    └──────────────────────┬───────────────────────┘
                                           │
         ┌─────────────────────────────────┼────────────────────────────────┐
         ▼                                 ▼                                ▼
┌─────────────────┐               ┌─────────────────┐              ┌─────────────────┐
│ 1. CMD / CTRL   │               │   2. STS / FBK  │              │  3. PAR / CFG   │
│ (控制输入/指令层)│               │  (物理反馈/状态层)│              │ (工艺参数/配置层)│
├─────────────────┤               ├─────────────────┤              ├─────────────────┤
│ • 自动/手动启动  │               │ • 运行/停止反馈  │              │ • 启动延时设定  │
│ • 速度/压力给定  │               │ • 故障/过载警报  │              │ • 超限报警电流  │
│ • 故障复位请求  │               │ • 实时温度/电流  │              │ • 反馈超时限定  │
└─────────────────┘               └─────────────────┘              └─────────────────┘
```

---

## 5. 工业级综合案例：智能电机结构体及其控制核心程序

现在，我们把本章讲的结构体设计、嵌套架构、以及上一章的数组、循环结合起来。

### 5.1 工业工艺描述
我们需要编写一个通用的标准电机控制功能块 **`FB_SmartMotor`**：
1.  **控制要求**：
    *   电机支持自动模式（`bAutoMode`）和手动模式（`bManualMode`）。
    *   在手动模式下，响应操作员在 HMI 上的手动启动/停止按键（`bHmiStart` / `bHmiStop`）。
    *   在自动模式下，响应 PLC 系统发来的自动运行指令（`bAutoStart`）。
2.  **安全性（核心：运行反馈检测算法）**：
    *   当 PLC 输出启动驱动（`bCmdStart` := TRUE）后，电机的接触器辅助触点必须在设定的**反馈超时时间**内反馈回 `TRUE` 信号（`bFbkRunning`）。
    *   如果在设定时间（如 3 秒）内没有收到反馈，说明接触器吸合失败，或者是现场电机被卡死，程序必须**立刻强行切断输出，自锁并报“反馈丢失故障”**。
    *   同理，当输出停止驱动后，如果运行反馈依然长亮，报“接触器粘连故障”。
3.  **数据交互**：
    *   所有这些数据，不使用零散引脚，全部打包在一个结构体中传入和传出。

---

### 5.2 步骤一：创建全局自定义数据类型（UDT）

由于结构体需要在 FB 的接口引脚上被传入和传出，为了保持类型一致，我们必须将结构体提升为全局的 **PLC 数据类型（UDT）**。
（我们在 TIA 项目树中，添加新 PLC 数据类型，命名为 `UDT_SmartMotorModel`）：

```scl
TYPE "UDT_SmartMotorModel"
VERSION : 0.1
   STRUCT
      Ctrl : STRUCT              // 1. 控制指令层
         bAutoMode : Bool;       // 自动/手动模式切换 (TRUE=自动, FALSE=手动)
         bAutoStart : Bool;      // 自动启动指令 (来自 PLC 内部逻辑)
         bHmiStart : Bool;       // 手动启动指令 (来自 HMI 按钮)
         bHmiStop : Bool;        // 手动停止指令 (来自 HMI 按钮)
         bReset : Bool;          // 故障一键复位
      END_STRUCT;
      
      Fbk : STRUCT               // 2. 物理硬件反馈层
         bFbkRunning : Bool;     // 电机接触器吸合运行反馈信号 (DI)
         bFbkOverload : Bool;    // 电机热继电器过载保护信号 (DI)
      END_STRUCT;
      
      Sts : STRUCT               // 3. 运行状态输出层
         bOutStart : Bool;       // PLC 真实输出驱动线圈 (DO)
         bRunning : Bool;        // 电机运行中状态
         bFault : Bool;          // 电机汇总故障报警
         iErrorCode : Int;       // 故障代码 (0:正常, 1:过载, 2:吸合失败, 3:粘连)
      END_STRUCT;
      
      Cfg : STRUCT               // 4. 工艺参数配置层
         tFeedbackTimeout : Time := T#3s; // 反馈监控超时设定时间
      END_STRUCT;
   END_STRUCT;
END_TYPE
```

---

### 5.3 步骤二：块接口声明（FB_SmartMotorControl）

我们创建核心 FB：`FB_SmartMotorControl`。该块包含用于监测超时的时间定时器，所以必须采用 **FB**。通过 `VAR_IN_OUT` 将整个电机的结构体对象传入。

```
VAR_INPUT
    bPulse_1Hz : Bool;         // 用于报警指示灯闪烁的系统脉冲
END_VAR

VAR_IN_OUT
    stMotor : "UDT_SmartMotorModel"; // 核心：整个电机的结构体数据模型 (引用传递)
END_VAR

VAR
    tonFbkOnTimeout {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME;  // 启动反馈超时定时器
    tonFbkOffTimeout {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME; // 停止反馈粘连定时器
    bManualRunLatch : Bool;    // 手动运行锁存信号静态变量
END_VAR
```

---

### 5.4 步骤三：SCL 代码实现

```scl
FUNCTION_BLOCK "FB_SmartMotorControl"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 无条件热继电器过载物理保护（最高优先级）
	// ==========================================
	IF #stMotor.Fbk.bFbkOverload THEN
	    #stMotor.Sts.bOutStart := FALSE; // 强制切断物理输出
	    #bManualRunLatch := FALSE;       // 复位手动锁存
	    #stMotor.Sts.bFault := TRUE;     // 触发汇总故障
	    #stMotor.Sts.iErrorCode := 1;    // 故障码 1: 物理热过载
	END_IF;
	
	// ==========================================
	// 2. 模式转换与起停控制逻辑
	// ==========================================
	IF NOT #stMotor.Sts.bFault THEN // 仅在无故障状态下允许动作
	    
	    // ------------------------------------------
	    // A. 自动模式逻辑
	    // ------------------------------------------
	    IF #stMotor.Ctrl.bAutoMode THEN
	        // 在自动模式下，直接由自动启动指令决定物理输出
	        #stMotor.Sts.bOutStart := #stMotor.Ctrl.bAutoStart;
	        
	    // ------------------------------------------
	    // B. 手动模式逻辑
	    // ------------------------------------------
	    ELSE
	        // 手动起停自锁控制（HMI 按钮触发）
	        IF #stMotor.Ctrl.bHmiStart THEN
	            #bManualRunLatch := TRUE;  // 启动自锁
	        ELSIF #stMotor.Ctrl.bHmiStop THEN
	            #bManualRunLatch := FALSE; // 停止动作
	        END_IF;
	        
	        #stMotor.Sts.bOutStart := #bManualRunLatch;
	    END_IF;
	    
	END_IF;
	
	// ==========================================
	// 3. 安全诊断：接触器动作反馈监控
	// ==========================================
	
	// --- 反馈吸合超时监测 ---
	// 当 PLC 输出启动指令后，启动反馈计时器
	#tonFbkOnTimeout(IN := #stMotor.Sts.bOutStart AND (NOT #stMotor.Fbk.bFbkRunning),
	                 PT := #stMotor.Cfg.tFeedbackTimeout);
	
	IF #tonFbkOnTimeout.Q THEN
	    #stMotor.Sts.bOutStart := FALSE; // 反馈超时未恢复，强行关泵切断输出
	    #bManualRunLatch := FALSE;
	    #stMotor.Sts.bFault := TRUE;     // 锁定故障
	    #stMotor.Sts.iErrorCode := 2;    // 故障码 2: 接触器吸合失败
	END_IF;
	
	// --- 反馈粘连超时监测 ---
	// 当 PLC 停止指令发出后，如果运行反馈迟迟不消失，启动粘连计时器
	#tonFbkOffTimeout(IN := (NOT #stMotor.Sts.bOutStart) AND #stMotor.Fbk.bFbkRunning,
	                  PT := #stMotor.Cfg.tFeedbackTimeout);
	                  
	IF #tonFbkOffTimeout.Q THEN
	    #stMotor.Sts.bFault := TRUE;
	    #stMotor.Sts.iErrorCode := 3;    // 故障码 3: 接触器粘连
	END_IF;
	
	// ==========================================
	// 4. 故障一键复位逻辑
	// ==========================================
	IF #stMotor.Ctrl.bReset THEN
	    // 只有在热继电器已复位、且动作反馈已归零后，才允许复位故障
	    IF (NOT #stMotor.Fbk.bFbkOverload) AND (NOT #stMotor.Fbk.bFbkRunning) THEN
	        #stMotor.Sts.bFault := FALSE;
	        #stMotor.Sts.iErrorCode := 0; // 恢复正常代码
	        #tonFbkOnTimeout(IN := FALSE, PT := #stMotor.Cfg.tFeedbackTimeout);
	        #tonFbkOffTimeout(IN := FALSE, PT := #stMotor.Cfg.tFeedbackTimeout);
	    END_IF;
	END_IF;
	
	// ==========================================
	// 5. 最终状态汇总与 HMI 指示灯驱动
	// ==========================================
	// 如果发生故障，HMI 指示灯根据系统自带的 1Hz 脉冲进行闪烁报警
	IF #stMotor.Sts.bFault THEN
	    #stMotor.Sts.bRunning := #bPulse_1Hz; 
	ELSE
	    #stMotor.Sts.bRunning := #stMotor.Fbk.bFbkRunning; // 正常运行
	END_IF;
	
END_FUNCTION_BLOCK
```

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：误将“临时局部结构体（STRUCT）”当作通用接口类型

有些徒弟在编写子块（FC）时，直接在输入引脚上拉了一个手动定义的 `STRUCT`：
```scl
// ❌ 导致后续外部参数根本无法传入的接口写法
VAR_INPUT
    MyMotorInput : STRUCT
        bStart : Bool;
    END_STRUCT;
END_VAR
```
*后果*：博途编译器对“结构体一致性”审查极严。如果不是引用同一个 **PLC 数据类型（UDT）** 模板产生的结构体，**即使里面的成员名字、类型一模一样，博途也坚决认为它们是完全不一样的结构，从而无法在主程序中把任何外部 DB 的结构体变量接到这个引脚上！**
**黄金法则：在编写任何跨块传输的设备结构体时，一律先去“PLC数据类型（UDT）”中建模板，不允许手写未命名的 STRUCT 接口。**

---

### 6.2 错误二：频繁读写外部复杂嵌套结构体产生的性能红损
```scl
// ❌ 性能低下的嵌套寻址写法
IF "DB_PlantData".Motors[5].Ctrl.bAutoMode THEN
    "DB_PlantData".Motors[5].Sts.bOutStart := "DB_PlantData".Motors[5].Ctrl.bAutoStart;
END_IF;
```
*后果*：这种多次跨越全局 DB、多级点“.运算符”寻找变量的做法，在底层会导致 CPU 进行多轮复杂的符号寻址和地址偏移计算，极大地消耗系统时钟。
*高阶解法（Ref 引用指针/FC引脚）*：
如本章案例 5 所示，**在 FB/FC 内部，通过 `IN_OUT` 将结构体整个接进来，程序内部完全使用本地缩写的别名操作。** 编译器底层会利用高性能的地址寄存器进行直接指针访问，代码可读性极佳，且效率达到最高。

---

## 7. 课后练习

请独立思考并编写以下两个具有高阶工艺价值的设备数据模型设计：

### 练习 1：智能单向双动气动调节阀结构体及监控系统 (UDT + SCL 控制)
在化工管道上，调节阀门是核心执行元件。单向双动气动阀包含：1个开启电磁阀驱动、1个关闭电磁阀驱动、1个开到位行程传感器、1个关到位行程传感器。
1.  请设计一个全局 PLC 数据类型（UDT）命名为 `UDT_SmartValveModel`，严格遵循“控制、反馈、状态、配置”四层结构进行设计。
2.  编写一个配套的控制 FB：
    *   **工艺安全要求**：当收到开启指令（`bOpenCmd`）后，如果同时收到关闭指令（`bCloseCmd`），强行互锁不动作。
    *   **时间诊断**：如果开启输出后，在 5 秒（`tTimeout`）内开到位传感器没有触发，或者关到位传感器没有消失，报“阀门动作卡死故障”。
    *   **异常诊断**：如果物理上开到位和关到位传感器**同时输出 TRUE**（物理上不可能发生，除非限位开关损坏），立刻发出“双位冲突故障”并强制切断电磁阀输出，避免气路故障。

### 练习 2：高精度重力配料称数据模型设计及校零程序
在混料机车间，重力称（Load Cell）的数据模型极其精密。
1.  设计一个 `UDT_WeighScale` 结构体，包含：
    *   实时毛重（`rGrossWeight`）
    *   实时净重（`rNetWeight`）
    *   校零偏置（`rTareOffset`）
    *   最大安全满量程上限（`rMaxCapacity`）
    *   校零触发（`bTareCmd`）
2.  编写一个 SCL FC，对该称进行**一键去皮/校零逻辑**：
    *   当操作员在 HMI 上按下去皮按钮 `bTareCmd` 时，程序必须抓取当前的实时毛重值 `rGrossWeight`，写入到 `rTareOffset` 中，并将 `bTareCmd` 复位。
    *   在后续每个周期，净重计算公式为：`净重 = 毛重 - 偏置`。
    *   **安全要求**：如果当前毛重超出了最大安全满量程，发出“传感器过载”故障标志，保护高精度的称重传感器。

---

## 总结

这一章，我们彻底攻克了 SCL 编程中决定“面向对象程序框架”生死存亡的至高阵地——**结构体 STRUCT 与设备数据模型**。

我们不仅在语法层面掌握了它的定义和多层嵌套美学，更深入剖析了它在标准 DB 与优化 DB 内部底层字节对齐的寻址差异。我们共同定义了符合现代工业标准、打包在 UDT 内并利用引用传递优化运算效率的“智能电机综合控制功能块”。

请记住，**把工艺中散落的位、字节、双字打包组合成有物理生命力的“设备结构体模型”，是你独立进行大型模块化项目架构最坚实的一步。**

下一章，我们将彻底打通自定义类型的终极大门：**《SCL自定义数据类型UDT深度剖析》**。我们将探讨 UDT 与 STRUCT 的本质区别，研究大厂如何在标准库设计中利用 UDT 实现“一处修改，全局自适应”的极速重构。

加油，下期见！