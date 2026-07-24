---
title: "第六章：SCL 中的 CASE 语句与有限状态机（FSM）"
date: 2026-07-21T09:50:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上两章中，我们一起攻克了 SCL 中的运算和 `IF` 条件分支。你现在应该能够游刃有余地写出各种互锁、安全判定逻辑了。"
---

在上两章中，我们一起攻克了 SCL 中的运算和 `IF` 条件分支。你现在应该能够游刃有余地写出各种互锁、安全判定逻辑了。

但是，随着项目的变大，你很快就会迎来 PLC 编程中最核心、最棘手的挑战——**顺序控制（Sequential Control）**。

在工厂里，绝大多数设备都是一步一步动作的。比如一台包装机：“第一步：气缸下压；第二步：热吸塑加热 2 秒；第三步：气缸退回；第四步：输送带送出。”

如果用 `IF-ELSIF` 或者梯形图（LAD）里的无数个中间标志位（如 `M10.0`、`M10.1`）去写这种顺序步序，你很快就会陷入“到底是哪一步没满足”、“为什么动作卡住不走”、“为什么有两个动作同时输出”的泥潭中。

今天，师父带你学习 SCL 语言中的“终极武器”——**`CASE` 语句**，并向你传授大厂标准级设计的核心思想：**有限状态机（Finite State Machine, FSM）**。

掌握了这一章的精髓，你就能把复杂、冗长、易出错的设备动作，重构为像流水一样清晰、绝对不会发生“步序冲突”的高质量程序。

---

## 1. CASE 语句的语法与底层物理机理

`CASE` 语句是西门子 SCL 中用于处理 **“多路分支选择”** 的标准语法结构。它允许我们根据一个**整型（Int/Dint/Byte 等）选择器变量**的值，直接跳转到对应的代码块执行。

### 1.1 基础语法结构

```scl
CASE <选择器变量> OF
    <数值1>:
        <代码块1>; // 当选择器变量 = 数值1 时执行
    <数值2, 数值3>:
        <代码块2>; // 当选择器变量 = 数值2 或 数值3 时执行
    <数值4..数值5>:
        <代码块3>; // 当选择器变量在 数值4 到 数值5 范围内（闭区间）时执行
    ELSE
        <默认代码块>; // 当选择器变量不满足以上任何值时执行
END_CASE;
```

*语法精要*：
1.  **选择器变量**必须是整型或字符型（如 `Int`, `DInt`, `Byte`, `Char`），绝对不能是浮点数 `REAL`。
2.  **`ELSE` 分支** 虽然是可选的，但师父强烈建议你**无条件写上**。当程序由于电磁干扰、人为强置导致选择器变量变成了一个非法值时，`ELSE` 是你最安全的防线。

---

### 1.2 💡 编译器的底层秘密：跳转表（Jump Table）

有些徒弟会问：“师父，我用 `IF-ELSIF-ELSIF` 也能实现同样的选择，为什么要用 `CASE` 呢？”

除了可读性外，最底层的区别在于**执行效率**。

*   **`IF-ELSIF` 的执行机制**：
    CPU 必须从上到下逐个进行逻辑比较。如果你的第 50 个 `ELSIF` 满足，CPU 就必须在前面进行 49 次无谓的对阶和比较计算。算法复杂度是 $O(N)$。

*   **`CASE` 的执行机制**：
    当选择器的数值分布比较紧密时，博途编译器会将 `CASE` 编译成 CPU 硬件级的 **“跳转表（Jump Table）”**。
    CPU 内部会开辟一段连续的指令地址内存。当执行到 `CASE` 时，CPU 直接将“选择器变量的值”作为**索引指针**，一步计算出目标代码的物理地址并直接跳过去（类似于 C 语言中的指针查表）。
    算法复杂度是 **$O(1)$**！无论你写了 10 个步骤还是 100 个步骤，**执行时间完全相同，且极快**。

---

## 2. 有限状态机（FSM）思想：工业控制的黄金法则

在引入案例之前，我们先来聊聊灵魂概念——**有限状态机（FSM）**。

```
              ┌──────────────────────────────────────┐
              │                初始化                │
              └──────────────────┬───────────────────┘
                                 │ 复位成功
                                 ▼
              ┌──────────────────────────────────────┐
    ┌────────>│               0. 待机                │<────────┐
    │         └──────────────────┬───────────────────┘         │
    │                            │ 启动按钮按下                 │
    │                            ▼                             │
    │         ┌──────────────────────────────────────┐         │
    │         │              10. 气缸下压             │         │
    │         └──────────────────┬───────────────────┘         │
    │                            │ 下压到位                    │
    │                            ▼                             │
    │         ┌──────────────────────────────────────┐         │
    │         │             20. 延时加热             │         │
    │         └──────────────────┬───────────────────┘         │
    │                            │ 2秒时间到                   │
    │                            ▼                             │
    │         ┌──────────────────────────────────────┐         │
    │         │              30. 气缸退回             │─────────┘
    │         └──────────────────────────────────────┘ 升起位
```

