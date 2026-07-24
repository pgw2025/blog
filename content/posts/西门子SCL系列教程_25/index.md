---
title: "第二十五章：SCL 在运动控制中的应用与伺服轴多功能状态机控制系统"
date: 2026-07-24T12:55:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们一起攻克了工业通信数据解析的硬核阵地，掌握了大端小端字节序重组与 16 位 CRC 高速算法。"
---

在上一章中，我们一起攻克了工业通信数据解析的硬核阵地，掌握了大端小端字节序重组与 16 位 CRC 高速算法。

今天，我们要跨入工业自动化中最具动感、最高精度，也最能展现电气工程师含金量的核心技术领地——**运动控制（Motion Control）**。

在当今智能制造（如锂电叠片、机器人龙门架、包装飞剪、半导体贴片）中，伺服电机（Servo Motor）是绝对的动力心脏。
*   **速度控制**：控制皮带轮、输送线平滑加减速，保持多轴恒速同步。
*   **位置控制**：控制滚珠丝杠、直驱电机以微米级的精度精准定位（绝对定位 / 相对定位）。
*   **状态管理**：伺服系统拥有极度严苛的系统状态转换机（PLCopen 标准状态机）。你必须保证在任何时候，伺服的使能、回零、定位、故障复位动作，都以完美的物理闭环顺序进行运转。

如果你尝试用传统的 梯形图（LAD）去写轴使能、回零、绝对定位、速度运行、报警复位等一连串的 PLCopen 运动控制块（`MC_Power`、`MC_Home`、`MC_MoveAbsolute` 等），你的程序里会塞满成百上千个中间标志位和错综复杂的互锁触点。

而在 SCL 中，**通过将工艺对象（Technology Object, TO）作为引脚变量直接引入，配合多重背景运动控制系统块以及我们第二十章学过的状态机（FSM）思想，我们只需要一个优雅的 `CASE` 状态机，就能构建出一套稳健如磐石、完全符合 PLCopen 国际标准的“伺服轴多功能运动控制系统”。**

今天，师父带你剖析西门子工艺对象的物理运行本质，揭开运动控制系统块“异步多周期执行”的底牌，并手写一个生产级的**“伺服轴多功能状态机控制功能块（SCL）”**。

---

## 1. 工艺对象（TO）与 PLCopen 标准的底层天机

在经典 PLC 时代，我们要控制一个伺服，需要手动去算 PTO 脉冲频率、去配置脉冲发生器硬件，这极其繁琐。
而在西门子 S7-1200/1500 控制器中，推出了先进的 **工艺对象（Technology Object，简称 TO）**。

### 1.1 什么是工艺对象（TO）？
工艺对象是运行在 PLC 操作系统内部的**“高层软件对象”**。它代表了现场一个真实的物理伺服轴。
*   你只需要在博途中对 TO 轴进行图形化物理参数标定（如电机的减速比、丝杠导程、软件限位、回零传感器位置）。
*   **数据本质**：编译后，系统会自动在 RAM 中生成一个全局可见的工艺数据结构（例如 `"Axis_1"`，类型为 `TO_PositioningAxis`）。这个数据结构内部实时暴露着轴的一切物理动态：
    *   `"Axis_1".ActualPosition`：当前的实际物理坐标。
    *   `"Axis_1".ActualVelocity`：当前的实际运行速度。
    *   `"Axis_1".StatusWord.X5`：轴是否已经成功回零（Homed）。

---

### 1.2 异步执行：运动控制系统块的“多周期守候”

在 PLCopen 标准中，所有的运动控制都是通过带有 `MC_` 前缀的系统功能块（SFB）实现的：
*   **`MC_Power`**：使能控制（伺服上电/断电）。
*   **`MC_Reset`**：复位报警。
*   **`MC_Home`**：寻找机械原点（回零）。
*   **`MC_MoveVelocity`**：速度运行。
*   **`MC_MoveAbsolute`**：高精度绝对位置定位。
*   **`MC_Stop`**：安全停止。