有限状态机是一种数学模型，用于表示系统在有限个**状态（States）**之间，根据特定的**触发条件（Transitions）**进行跳转的逻辑。

### 2.1 为什么传统的 LAD 步序控制极易出错？

在经典的 LAD 编程中，大家喜欢用“起保停”或 SET/RESET 指令来写步序：
*   第1步：`SET M10.1; RESET M10.0;`
*   第2步：`SET M10.2; RESET M10.1;`

这种设计被称为“分布式状态”。在物理上，内存中可能同时出现 `M10.1` 和 `M10.2` 都为 `TRUE` 的异常情况。这会导致 PLC 同时驱动两个相冲突的物理阀门，从而造成**撞机**。

### 2.2 SCL 状态机的降维打击：唯一真相原则

当我们用 SCL 的 `CASE` 语句构建状态机时，我们定义一个全局或静态的整型变量 `#iState` 来代表当前步骤。
*   `#iState = 0` 代表待机。
*   `#iState = 10` 代表下压。
*   `#iState = 20` 代表加热。

**核心优势**：
1.  **绝对互斥**：在任何一个 CPU 扫描周期，`#iState` 的值只可能是一个。它绝对不可能同时既是 `10` 又是 `20`。这从内存机制上**100%杜绝了多步冲突输出**的安全隐患。
2.  **极易调试**：现场设备卡住时，你只需看一眼 `#iState` 的值（比如等于 `20`），再去看步骤 `20` 的转移条件（比如“定时器时间到”），就能瞬间定位故障。

---

## 3. CASE 替代大量 IF 语句的重构美学

我们来看一段反面教材。很多新手写步序控制，喜欢这样套娃：

```scl
// ❌ 让人窒息的 IF-ELSIF 步序控制写法
IF #bStep0_Active THEN
    IF #bStart THEN
        #bStep0_Active := FALSE;
        #bStep1_Active := TRUE;
    END_IF;
ELSIF #bStep1_Active THEN
    #bCylinderDown := TRUE;
    IF #bSensorDown THEN
        #bStep1_Active := FALSE;
        #bStep2_Active := TRUE;
    END_IF;
END_IF;
```

这段代码不仅难以阅读，还产生了大量的冗余变量（`bStep0_Active`、`bStep1_Active`……）。

### 3.1 师父的规范：使用常数（Constants）消灭“魔术数字（Magic Numbers）”

如果我们在 `CASE` 语句中直接写：
```scl
CASE #iState OF
    0:  // 什么是 0？
        ...
    10: // 什么是 10？
        ...
```
这些 `0`、`10`、`20` 叫做“魔术数字”，过三个月你自己也看不懂。

**大厂编程规范**：在 TIA 博途的 FB/FC 属性或 PLC 变量表中，声明一组 **局部/全局常数（Constants）**，赋予其有物理意义的名称。

| 常数名 | 数据类型 | 默认值 | 注释 |
| :--- | :--- | :--- | :--- |
| `ST_IDLE` | `Int` | `0` | 待机状态 |
| `ST_CYL_DOWN` | `Int` | `10` | 气缸下压状态 |
| `ST_HEATING` | `Int` | `20` | 延时加热状态 |
| `ST_CYL_UP` | `Int` | `30` | 气缸退回状态 |
| `ST_FAULT` | `Int` | `99` | 故障锁定状态 |

这样，我们的 `CASE` 语句就会变得像天书一样清晰易懂：

```scl
//  符合高级工业规范的 SCL 状态机模板
CASE #iState OF
    #ST_IDLE:
        #bCylinderDown := FALSE;
        IF #bStart THEN
            #iState := #ST_CYL_DOWN; // 状态转移
        END_IF;
        
    #ST_CYL_DOWN:
        #bCylinderDown := TRUE;
        IF #bSensorDown THEN
            #iState := #ST_HEATING; // 状态转移
        END_IF;
        
    #ST_HEATING:
        ...
END_CASE;
```

---

## 4. 三大硬核工业实战案例

现在，我们把状态机思想彻底落到实处，手写三个现场最经典的控制程序。

---

### 案例 1：地铁式高安全性自动感应平移门系统 (CASE 基础应用)

**场景描述**：
控制一个地铁站或商场的全自动平移感应门。
*   **状态分布**：
    *   `0 (ST_CLOSED)`：门完全关闭并上锁。
    *   `10 (ST_OPENING)`：门正在开启。
    *   `20 (ST_OPENED_WAIT)`：门完全打开，并停留等待 5 秒，供人员通过。
    *   `30 (ST_CLOSING)`：门正在关闭。
    *   `40 (ST_SAFETY_REVERSE)`：防夹保护反转。在关门过程中，若安全光幕被遮挡，门必须立刻停止关门并重新开启。
    *   `90 (ST_FAULT)`：门发生卡阻、传感器丢失等故障，红灯闪烁。

#### 块接口声明（FB_AutoDoor）：
因为需要使用系统定时器记录关门等待时间，所以采用 **FB** 结构。

```
VAR_INPUT
    bSensor_Radar : Bool;      // 雷达感应（有人靠近）
    bSensor_Opened : Bool;     // 门完全打开限位
    bSensor_Closed : Bool;     // 门完全关闭限位
    bLightCurtain_Blocked : Bool; // 安全光幕防夹阻挡信号
    bReset : Bool;             // 故障复位
END_VAR

VAR_OUTPUT
    bMotor_Open : Bool;        // 电机开门驱动
    bMotor_Close : Bool;       // 电机关门驱动
    bLock_Signal : Bool;       // 电磁锁上锁控制信号
    bAlarm_RedLight : Bool;    // 报警指示灯
END_VAR

VAR
    iState : Int := 0;         // 当前运行状态静态变量
    tonWaitOpened {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME; // 开门等待5s定时器
    tonWatchdog {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME;   // 动作超时监控（防卡阻）
END_VAR

VAR_CONST
    ST_CLOSED : Int := 0;
    ST_OPENING : Int := 10;
    ST_OPENED_WAIT : Int := 20;
    ST_CLOSING : Int := 30;
    ST_SAFETY_REVERSE : Int := 40;
    ST_FAULT : Int := 90;
END_VAR
```

#### SCL 代码实现：

```scl
FUNCTION_BLOCK "FB_AutoDoor"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 系统超时看门狗定时器 (防电机堵转烧毁)
	// 如果开门或关门动作持续超过 10 秒仍未到达限位，强行切入故障状态
	// ==========================================
	#tonWatchdog(IN := (#iState = #ST_OPENING OR #iState = #ST_CLOSING),
	             PT := T#10s);
	             
	IF #tonWatchdog.Q THEN
	    #iState := #ST_FAULT; // 触发超时故障
	END_IF;
	
	// ==========================================
	// 2. 核心状态机控制逻辑
	// ==========================================
	CASE #iState OF
	        
	    #ST_CLOSED:
	        // 动作：关闭电机，使能电磁锁
	        #bMotor_Open := FALSE;
	        #bMotor_Close := FALSE;
	        #bLock_Signal := TRUE;
	        #bAlarm_RedLight := FALSE;
	        
	        // 转移条件：雷达感应到人，释放锁并开门
	        IF #bSensor_Radar THEN
	            #bLock_Signal := FALSE;
	            #iState := #ST_OPENING;
	        END_IF;
	        
	    #ST_OPENING:
	        // 动作：驱动开门电机
	        #bMotor_Open := TRUE;
	        #bMotor_Close := FALSE;
	        
	        // 转移条件：开门到位限位触发
	        IF #bSensor_Opened THEN
	            #iState := #ST_OPENED_WAIT;
	        END_IF;
	        
	    #ST_OPENED_WAIT:
	        // 动作：停止电机，启动 5 秒等待计时器
	        #bMotor_Open := FALSE;
	        #bMotor_Close := FALSE;
	        
	        #tonWaitOpened(IN := TRUE, PT := T#5s);
	        
	        // 转移条件：
	        // 1. 如果在等待期间雷达持续感应到人，重置定时器
	        IF #bSensor_Radar THEN
	            #tonWaitOpened(IN := FALSE, PT := T#5s); // 复位定时器重新计时
	        END_IF;
	        
	        // 2. 5 秒时间到，且没人，开始关门
	        IF #tonWaitOpened.Q THEN
	            #tonWaitOpened(IN := FALSE, PT := T#5s); // 关闭定时器
	            #iState := #ST_CLOSING;
	        END_IF;
	        
	    #ST_CLOSING:
	        // 动作：驱动关门电机
	        #bMotor_Open := FALSE;
	        #bMotor_Close := TRUE;
	        
	        // 转移条件：
	        // 1. 关门期间如果光幕被挡住，立刻紧急反转开门
	        IF #bLightCurtain_Blocked THEN
	            #iState := #ST_SAFETY_REVERSE;
	        // 2. 关门完全到位
	        ELSIF #bSensor_Closed THEN
	            #iState := #ST_CLOSED;
	        END_IF;
	        
	    #ST_SAFETY_REVERSE:
	        // 动作：紧急停止关门，全速反向开门
	        #bMotor_Open := TRUE;
	        #bMotor_Close := FALSE;
	        
	        // 转移条件：开门到位后，重新进入等待状态
	        IF #bSensor_Opened THEN
	            #iState := #ST_OPENED_WAIT;
	        END_IF;
	        
	    #ST_FAULT:
	        // 动作：安全断电，报警指示
	        #bMotor_Open := FALSE;
	        #bMotor_Close := FALSE;
	        #bLock_Signal := FALSE;
	        #bAlarm_RedLight := TRUE;
	        
	        // 转移条件：按下复位按钮，且门回到初始安全位置，尝试进入待机
	        IF #bReset THEN
	            #bAlarm_RedLight := FALSE;
	            #iState := #ST_CLOSED;
	        END_IF;
	        
	    ELSE
	        // 防御性异常补漏
	        #iState := #ST_FAULT;
	        
	END_CASE;
	
END_FUNCTION_BLOCK
```