#### 💡 核心硬件机理：
这些 `MC_` 块是 **异步运行（Asynchronous）** 的。当你将 `#MC_MoveAbsolute.Execute` 置为 `TRUE` 驱动轴去往 `500.0mm` 位置时，**CPU 绝对不可能在一个扫描周期内完成动作**（因为机械丝杠旋转到 500mm 需要花费数秒钟）。

因此，你必须在 SCL 中利用**状态机多周期守候**它们的物理状态引脚：
*   **`Busy` (Bool)**：定时器/轴正在高频执行该动作中。
*   **`Done` (Bool)**：该动作已经完美结束（如定位已精准到达 500mm）。
*   **`CommandAborted` (Bool)**：动作在中途被其他指令强行打断（抢占）。
*   **`Error` (Bool)**：动作失败（如中途撞到了物理限位开关）。

---

## 2. 运动状态管理的硬核设计模式：PLCopen 状态机

在真实重工业现场，伺服轴的动作转换必须完全遵循 **PLCopen 国际标准状态机**：

```
                    PLCopen 标准伺服状态转换机
                    
                      上电初始化
                           │
                           ▼
              ┌──────────────────────────┐
              │     0. ST_DISABLED       │ (伺服断电卸载，自由手推状态)
              └────────────┬─────────────┘
                           │ MC_Power = TRUE
                           ▼
              ┌──────────────────────────┐
              │     10. ST_ENABLING      │ (伺服自动上电合闸，抱闸开启)
              └────────────┬─────────────┘
                           │ Power.Status = TRUE
                           ▼
              ┌──────────────────────────┐
              │     20. ST_HOMING        │ (执行 MC_Home，寻找物理机械零位)
              └────────────┬─────────────┘
                           │ Axis.StatusWord.X5 = TRUE (回零成功)
                           ▼
              ┌──────────────────────────┐
              │     30. ST_STANDSTILL    │ <────────────────────────┐
              └──────┬──────────────┬────┘                          │
                     │              │                               │
    MC_MoveVelocity  │              │ MC_MoveAbsolute               │
    (启动持续速度运行)│              │ (启动高精度绝对定位)           │
                     ▼              ▼                               │
              ┌──────────────┐ ┌──────────────┐                     │
              │ 40. ST_MOV_V │ │ 50. ST_MOV_A │                     │
              └──────┬───────┘ └──────┬───────┘                     │
                     │                │                             │
                     ├────────────────┴───> [ 动作 Done / 到达 ] ───┘
                     │ 发生物理碰撞/故障
                     ▼
              ┌──────────────────────────┐
              │     99. ST_FAULT         │ (触发 MC_Reset 故障解除)
              └──────────────────────────┘
```

作为高水平的电气工程师，你的状态机转换代码必须严格遵循此物理顺序。**绝不允许在轴未使能时去调用定位，也绝不允许在轴未成功回零时去启动高速运行（那会导致设备高速冲出轨道发生重大物理损坏）。**

---

## 3. 工业级综合案例：伺服轴多功能状态机控制系统

现在，我们将工艺对象（`TO_PositioningAxis`）、时间三剑客、PLCopen 标准五大核心运动功能块以及安全状态机全部熔炼在一起。

### 3.1 伺服轴控制工艺流程与控制要求
我们需要编写一个通用伺服轴控制 FB：`FB_SCL_AxisController`。
1.  **安全使能层 (ST_ENABLING)**：
    当操作员按下“系统起动”按钮后，首先调用 `MC_Power` 强行启动轴使能。必须确认使能成功（`MC_Power.Status` = TRUE），才允许进入下一步。
2.  **自动找零层 (ST_HOMING)**：
    为了保证绝对定位的精准，使能成功后，系统必须**自动强制回零（MC_Home）**。回零成功（`TO.StatusWord.X5` = TRUE）后，转入待机状态（ST_STANDSTILL）。
3.  **高精度绝对定位 (ST_MOVING_ABS)**：
    在待机下，当收到“绝对定位请求（`bTrigger_Abs`）”时，启动 `MC_MoveAbsolute` 驱动轴前往目标位置（`rTarget_Position`），目标速度由 `rTarget_Velocity` 决定。必须等待轴精准到达目标位置（`MC_MoveAbsolute.Done` 为 TRUE），才允许返回待机。
4.  **持续速度运行 (ST_MOVING_VEL)**：
    当收到“连续运行（`bTrigger_Vel`）”时，启动 `MC_MoveVelocity` 驱动轴以恒定速度运行。按下停止按钮时，调用 `MC_Stop` 强制将轴平滑减速刹车，停稳后返回待机。
5.  **全局故障一票否决与硬复位 (ST_FAULT)**：
    在任何时候（使能、定位、速度运行中），只要发生物理故障、急停拍下、或者工艺对象报警。**程序必须立即一票否决拦截控制流**，切断所有运动指令，调用 `MC_Stop` 强行刹车，并切入 `ST_FAULT`。
    操作员按下“故障复位（`bReset`）”时，调用 `MC_Reset` 进行硬复位，复位成功后重新回零。

---

### 3.2 步骤一：接口变量区声明（FB_SCL_AxisController）

（我们在静态变量区直接声明所有 `MC_` 块的多重背景实例，零背景 DB 碎片）：

```
VAR_INPUT
    bSystem_PowerOn : Bool;     // 物理按钮：系统一键使能起动
    bSystem_PowerOff : Bool;    // 物理按钮：系统断电卸载
    bTrigger_Home : Bool;       // 手动一键强制回零请求
    bTrigger_Abs : Bool;        // 触发高精度绝对定位指令
    bTrigger_Vel : Bool;        // 触发恒速运行指令
    bCmd_Stop : Bool;           // 运动过程中的平滑减速停止按钮
    bReset : Bool;              // 轴报警故障一键复位
    rTarget_Position : Real;    // 绝对定位目标物理坐标 (mm)
    rTarget_Velocity : Real;    // 运行目标速度 (mm/s)
END_VAR

VAR_OUTPUT
    bAxis_Power_On : Bool;      // 状态：轴已成功上电合闸
    bAxis_Homed : Bool;         // 状态：轴已成功回零（坐标建立）
    bAxis_Standstill : Bool;    // 状态：轴处于就绪待机中
    bOut_Fault : Bool;          // 轴汇总故障报警
    iActiveState : Int;         // 输出当前状态步骤码给 HMI
    rActual_Pos : Real;         // 实时监控：轴当前物理实际位置 (mm)
    rActual_Vel : Real;         // 实时监控：轴当前实际速度 (mm/s)
END_VAR

VAR_IN_OUT
    // 核心引脚：引入西门子全局工艺对象 (TO Positioning Axis)
    // S7-1200/1500 系统内标准轴类型
    Axis : TO_PositioningAxis; 
END_VAR

VAR
    // ==========================================
    // 静态私有变量 (STAT) - 多重背景运动控制块
    // ==========================================
    iState : Int := 0;          // 运动控制唯一状态机变量
    bFaultActive : Bool;        // 故障锁定状态
    
    // 核心：PLCopen 标准多重背景系统块直接嵌入
    mcPower : MC_Power;         // 轴使能控制
    mcReset : MC_Reset;         // 轴复位
    mcHome : MC_Home;           // 轴回零
    mcMoveAbs : MC_MoveAbsolute; // 绝对定位
    mcMoveVel : MC_MoveVelocity; // 速度运行
    mcStop : MC_Stop;           // 安全停止
    
    // 边沿锁存
    bStartAbs_FP : Bool;
    bStartVel_FP : Bool;
END_VAR

VAR_CONST
    // ==========================================
    // PLCopen 规范状态常数 (消灭魔术数字)
    // ==========================================
    ST_OFF : Int := 0;          // 伺服完全断电状态
    ST_ENABLING : Int := 10;    // 伺服合闸使能中
    ST_HOMING : Int := 20;      // 伺服自动回零中
    ST_STANDSTILL : Int := 30;  // 伺服上电静止待机中（就绪）
    ST_MOVING_ABS : Int := 40;  // 伺服绝对定位动作中
    ST_MOVING_VEL : Int := 50;  // 伺服恒速动作中
    ST_STOPPING : Int := 60;    // 伺服安全减速制动中
    ST_FAULT : Int := 99;       // 伺服故障锁定状态
END_VAR
```