---

### 案例 2：三轴取放料直角坐标机械手步序控制 (带防卡死监控状态机)

**场景描述**：
控制一个在流水线上抓取电芯到托盘的机械手。
*   **动作步骤**：
    1.  机械手在原点，等待输送带电芯到位。
    2.  Z轴下行，直到抓取位传感器触发。
    3.  吸盘电磁阀通电，气压表反馈真空度OK（抓取成功）。
    4.  Z轴上行，直到高位限位触发。
    5.  X轴横移，直到放料位限位触发。
    6.  Z轴再次下行。
    7.  吸盘断电，并向电磁阀吹气 0.5s（快速脱料）。
    8.  Z轴、X轴复位回原点，完成一次循环。

#### 块接口声明（FB_GantryManipulator）：
```
VAR_INPUT
    bStart_Cycle : Bool;       // 启动单次循环请求
    bPart_Present : Bool;      // 物料检测到位传感器
    bZ_Limit_Up : Bool;        // Z 轴上限位
    bZ_Limit_Down : Bool;      // Z 轴下限位
    bX_Limit_Home : Bool;      // X 轴原点限位
    bX_Limit_Work : Bool;      // X 轴工作放料位限位
    bVacuum_OK : Bool;         // 真空吸盘反馈 OK
    bReset : Bool;             // 故障复位
END_VAR

VAR_OUTPUT
    bZ_Move_Up : Bool;         // Z 轴上升输出
    bZ_Move_Down : Bool;       // Z 轴下降输出
    bX_Move_Work : Bool;       // X 轴前行放料输出
    bX_Move_Home : Bool;       // X 轴退回原位输出
    bSucker_On : Bool;         // 吸盘抽真空阀驱动
    bSucker_Blow : Bool;       // 吸盘吹气脱料阀驱动
    bCycle_Done : Bool;        // 单次取放循环完成信号
    bAlarm_Fault : Bool;       // 机械手故障指示
END_VAR

VAR
    iState : Int := 0;         // 步序状态寄存器
    tonBlowTimer {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME; // 吹气释放定时器
    tonTimeout {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME;    // 机械动作超时保护
END_VAR

VAR_CONST
    ST_MAN_HOME : Int := 0;
    ST_MAN_Z_DOWN1 : Int := 10;
    ST_MAN_GRIP : Int := 20;
    ST_MAN_Z_UP1 : Int := 30;
    ST_MAN_X_WORK : Int := 40;
    ST_MAN_Z_DOWN2 : Int := 50;
    ST_MAN_RELEASE : Int := 60;
    ST_MAN_RETURN : Int := 70;
    ST_MAN_FAULT : Int := 99;
END_VAR
```

#### SCL 代码实现：