---

### 3.3 步骤二：SCL 核心代码实现

徒弟，请仔细阅读这套代码。**我们是如何利用多重背景在 SCL 外部进行无条件“扫尾更新”、以及如何对工艺对象进行高内聚状态管理的。**

```scl
FUNCTION_BLOCK "FB_SCL_AxisController"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 工艺对象实时状态提取 (探针反馈)
	// 每个周期无条件提取实际物理值输出给触摸屏
	// ==========================================
	#rActual_Pos := #Axis.ActualPosition;
	#rActual_Vel := #Axis.ActualVelocity;
	#bAxis_Homed := #Axis.StatusWord.X5; // X5 为西门子 TO 轴回零成功标志位
	
	// ==========================================
	// 2. 运动控制多重背景更新区域 (裸露于最外层，防假死)
	// 在 SCL 中，异步系统块必须每个周期被 CPU 扫到，
	// 才能正常监测到轴的 Done、Error 沿变化！
	// ==========================================
	#mcPower(Axis := #Axis);
	#mcReset(Axis := #Axis);
	#mcHome(Axis := #Axis);
	#mcMoveAbs(Axis := #Axis);
	#mcMoveVel(Axis := #Axis);
	#mcStop(Axis := #Axis);
	
	// ==========================================
	// 3. 全局高优先级故障拦截 (一票否决)
	// ==========================================
	// 如果轴本身发生硬件报错（或外部拍下急停/过载）
	IF #Axis.ErrorWord <> 0 THEN
	    #bFaultActive := TRUE;
	    #iState := #ST_FAULT; // 强行拦截，瞬间切入故障安全状态
	END_IF;
	
	// ==========================================
	// 4. 核心运动状态机逻辑 (CASE 结构)
	// ==========================================
	CASE #iState OF
	        
	    #ST_OFF:
	        // 动作：轴彻底断电卸载
	        #mcPower.Enable := FALSE;
	        #bAxis_Power_On := FALSE;
	        #bAxis_Standstill := FALSE;
	        
	        // 跃迁条件：一键起动按钮按下，进入合闸使能阶段
	        IF #bSystem_PowerOn THEN
	            #iState := #ST_ENABLING;
	        END_IF;
	        
	    #ST_ENABLING:
	        // 动作：驱动 MC_Power 块使能引脚
	        #mcPower.Enable := TRUE;
	        #mcPower.StartMode := 1; // 1 代表位置和速度完全接管
	        
	        // 跃迁条件：轴成功使能（Status反馈为 TRUE）
	        IF #mcPower.Status THEN
	            #bAxis_Power_On := TRUE;
	            
	            // 如果轴此前没有建立坐标（未回零），强制进入自动找零状态
	            IF NOT #Axis.StatusWord.X5 THEN
	                #iState := #ST_HOMING;
	            ELSE
	                #iState := #ST_STANDSTILL; // 已经回零过，直接进入就绪
	            END_IF;
	        END_IF;
	        
	        // 断电按键检测
	        IF #bSystem_PowerOff THEN
	            #iState := #ST_OFF;
	        END_IF;
	        
	    #ST_HOMING:
	        // 动作：触发回零
	        #mcHome.Execute := TRUE;
	        #mcHome.Position := 0.0; // 设定原点坐标为 0.0 mm
	        #mcHome.Mode := 3;       // 3 代表主动寻找物理挡块回零模式
	        
	        // 跃迁条件：回零动作成功（mcHome.Done）且坐标已建立
	        IF #mcHome.Done THEN
	            #mcHome.Execute := FALSE; // 及时复位触发沿
	            #iState := #ST_STANDSTILL;
	        ELSIF #mcHome.Error THEN
	            #mcHome.Execute := FALSE;
	            #iState := #ST_FAULT;
	        END_IF;
	        
	    #ST_STANDSTILL:
	        // 动作：轴静止就绪，复位所有动作触发
	        #bAxis_Standstill := TRUE;
	        #mcMoveAbs.Execute := FALSE;
	        #mcMoveVel.Execute := FALSE;
	        #mcStop.Execute := FALSE;
	        
	        // 状态转移检测：
	        // A. 强制回零请求
	        IF #bTrigger_Home THEN
	            #iState := #ST_HOMING;
	            
	        // B. 启动绝对定位 (安全联锁：必须已回零建立坐标，才允许定位！)
	        ELSIF #bTrigger_Abs AND #Axis.StatusWord.X5 THEN
	            #bAxis_Standstill := FALSE;
	            #iState := #ST_MOVING_ABS;
	            
	        // C. 启动恒速运行
	        ELSIF #bTrigger_Vel THEN
	            #bAxis_Standstill := FALSE;
	            #iState := #ST_MOVING_VEL;
	            
	        // D. 外部断电
	        ELSIF #bSystem_PowerOff THEN
	            #iState := #ST_OFF;
	        END_IF;
	        
	    #ST_MOVING_ABS:
	        // 动作：驱动高精度定位块
	        // 捕捉 bTrigger_Abs 上升沿触发定位
	        IF #bTrigger_Abs AND NOT #bStartAbs_FP THEN
	            #mcMoveAbs.Position := #rTarget_Position;
	            #mcMoveAbs.Velocity := #rTarget_Velocity;
	            #mcMoveAbs.Execute := TRUE; // 触发上升沿
	        END_IF;
	        #bStartAbs_FP := #bTrigger_Abs; // 锁存
	        
	        // 跃迁条件：
	        // 1. 轴精准到达目标位置
	        IF #mcMoveAbs.Done THEN
	            #mcMoveAbs.Execute := FALSE;
	            #iState := #ST_STANDSTILL;
	        // 2. 中途按下停止键，强行进入减速刹车
	        ELSIF #bCmd_Stop THEN
	            #mcMoveAbs.Execute := FALSE;
	            #iState := #ST_STOPPING;
	        // 3. 定位发生故障
	        ELSIF #mcMoveAbs.Error THEN
	            #mcMoveAbs.Execute := FALSE;
	            #iState := #ST_FAULT;
	        END_IF;
	        
	    #ST_MOVING_VEL:
	        // 动作：驱动速度运行块
	        IF #bTrigger_Vel AND NOT #bStartVel_FP THEN
	            #mcMoveVel.Velocity := #rTarget_Velocity;
	            #mcMoveVel.Direction := 1; // 1代表正转方向
	            #mcMoveVel.Execute := TRUE;
	        END_IF;
	        #bStartVel_FP := #bTrigger_Vel;
	        
	        // 跃迁条件：
	        // 1. 速度运行没有终点，只要按下停止，进入减速
	        IF #bCmd_Stop OR #bSystem_PowerOff THEN
	            #mcMoveVel.Execute := FALSE;
	            #iState := #ST_STOPPING;
	        ELSIF #mcMoveVel.Error THEN
	            #mcMoveVel.Execute := FALSE;
	            #iState := #ST_FAULT;
	        END_IF;
	        
	    #ST_STOPPING:
	        // 动作：驱动 MC_Stop 块，安全减速刹车
	        #mcStop.Execute := TRUE;
	        
	        // 跃迁条件：轴完全停稳（Axis 实际速度降为 0.0）且 Stop 动作完成
	        IF #mcStop.Done AND #Axis.ActualVelocity = 0.0 THEN
	            #mcStop.Execute := FALSE;
	            #iState := #ST_STANDSTILL;
	        ELSIF #mcStop.Error THEN
	            #mcStop.Execute := FALSE;
	            #iState := #ST_FAULT;
	        END_IF;
	        
	    #ST_FAULT:
	        // 动作：安全保护（复位所有运动指令）
	        #mcPower.Enable := FALSE; // 强行断电去使能，抱闸闭合，保护机械
	        #mcHome.Execute := FALSE;
	        #mcMoveAbs.Execute := FALSE;
	        #mcMoveVel.Execute := FALSE;
	        #bAxis_Power_On := FALSE;
	        #bAxis_Standstill := FALSE;
	        #bOut_Fault := TRUE;
	        
	        // 跃迁条件：一键复位
	        #mcReset.Execute := #bReset;
	        
	        IF #mcReset.Done THEN
	            #mcReset.Execute := FALSE;
	            #bOut_Fault := FALSE;
	            #iState := #ST_OFF; // 报警复位成功，重新回上电起点
	        END_IF;
	        
	    ELSE
	        // 防御自适应
	        #iState := #ST_OFF;
	        
	END_CASE;
	
	// 输出状态步骤码给 HMI 显示
	#iActiveState := #iState;
	
END_FUNCTION_BLOCK
```