```scl
FUNCTION_BLOCK "FB_GantryManipulator"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 全局保护看门狗：任何单步动作如果持续超过 8秒 仍未完成，判定机械卡死，进入故障
	// ==========================================
	#tonTimeout(IN := (#iState <> #ST_MAN_HOME AND #iState <> #ST_MAN_FAULT AND #iState <> #ST_MAN_GRIP),
	            PT := T#8s);
	            
	IF #tonTimeout.Q THEN
	    #iState := #ST_MAN_FAULT;
	END_IF;
	
	// ==========================================
	// 2. 状态机
	// ==========================================
	CASE #iState OF
	        
	    #ST_MAN_HOME:
	        // 动作复位
	        #bZ_Move_Up := FALSE;
	        #bZ_Move_Down := FALSE;
	        #bX_Move_Work := FALSE;
	        #bX_Move_Home := FALSE;
	        #bSucker_On := FALSE;
	        #bSucker_Blow := FALSE;
	        #bCycle_Done := FALSE;
	        
	        // 转移条件：满足原点信号，物料到位，且操作员按下启动
	        IF #bX_Limit_Home AND #bZ_Limit_Up AND #bPart_Present AND #bStart_Cycle THEN
	            #iState := #ST_MAN_Z_DOWN1;
	        END_IF;
	        
	    #ST_MAN_Z_DOWN1:
	        // Z轴下行抓料
	        #bZ_Move_Down := TRUE;
	        
	        // 转移条件：Z轴到达下限位
	        IF #bZ_Limit_Down THEN
	            #bZ_Move_Down := FALSE;
	            #iState := #ST_MAN_GRIP;
	        END_IF;
	        
	    #ST_MAN_GRIP:
	        // 打开真空阀吸料
	        #bSucker_On := TRUE;
	        
	        // 转移条件：真空压力表反馈信号OK
	        IF #bVacuum_OK THEN
	            #iState := #ST_MAN_Z_UP1;
	        END_IF;
	        
	    #ST_MAN_Z_UP1:
	        // Z轴携带物料上行
	        #bZ_Move_Up := TRUE;
	        
	        // 转移条件：Z轴到达上限位
	        IF #bZ_Limit_Up THEN
	            #bZ_Move_Up := FALSE;
	            #iState := #ST_MAN_X_WORK;
	        END_IF;
	        
	    #ST_MAN_X_WORK:
	        // X轴横移到放料工位
	        #bX_Move_Work := TRUE;
	        
	        // 转移条件：X轴工作位限位触发
	        IF #bX_Limit_Work THEN
	            #bX_Move_Work := FALSE;
	            #iState := #ST_MAN_Z_DOWN2;
	        END_IF;
	        
	    #ST_MAN_Z_DOWN2:
	        // Z轴下行放料
	        #bZ_Move_Down := TRUE;
	        
	        // 转移条件：Z轴到达下限位
	        IF #bZ_Limit_Down THEN
	            #bZ_Move_Down := FALSE;
	            #iState := #ST_MAN_RELEASE;
	        END_IF;
	        
	    #ST_MAN_RELEASE:
	        // 关闭真空吸附，同时开启电磁阀强力吹气 0.5s，确保脱料成功
	        #bSucker_On := FALSE;
	        #bSucker_Blow := TRUE;
	        
	        #tonBlowTimer(IN := TRUE, PT := T#500ms);
	        
	        // 转移条件：吹气延时完成
	        IF #tonBlowTimer.Q THEN
	            #tonBlowTimer(IN := FALSE, PT := T#500ms); // 复位定时器
	            #bSucker_Blow := FALSE;
	            #iState := #ST_MAN_RETURN;
	        END_IF;
	        
	    #ST_MAN_RETURN:
	        // X轴原点驱动，Z轴上升驱动，同时返回原点
	        #bX_Move_Home := NOT #bX_Limit_Home;
	        #bZ_Move_Up := NOT #bZ_Limit_Up;
	        
	        // 转移条件：双轴均返回原位
	        IF #bX_Limit_Home AND #bZ_Limit_Up THEN
	            #bX_Move_Home := FALSE;
	            #bZ_Move_Up := FALSE;
	            #bCycle_Done := TRUE; // 报告单周期完成
	            #iState := #ST_MAN_HOME;
	        END_IF;
	        
	    #ST_MAN_FAULT:
	        // 故障锁定：复位所有物理输出，等待人工介入
	        #bZ_Move_Up := FALSE;
	        #bZ_Move_Down := FALSE;
	        #bX_Move_Work := FALSE;
	        #bX_Move_Home := FALSE;
	        #bSucker_On := FALSE;
	        #bSucker_Blow := FALSE;
	        #bAlarm_Fault := TRUE;
	        
	        IF #bReset THEN
	            #bAlarm_Fault := FALSE;
	            #iState := #ST_MAN_HOME; // 重新返回原点待机
	        END_IF;
	        
	    ELSE
	        #iState := #ST_MAN_FAULT;
	END_CASE;
	
END_FUNCTION_BLOCK
```

---

### 案例 3：智能包装线分拣输送系统 (带 MES 数据通信异步交互的状态机)