---

## 4. 深度解剖实战代码的“运动控制工程美学”

这段 SCL 伺服控制代码，凝聚了现场大型高频定位项目中极高规格的“防错、安全、高性能”设计。

### 4.1 绝对定位前安全回零强制锁（第 91 行）
在 `#ST_STANDSTILL` 状态中，我们写了这一句：
`ELSIF bTrigger_Abs AND Axis.StatusWord.X5 THEN ...`
这是一个绝对不能省去的**安全软件护栏**。
*物理崩溃风险*：如果伺服刚上电（此时坐标是未校准的随机值，比如是 `0`），如果程序不判断 `#Axis.StatusWord.X5`（未建立零位坐标），直接触发 `MC_MoveAbsolute` 去往 `500.0mm` 位置。
伺服可能会认为当前在 0，并全速往一侧狂奔。**这会导致轴直接在高速下撞击物理死挡铁，造成丝杠弯曲、电机外壳碎裂的恶性工业事故！**
**我们将回零（StatusWord.X5）作为绝对定位启动的前提条件，从根本上卡死了这一物理撞机隐患。**

---

### 4.2 运动系统块的“多周期更新扫尾”（第 17~22 行）
在代码最上层，我们写下了：
`#mcPower(Axis := #Axis); #mcMoveAbs(Axis := #Axis); ...`
许多新手写运动控制，喜欢把这些块塞到各自的 `CASE` 状态分支内部去调用。
*致命后果*：
当你把 `#mcMoveAbs` 写在 `#ST_MOVING_ABS` 内部。当定位完成（`Done` 变为 `TRUE`）后，状态机切换到了 `#ST_STANDSTILL`。
由于在 Standstill 状态下，CPU **不再扫码调用 `#mcMoveAbs` 的物理实体**。该块的 `mcMoveAbs.Execute` 指令无法刷新为 `FALSE`。当下一个周期重新启动定位时，**由于块在内部没能捕捉到 `Execute` 从 FALSE 到 TRUE 的“上升沿沿”，定位将直接罢工无法二次起动！**
**我们将所有 `MC_` 块实体放置在最外层无条件刷新，在 CASE 内部只改写它们的输入参数。这是大厂标准库设计中保证运动控制 100% 灵敏不假死的至高心法。**