**场景描述**：
控制一段集成了 RFID 扫码器的包装输送带。
*   **工艺流向**：
    1.  当光电开关检测到托盘流入，输送带停止运行，阻挡气缸升起。
    2.  PLC 触发 RFID 读写头读取托盘上的电子标签数据。
    3.  PLC 拿到 RFID 条码后，通过总线发给上位机（MES）进行工艺路由检索，并**等待 MES 系统应答（Handshake 握手信号）**。
    4.  MES 返回判定数据后（如：0=合格送至包装线；1=废品分流）。
    5.  PLC 根据应答指令，控制分流摆臂气缸动作，释放阻挡气缸，将产品送往对应通道。

#### 块接口声明（FB_SmartSrtConveyor）：
```
VAR_INPUT
    bSensor_Entry : Bool;      // 入口托盘到位传感器
    bRFID_Read_Done : Bool;    // RFID 读写器读取完成完成信号
    sRFID_Barcode : String[20]; // 读回的电芯条码
    bMES_Response_Received : Bool; // MES 应答判定接收完成标志
    iMES_Route_Cmd : Int;      // MES 返回的路由分流代码 (0=合格主线, 1=不合格分流)
    bBypass_MES : Bool;        // 旁路模式（MES断网时，人工全检，全部走主线）
    bReset : Bool;             // 故障复位
END_VAR

VAR_OUTPUT
    bConveyor_Run : Bool;      // 输送带电机运行驱动
    bBlock_Cylinder_Up : Bool; // 阻挡阻挡气缸升起
    bRFID_Trigger : Bool;      // 触发 RFID 扫描信号
    bMES_Request_Trigger : Bool; // 向 MES 申请路由请求脉冲
    bSrt_Arm_Active : Bool;    // 废品分流摆臂气缸驱动
    bAlarm_CommFault : Bool;   // 判定通信超时报警
END_VAR

VAR
    iState : Int := 0;         // 状态寄存器
    tonCommWatchdog {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME; // MES 通信响应 5 秒超时保护
END_VAR

VAR_CONST
    ST_CONV_FREE : Int := 0;       // 输送线自由通行状态
    ST_CONV_STOP : Int := 10;      // 托盘阻挡停止状态
    ST_CONV_READ_RFID : Int := 20; // 读取 RFID 状态
    ST_CONV_MES_REQ : Int := 30;   // 等待 MES 路由反馈状态
    ST_CONV_ROUTING : Int := 40;   // 执行摆臂物理分流行移动状态
    ST_CONV_RELEASE : Int := 50;   // 释放托盘状态
    ST_CONV_FAULT : Int := 90;     // 通信中断故障状态
END_VAR
```

#### SCL 代码实现：

```scl
FUNCTION_BLOCK "FB_SmartSrtConveyor"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 通信延迟守护：
	// 如果在 MES_REQ 状态持续超过 5 秒，MES 系统未返回数据，判定为断网通信故障
	// ==========================================
	#tonCommWatchdog(IN := (#iState = #ST_CONV_MES_REQ),
	                 PT := T#5s);
	                 
	IF #tonCommWatchdog.Q THEN
	    IF NOT #bBypass_MES THEN
	        #iState := #ST_CONV_FAULT; // MES 断网，进入通信故障锁定
	    ELSE
	        // 如果开启了旁路，通信超时不报警，默认当作主线合格产品流走
	        #iState := #ST_CONV_RELEASE; 
	    END_IF;
	END_IF;
	
	// ==========================================
	// 2. 核心状态机
	// ==========================================
	CASE #iState OF
	        
	    #ST_CONV_FREE:
	        // 动作：输送线全速运转，阻挡器降下，所有分流复位
	        #bConveyor_Run := TRUE;
	        #bBlock_Cylinder_Up := FALSE;
	        #bRFID_Trigger := FALSE;
	        #bMES_Request_Trigger := FALSE;
	        #bSrt_Arm_Active := FALSE;
	        
	        // 转移条件：一旦有托盘触及入口传感器
	        IF #bSensor_Entry THEN
	            #iState := #ST_CONV_STOP;
	        END_IF;
	        
	    #ST_CONV_STOP:
	        // 动作：输送线立即停机，阻挡气缸升起截停托盘
	        #bConveyor_Run := FALSE;
	        #bBlock_Cylinder_Up := TRUE;
	        
	        // 转移条件：延迟一小会儿（或物理行程开关就绪），进入扫码
	        #iState := #ST_CONV_READ_RFID;
	        
	    #ST_CONV_READ_RFID:
	        // 动作：向 RFID 读写头发出触发电平
	        #bRFID_Trigger := TRUE;
	        
	        // 转移条件：RFID 读取成功并发出 Done 信号
	        IF #bRFID_Read_Done THEN
	            #bRFID_Trigger := FALSE;
	            #iState := #ST_CONV_MES_REQ;
	        END_IF;
	        
	    #ST_CONV_MES_REQ:
	        // 动作：向 MES 发出网络路由数据包，置位请求标志
	        #bMES_Request_Trigger := TRUE;
	        
	        // 转移条件：收到 MES 应答且数据有效
	        IF #bMES_Response_Received THEN
	            #bMES_Request_Trigger := FALSE;
	            #iState := #ST_CONV_ROUTING;
	        END_IF;
	        
	    #ST_CONV_ROUTING:
	        // 动作：根据 MES 返回的分流指令，进行分拣摆臂气缸的动作决策
	        IF #iMES_Route_Cmd = 1 THEN
	            // 1 代表不合格产品，伸出摆臂物理分流
	            #bSrt_Arm_Active := TRUE;
	        ELSE
	            // 0 代表合格产品，摆臂复位收回，正常走主线
	            #bSrt_Arm_Active := FALSE;
	        END_IF;
	        
	        // 转移条件：摆臂物理动作时间（可使用小延时或传感器）完成，释放托盘
	        #iState := #ST_CONV_RELEASE;
	        
	    #ST_CONV_RELEASE:
	        // 动作：输送线重新启动运行，降下阻挡气缸释放托盘流走
	        #bConveyor_Run := TRUE;
	        #bBlock_Cylinder_Up := FALSE;
	        
	        // 转移条件：托盘完全离开入口传感器，恢复自由通行状态，准备接纳下一个产品
	        IF NOT #bSensor_Entry THEN
	            #iState := #ST_CONV_FREE;
	        END_IF;
	        
	    #ST_CONV_FAULT:
	        // 故障锁定：输送线停机，阻挡器保持锁定，触发声光红灯报警
	        #bConveyor_Run := FALSE;
	        #bBlock_Cylinder_Up := TRUE;
	        #bAlarm_CommFault := TRUE;
	        
	        IF #bReset THEN
	            #bAlarm_CommFault := FALSE;
	            #iState := #ST_CONV_FREE; // 重试，返回待机
	        END_IF;
	        
	    ELSE
	        #iState := #ST_CONV_FREE;
	END_CASE;
	
END_FUNCTION_BLOCK
```

---

## 5. 状态机设计的进阶秘籍与高级避坑指南

写好一个状态机，不仅需要熟练掌握 `CASE` 语法，更需要时刻提防以下两个在调试现场极易让你“抓狂”的底层陷阱。

### 5.1 💡 致命陷阱：定时器在状态切换时的“未复位”假死

这是一个经典的“写状态机必栽跟头”的巨坑。

假设你在步骤 `10`（下压）中，使用了一个标准 `TON` 定时器来延迟 2 秒：
```scl
// ❌ 导致定时器无法二次启动的错误写法
CASE #iState OF
    10:
        #tonDelay(IN := TRUE, PT := T#2s); // 启动延时
        IF #tonDelay.Q THEN
            #tonDelay(IN := FALSE, PT := T#2s); // 尝试复位，随后跳转
            #iState := 20;
        END_IF;
END_CASE;
```

当程序执行到 `#iState := 20;` 之后，在下一个扫描周期，`#iState` 变成了 `20`。
**关键问题来了**：因为 `CASE` 的跳转机制，CPU **不再会执行步骤 10 内部的代码**。因此，底层的 `#tonDelay` 物理块在此刻根本没有被调用。
当你下一次循环再次回到步骤 `10` 时，定时器的输入端 `IN` 会突然看到一个 `TRUE`。但因为中间缺少了一个完整的周期将 `IN` 扫为 `FALSE`，**定时器无法捕捉到从 FALSE 到 TRUE 的上升沿沿变化，导致定时器彻底“假死”，不再开始计时！**

#### 师父教你的高级解法：定时器外置调用
**黄金铁律：千万不要在 `CASE` 分支内部直接去调用定时器的本体！**
正确的做法是：在 `CASE` 分支内只控制一个用于触发定时器的状态标志位（布尔量），而将**定时器的物理块调用放在整个 `CASE` 语句的外面**。

```scl
//  定时器外置优雅写法示范

// 1. 在整个 CASE 外部计算启动条件
#bTimerTrigger := (#iState = #ST_HEATING_STEP); // 仅在特定状态下置真触发

// 2. 在 CASE 外部调用定时器实体（保证每个周期都扫到它的底层时钟数据）
#tonDelay(IN := #bTimerTrigger, PT := T#2s);

// 3. 核心 CASE 结构
CASE #iState OF
    #ST_HEATING_STEP:
        #bHeaterValve := TRUE;
        IF #tonDelay.Q THEN
            // 状态正常转移，iState 变为下一个状态，bTimerTrigger 自动变为 FALSE，定时器安全复位！
            #iState := #ST_NEXT_STEP; 
        END_IF;
END_CASE;
```