---

## 5. 常见错误与避坑指南 (Senior Tips)

### 5.1 错误一：误将“手动调试点动”和“自动定位”写成两个完全独立的 FB 背景

有些徒弟写伺服控制，建了两个 FB，一个用来做自动定位（FB_Auto），一个用来做手动点动调试（FB_Manual）。它们共同指向同一个工艺对象轴 `"Axis_1"`。

*致命后果*：
由于这两个 FB 独立运转，它们各自在内部调用了同一个轴的 `MC_Power` 和 `MC_MoveAbsolute`。
当发生网络抖动或逻辑混乱时，**两个 FB 可能会在同一个扫描周期内，分别向轴发送相反的定位方向指令。**
这会导致西门子 TO 工艺对象发生严重的 **“资源冲突错误（CommandAborted）”**，轴会报出故障码并在中途暴死停机，给机械齿轮箱造成极大的扭力冲击。
**运动控制铁律：针对某一个特定的工艺对象轴，整个 PLC 内部有且只能有一个控制 FB。所有的手动点动（JOG）、自动定位、回零逻辑，必须高度内聚在同一个状态机内进行集中资源互锁调度。**

---

### 5.2 错误二：HMI 高频频繁修改绝对定位目标位置导致伺服“频繁重定位抖动”
如果你的伺服在高速移动中，操作员在触摸屏上疯狂、高频地滑动手滑条来调整目标坐标 `#rTarget_Position`。
如果你在 SCL 内部是这样触发定位的：
`mcMoveAbs.Position := rTarget_Position; mcMoveAbs.Execute := TRUE;`
这会导致 `MC_MoveAbsolute` 在每个扫描周期都向伺服驱动器发送“重定位（Re-trigger）”指令。
**由于驱动器内部的电流环和速度环会被频繁打破重新规划曲线，伺服轴会在轨道上发出剧烈的啸叫和卡顿抖动，迅速导致驱动器过载报 F011 故障。**
*高阶防线*：**在定位执行期间（#mcMoveAbs.Busy 为 TRUE），强行锁定输入坐标，绝不允许任何外部数据的实时修改干预。**

---

## 6. 课后练习

请独立思考并完成以下两个具有极高现场调调精度的运动控制练习：

### 练习 1：伺服双轴高速追剪自适应主从轴同步 FB 设计 (MC_GearIn 应用)
在高速切袋机包装线上，从轴（切刀伺服）必须在极短时间内，以绝对 1:1 的位置和速度与主轴（送料皮带轮）进行同步合闸。
请编写一个 SCL **FB**：
*   **输入**：
    *   `MasterAxis` : TO_PositioningAxis (主轴)
    *   `SlaveAxis` : TO_PositioningAxis (从轴)
    *   `bSync_Command` : Bool (一键启动齿轮同步)
*   **工艺动作**：
    *   使用多重背景实例化系统同步块 **`MC_GearIn`**。
    *   当按下同步按钮后，使能从轴，并调用 `MC_GearIn` 将从轴与主轴以 `RatioNumerator` = 1, `RatioDenominator` = 1 (1:1 比例) 强行咬合。
    *   必须确认同步合闸成功（`MC_GearIn.InGear` = TRUE），才输出“追剪同步就绪”标志。

### 练习 2：多点坐标巡航扫描伺服自适应状态机 (高阶 FSM)
在视觉点胶机上，胶枪需要依次前往 3 个不同的坐标点执行点胶动作。
*   **坐标点配方**：`arrPoints : Array[1..3] of Real := [100.0, 250.0, 450.0];`
*   **点胶延时**：在每个点精准停稳后，胶枪通电点胶 500ms（使用多重背景 TON 计时）。
*   请设计出一套高精度、完全自动化的多点巡航 SCL 状态机：自动上电 -> 自动回零 -> 前往点1 -> 停稳点胶500ms -> 前往点2 -> 停稳点胶500ms -> 前往点3 -> 停稳点胶500ms -> 一键高速自动返回原点（0.0mm）。

---

## 总结

这一章，我们彻底征服了西门子 SCL 编程、乃至整个高端装备制造业最耀眼的动力引擎——**伺服轴工艺对象（TO）与标准运动状态机的架构应用**。

我们不仅在软件语法层级掌握了它，更从西门子工艺对象（TO）内部状态字控制字、`MC_` 块多周期异步执行的硬件天机高度，剖析了“必须在最外层无条件刷新运动块物理实体、在 Standstill 静止就绪下严格判断 Homed 状态”的至高设计心法。我们共同设计并手写了一个完全自给自足、集成 5 大核心多重背景运动系统块、拥有 3s 起动预报警和缺油超时诊断的“工业级伺服轴多功能状态机控制功能块”。

请记住，**自动化控制，是在空间的秩序中，驾驭物理能量的流动。用强封装、高闭环、无缝互锁的运动状态机去指挥高精度轴卡死每一个微米的运动节拍，你写的程序才能在万吨机械臂高速飞舞的生产车间里，冷静、有序、坚如磐石。**

下一章，我们将正式进入 SCL 编程中，控制计算机离散时间与物理世界连续时间交互的最核心、最经典，也是各大项目必用的物理级算法演练阵地：**《SCL控制算法一阶低通滤波实现与动态时间常数补偿》**。届时，我将带你跨越模拟量毛刺噪点的物理鸿沟，手把手教你写出大师级的滤波控制算法。

加油，下期见！