### 5.2 绝不允许不加保护的“跳步”

在状态转移时，绝对不能跳过中间的过渡安全条件。例如，在机械手从工作位（Work）返回原点时，必须确保 Z 轴已经升到了安全上限，否则横移会把工装直接撞飞。
```scl
// ❌ 危险的无联锁跳步
#iState := #ST_MAN_RETURN; // 未确认 Z 轴高度，极度危险！

//  安全的联锁跳转
IF #bZ_Limit_Up THEN
    #iState := #ST_MAN_RETURN; // 物理条件闭环，安全放行
END_IF;
```

---

## 6. 课后练习

请独立思考并编写以下两个极富工业现场实战价值的状态机程序。

### 练习 1：智能红绿灯十字路口控制系统 (CASE 练习)
设计一个十字路口的红绿灯控制 FB：
*   **状态分布**：
    *   `ST_NS_GREEN (0)`：南北方向绿灯亮，东西方向红灯亮。维持 30 秒。
    *   `ST_NS_YELLOW (10)`：南北绿灯灭，黄色指示灯闪烁（1Hz 频率）。维持 3 秒。
    *   `ST_EW_GREEN (20)`：东西方向绿灯亮，南北方向红灯亮。维持 20 秒。
    *   `ST_EW_YELLOW (30)`：东西绿灯灭，黄色指示灯闪烁。维持 3 秒。
*   **紧急中断要求**：
    *   输入端配有一个强置紧急按钮 `bEmergency_Active`。当其激活时，状态机必须立刻无视当前步骤，切入状态 `ST_ALL_RED (90)`：所有方向红灯全亮。
    *   当紧急按钮复位后，恢复从初始状态开始运行。

### 练习 2：汽车总装线摩擦输送小车（EMS）滑触式运行控制 (高阶 FSM 应用)
摩擦小车在车身车间的轨道上运行。
*   **物理元件**：
    *   小车配有前行接触器（`bContact_Forward`）和慢速接触器（`bContact_Slow`）。
    *   轨道上有三个物理感应开关：`bSensor_SlowDown`（减速点）、`bSensor_Stop`（停止点）、`bSensor_AntiCollision`（前车防撞传感器，有车靠近时输出 FALSE，代表不安全）。
*   **工艺步骤**：
    *   `0 (ST_PARK)`：小车停止，等待发车按钮 `bStart_Car` 按下。
    *   `10 (ST_HIGH_SPEED)`：全速前行（`bContact_Forward` := TRUE）。
    *   `20 (ST_SLOW_SPEED)`：小车驶过减速点（`bSensor_SlowDown` = TRUE）后，断开高速，进入低速爬行状态（`bContact_Slow` := TRUE）。
    *   `30 (ST_STOP)`：小车驶过停止点后，切断所有接触器，刹车制动上锁。
    *   **安全要求**：
        *   在任何前行状态下（`ST_HIGH_SPEED`、`ST_SLOW_SPEED`），只要前车防撞传感器断开（`bSensor_AntiCollision` = FALSE），小车必须立刻停下，状态切入 `40 (ST_SAFETY_PAUSE)`。
        *   一旦前车离去，安全恢复，小车必须能够自适应“断点续传”，恢复上一步的前行速度。

---

## 总结

这一章，我们彻底征服了 SCL 中分量极重的 `CASE` 语句和有限状态机（FSM）控制技术。

我们不仅理解了 `CASE` 语句在 CPU 底层通过“跳转表”将计算开销降为 $O(1)$ 的优越性能，更深入剖析了状态机如何以“唯一真相原则”从源头上铲除多步冲突和异常自锁的物理逻辑。我们一起手写了涵盖自动感应门、三轴机械手、MES 异步通信分拣输送线三个经典现场控制块。最后，师父向你毫无保留地传授了“定时器在状态跳转中失忆假死”的防坑心法。

请记住，**有限状态机思想是区分初级程序员与高级控制架构师的试金石。用整型指针去驾驭设备的步序，你写的不仅是程序，更是一台精密配合的数字工艺钟表。**

下一章，我们将正式攻克 SCL 控制流中的最后一座大山，也是 SCL 展现出最无情统治力的阵地：**《SCL中的循环语句与大规模数组处理》**。届时，我将带你深入研究 `FOR`、`WHILE` 循环，探讨如何在 PLC 中做大规模数组的高速数据处理，并手把手教你如何防范致命的“CPU看门狗超时停机”事故。

加油，下期见！