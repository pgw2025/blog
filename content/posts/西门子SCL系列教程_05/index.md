---
title: "第五章：SCL 条件判断 IF 语句深入理解"
date: 2026-07-21T09:40:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在前面几章中，我们一起打通了 TIA 博途 SCL 的数据类型和基础运算。现在，我们终于拿到了构建复杂工业逻辑最核心的画笔——**控制流语句（Control Flow Statements）**。"
---


在前面几章中，我们一起打通了 TIA 博途 SCL 的数据类型和基础运算。现在，我们终于拿到了构建复杂工业逻辑最核心的画笔——**控制流语句（Control Flow Statements）**。

在自动化控制中，PLC 的 CPU 必须根据传感器反馈、操作员指令以及系统当前状态，实时做出正确的决策。例如：“如果储罐压力超标，且出料阀关闭，那么立刻关停供料泵并报警。”

这种逻辑判断，在 SCL 中主要通过 **`IF` 语句** 来实现。

很多刚从梯形图（LAD）转过来的徒弟会觉得：`IF` 语句有什么好讲的？不就是“如果……那么……”吗？任何会写代码的人都会用。

但师父想告诉你：**在工业现场，90% 以上的逻辑漏洞、异常自锁、动作不响应甚至是偶发性设备撞车，都和 `IF` 语句的滥用、错误嵌套以及边缘条件遗漏有关。**

今天，我会带你从 CPU 底层执行机制、代码重构美学以及与 梯形图（LAD）对应关系的角度，彻底吃透 `IF` 语句。

---

## 1. IF 语句的底层运行机制

在 TIA 博途中，最基础的 `IF` 语句结构如下：

```scl
IF <条件表达式> THEN
    <执行语句1>;
    <执行语句2>;
END_IF;
```

### 1.1 CPU 是如何执行 IF 语句的？

从底层的汇编指令/机器码级别来看，CPU 执行 `IF` 语句本质上是一组 **条件跳转（Conditional Jump）** 指令。

当你写下：
```scl
IF #bStart THEN
    #bMotor := TRUE;
END_IF;
```

CPU 的执行步骤是：
1.  读取输入映像区中 `#bStart` 的状态。
2.  评估其真假。如果 `#bStart` 为 `FALSE`，CPU 会在硬件层级执行一条类似 `JZ`（Jump if Zero，若为零则跳转）的底层指令，**直接跳过 `#bMotor := TRUE;` 这行代码的内存地址**，直接执行 `END_IF;` 之后的下一条语句。
3.  如果 `#bStart` 为 `TRUE`，则不发生跳转，按顺序执行内部的赋值指令。

**高级性能提示**：这意味着，在 SCL 中，**未激活的条件分支内部的代码是完全不消耗 CPU 计算资源的（因为直接跳过了）**。这与 梯形图（LAD）有很大的不同。在 LAD 中，即使整条支路是不通的，CPU 依然要遍历每一个触点来计算它的逻辑通断状态。因此，合理使用 `IF` 语句可以显著缩短 CPU 的循环扫描时间。

---

## 2. ELSE 与 ELSIF：分流的艺术

工业控制很少有单一条件，我们往往需要处理“非此即彼”或“多选一”的复杂场景。

### 2.1 ELSE 结构（非此即彼）
```scl
IF <条件> THEN
    <语句 A>; // 条件为 TRUE 时执行
ELSE
    <语句 B>; // 条件为 FALSE 时执行
END_IF;
```

#### ⚠️ 致命警告：LAD 转 SCL 的“线圈丢失状态”陷阱
这是初学者最常犯的错误，请拿笔在小本子上记下来。

*   **在 LAD 中**：如果你画了一个常开触点接一个物理输出线圈 `-( )`。当触点闭合，线圈通电（`TRUE`）；当触点断开，线圈**自动失电**（`FALSE`）。
*   **在 SCL 中**：如果你写了下面这段代码：
    ```scl
    // ❌ 极其隐蔽的逻辑漏洞！
    IF #bSensor THEN
        #bValve := TRUE;
    END_IF;
    ```
    当 `#bSensor` 从 `TRUE` 变为 `FALSE` 后，**`#bValve` 依然会保持 `TRUE` 状态，不会自动关闭！**
    *原因*：因为当条件为 `FALSE` 时，CPU 跳过了内部代码。没有代码去改写 `#bValve` 的值，它就会保持上一次的内存状态（类似于自锁锁存）。
    
    *正确写法*：对于必须随条件同步断开的输出，必须写全 `ELSE` 分支：
    ```scl
    //  正确的输出同步写法
    IF #bSensor THEN
        #bValve := TRUE;
    ELSE
        #bValve := FALSE; // 确保传感器不满足时关闭阀门
    END_IF;
    ```

---

### 2.2 ELSIF 结构（多路分支判定）
当有多种互斥的状态需要判定时，我们使用 `ELSIF`。

```scl
IF <条件1> THEN
    <动作1>;
ELSIF <条件2> THEN
    <动作2>;
ELSIF <条件3> THEN
    <动作3>;
ELSE
    <默认动作>;
END_IF;
```

*语法排错注意*：在西门子 SCL 中，拼写是 **`ELSIF`**（没有中间的 `E`），很多写过 C 语言或 Basic 的徒弟经常习惯性地拼写成 `ELSEIF` 或 `ELSE IF`，这会导致博途编译器疯狂报红叉。

**底层执行规则**：`ELSIF` 是有**执行优先级**的。CPU 从上到下依次评估条件，**一旦发现某个条件满足，就会执行其对应的动作，然后立刻跳出整个 IF-END_IF 结构**。即使后面的条件同样满足，它们也永远没有机会被执行。

---

## 3. 多条件合并判断（组合逻辑）

在实际项目中，一个动作的触发往往需要多个传感器同时满足（与），或者满足其中之一（或）。在 SCL 中，我们可以将多个布尔变量通过 `AND`、`OR`、`NOT` 拼接在 `IF` 后面。

```scl
IF #bAutoMode AND #bSafeguardOK AND NOT #bEStop THEN
    #bStartAllowed := TRUE;
END_IF;
```

### 师父的代码美学：拒绝“面条式条件”
如果你在现场看到有工程师写出长达三四行、包含十几个 `AND`、`OR` 的 `IF` 条件：
```scl
// ❌ 让人崩溃的“面条代码”
IF (#bA AND #bB) OR (NOT #bC AND #bD) AND (#bE OR #bF) AND NOT #bG AND #bH THEN
   ...
```
这种代码在现场调试和排故时简直是灾难。

**高级重构手法**：利用临时变量（`VAR_TEMP`）进行逻辑分流。

```scl
//  优雅的重构
#temp_SafetyOK := NOT #bG AND #bH;
#temp_ModeOK   := (#bA AND #bB) OR (NOT #bC AND #bD);
#temp_HardwareOK := #bE OR #bF;

IF #temp_SafetyOK AND #temp_ModeOK AND #temp_HardwareOK THEN
    #bActionAllowed := TRUE;
END_IF;
```
*好处*：调试时，你戴上博途监控眼镜，可以清晰地看到是“安全区故障”、“模式不对”还是“硬件未准备好”，无需在密密麻麻的单行公式中去数括号。

---

## 4. 嵌套 IF（Nested IF）的艺术与克制

在一个 `IF` 内部，可以嵌套另一个 `IF`，这被称为嵌套。

```scl
IF #bAutoMode THEN
    IF #bManualOverride THEN
        #bOutput := FALSE; // 嵌套在 Auto 内部的手动干预
    ELSE
        #bOutput := TRUE;
    END_IF;
END_IF;
```

### ⚠️ 嵌套的致命陷阱：箭形代码（Arrow Code）
很多新手写着写着，代码的缩进就像一支往右射出的箭：

```scl
// ❌ 噩梦般的深层嵌套
IF #bCondition1 THEN
    IF #bCondition2 THEN
        IF #bCondition3 THEN
            IF #bCondition4 THEN
                #bExecute := TRUE;
            END_IF;
        END_IF;
    END_IF;
END_IF;
```
这种结构不仅阅读困难，而且极易漏掉对应分支的 `END_IF`。

**师父的降维打击手法**：
1.  **合并条件**：如果嵌套内部没有任何其他的 `ELSE` 动作，直接用 `AND` 合并条件。
2.  **卫语句（Guard Clauses）/ 提前退出**：利用 `RETURN` 提前截断逻辑。

```scl
//  卫语句重构示范
IF NOT #bCondition1 THEN RETURN; END_IF;
IF NOT #bCondition2 THEN RETURN; END_IF;
IF NOT #bCondition3 THEN RETURN; END_IF;
IF NOT #bCondition4 THEN RETURN; END_IF;

#bExecute := TRUE; // 只有全部通过，才会执行到这里
```

---

## 5. SCL 的 IF 语句与 LAD（梯形图）的直观对应

学会将 LAD 的逻辑形象地转换为 SCL，是快速掌握 SCL 编程的捷径。

### 5.1 LAD 串联（与逻辑）对应 SCL

*   **LAD 表现形式**：两个常开触点串联控制一个线圈。
    ```
    |--[A]--[B]--(Q)--|
    ```
*   **SCL 对应关系**：
    ```scl
    #Q := #A AND #B;  // 这种最基础的连续赋值，甚至不需要用 IF-THEN-ELSE
    ```

### 5.2 LAD 并联（或逻辑）对应 SCL

*   **LAD 表现形式**：两个常开触点并联控制一个线圈。
    ```
    |--+--[A]--+--(Q)--|
    |  +--[B]--+       |
    ```
*   **SCL 对应关系**：
    ```scl
    #Q := #A OR #B;
    ```

### 5.3 LAD 保持回路（自锁）对应 SCL

*   **LAD 表现形式**：经典的起动、停止、自锁电路。
    ```
    |--+--[Start]--+--[/Stop]--(Run)--|
    |  +--[ Run ]--+                  |
    ```
*   **SCL 对应关系**（有两种写法，强烈建议使用第一种纯代数赋值写法）：
    ```scl
    // 写法 1：单行无 IF 逻辑（性能最高，最不易产生未定义赋值）
    #Run := (#Start OR #Run) AND NOT #Stop;
    
    // 写法 2：使用 IF-THEN-ELSE
    IF #Start THEN
        #Run := TRUE;
    ELSIF #Stop THEN
        #Run := FALSE;
    END_IF;
    ```

---

## 6. 五大经典工业级实战案例

现在，我们把所有的条件判断机制融会贯通，应用到 5 个真实的工业现场场景中。

---

### 案例 1：多泵联动全自动供水泵站联锁保护控制 (多条件判定 + ELSE 安全防错)

**场景描述**：
某化工园区供水站有两台主泵。需要设计一套联锁启停程序。
*   **启动条件（必须同时满足）**：
    1.  控制模式处于自动状态（`bAutoMode`）。
    2.  蓄水池液位高于安全下限（`bLevelHighEnough`）。
    3.  系统没有紧急停止信号（`bEStopActive` 为 FALSE）。
    4.  出水口排气阀处于完全打开状态（`bAirValveOpened`）。
*   **安全保护（任意一条触发立刻停机，即使不在自动模式下）**：
    *   蓄水池液位极低（`bLevelTooLow`）。
    *   主管道压力超高（`bPressureOverHigh`）。

#### 块接口声明：
```
VAR_INPUT
    bAutoMode : Bool;          // 自动模式
    bLevelHighEnough : Bool;   // 液位高于启动下限
    bEStopActive : Bool;       // 急停激活
    bAirValveOpened : Bool;    // 排气阀打开
    bLevelTooLow : Bool;       // 液位极低（保护）
    bPressureOverHigh : Bool;  // 压力超高（保护）
    bStartRequest : Bool;      // 操作员/MES 启动请求
END_VAR

VAR_OUTPUT
    bPumpRunning : Bool;       // 泵运行输出
    wStatusWord : Word;        // 状态字输出（用于 HMI 显示报警）
END_VAR
```

#### SCL 代码实现：
```scl
FUNCTION "FC_PumpStationCtrl" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 无条件安全保护逻辑（高优先级）
	// ==========================================
	IF #bEStopActive OR #bLevelTooLow OR #bPressureOverHigh THEN
	    #bPumpRunning := FALSE; // 强行关泵
	    
	    // 状态字写入对应的报警码位 (使用上一章学过的 Slice 位寻址)
	    #wStatusWord.X0 := #bEStopActive;
	    #wStatusWord.X1 := #bLevelTooLow;
	    #wStatusWord.X2 := #bPressureOverHigh;
	    RETURN; // 退出，不允许执行后续任何启动判定
	ELSE
	    // 清除报警位
	    #wStatusWord.X0 := FALSE;
	    #wStatusWord.X1 := FALSE;
	    #wStatusWord.X2 := FALSE;
	END_IF;
	
	// ==========================================
	// 2. 自动启动联锁逻辑
	// ==========================================
	IF #bAutoMode THEN
	    // 评估启动联锁是否全部通过
	    IF #bLevelHighEnough AND #bAirValveOpened AND #bStartRequest THEN
	        #bPumpRunning := TRUE;
	        #wStatusWord.X3 := TRUE; // 标记泵处于自动运行状态
	    ELSE
	        #bPumpRunning := FALSE; // 联锁断开，安全关泵
	        #wStatusWord.X3 := FALSE;
	    END_IF;
	ELSE
	    // 如果切出了自动模式，无条件关泵
	    #bPumpRunning := FALSE;
	    #wStatusWord.X3 := FALSE;
	END_IF;
	
END_FUNCTION
```

---

### 案例 2：重油加热器三段加热带温区阶梯式控制 (ELSIF 多路分支)

**场景描述**：
重油燃烧器在点火前，必须对重油进行加热以降低粘度。系统配有三组电加热器（功率各占 33%）。
我们根据当前实际温度（`rActualTemp`）与设定温度（`rSetPointTemp`）之间的温度偏差 $E = T_{set} - T_{act}$，实行阶梯式控制：
1.  当 $E > 15.0$°C 时：温差极大，开启全部三组加热器（1、2、3 全部启动）。
2.  当 $15.0 \ge E > 5.0$°C 时：温差中等，开启两组加热器（1、2 启动，3 停止）。
3.  当 $5.0 \ge E > 1.0$°C 时：温差较小，开启一组加热器（1 启动，2、3 停止）。
4.  当 $E \le 1.0$°C 时：温差极小，全关以防超调（全部停止）。

#### 块接口声明：
```
VAR_INPUT
    rActualTemp : Real;        // 实际重油温度
    rSetPointTemp : Real;      // 设定目标温度
END_VAR

VAR_OUTPUT
    bHeater_Stage1 : Bool;     // 1号加热器线圈
    bHeater_Stage2 : Bool;     // 2号加热器线圈
    bHeater_Stage3 : Bool;     // 3号加热器线圈
    rPowerOutput_Percent : Real; // 实际加热总输出百分比 (%)
END_VAR

VAR_TEMP
    rTempDeviation : Real;     // 温度偏差 E
END_VAR
```

#### SCL 代码实现：
```scl
FUNCTION "FC_HeaterCascadeCtrl" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// 计算偏差
	#rTempDeviation := #rSetPointTemp - #rActualTemp;
	
	// ==========================================
	// 使用 ELSIF 多路阶梯式匹配
	// ==========================================
	IF #rTempDeviation > 15.0 THEN
	    // 第一档：全开
	    #bHeater_Stage1 := TRUE;
	    #bHeater_Stage2 := TRUE;
	    #bHeater_Stage3 := TRUE;
	    #rPowerOutput_Percent := 100.0;
	    
	ELSIF #rTempDeviation > 5.0 THEN
	    // 第二档：开两组
	    #bHeater_Stage1 := TRUE;
	    #bHeater_Stage2 := TRUE;
	    #bHeater_Stage3 := FALSE; // 显式关闭，防锁死
	    #rPowerOutput_Percent := 66.6;
	    
	ELSIF #rTempDeviation > 1.0 THEN
	    // 第三档：开一组
	    #bHeater_Stage1 := TRUE;
	    #bHeater_Stage2 := FALSE;
	    #bHeater_Stage3 := FALSE;
	    #rPowerOutput_Percent := 33.3;
	    
	ELSE
	    // 目标到达或超调：全关
	    #bHeater_Stage1 := FALSE;
	    #bHeater_Stage2 := FALSE;
	    #bHeater_Stage3 := FALSE;
	    #rPowerOutput_Percent := 0.0;
	END_IF;
	
END_FUNCTION
```

---

### 案例 3：三轴直角坐标机械手安全工作包络区校验 (深层嵌套 IF)

**场景描述**：
一台在锂电池涂布线上运行的三轴直角坐标桁架机械手（XYZ 轴）。
*   为了防止机械手撞毁通道旁的物理检测探针，我们划定了一个物理**危险软限位包络区**。
*   **限位要求**：如果机械手在 Z 轴未退回安全高度（`rActual_Z` $< 200.0$ mm）的情况下，强行进入危险温区 X轴（$100.0 \sim 500.0$ mm）和 Y轴（$150.0 \sim 350.0$ mm）的交界包络区。
*   **控制决策**：如果机械手强行闯入，程序必须立刻使能防撞急停输出，并将运行速度限制在 5% 的低速爬行安全档。

#### 块接口声明：
```
VAR_INPUT
    rActual_X : Real;          // 机械手 X 轴当前位置 (mm)
    rActual_Y : Real;          // 机械手 Y 轴当前位置 (mm)
    rActual_Z : Real;          // 机械手 Z 轴当前位置 (mm)
    bAutoRunning : Bool;       // 机械手处于自动运行中
END_VAR

VAR_OUTPUT
    bSafetyStop : Bool;        // 安全防撞刹车（急停）输出
    bLowSpeedLimit : Bool;     // 速度限制输出（爬行档）
END_VAR
```

#### SCL 代码实现：
```scl
FUNCTION "FC_RobotEnvelopCheck" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// 默认状态初始化：安全、正常速度
	#bSafetyStop := FALSE;
	#bLowSpeedLimit := FALSE;
	
	// ==========================================
	// 使用嵌套 IF 剥洋葱式地检测危险状态
	// ==========================================
	IF #bAutoRunning THEN
	    // 第一层：判断 Z 轴是否未上升到安全高度
	    IF #rActual_Z < 200.0 THEN
	        // 第二层：判断是否闯入 X 轴禁区
	        IF #rActual_X >= 100.0 AND #rActual_X <= 500.0 THEN
	            // 第三层：判断是否同时闯入 Y 轴禁区
	            IF #rActual_Y >= 150.0 AND #rActual_Y <= 350.0 THEN
	                // 所有的条件均已满足：进入了危险立体包络空间！
	                #bSafetyStop := TRUE; // 启动防撞急停
	                #bLowSpeedLimit := TRUE; // 强制降速
	            END_IF;
	        END_IF;
	    END_IF;
	END_IF;
	
END_FUNCTION
```

---

### 案例 4：包装线废品分拣气缸自适应路径路由逻辑 (多条件组合判定)

**场景描述**：
物流输送线上，视觉检测相机对药盒进行外观检测。
*   当检测到不合格品时，相机会给 PLC 发送触发信号（`bRejectTrigger`）。
*   **气缸路由动作**：
    *   如果药盒是“严重物理破损”（`bDefect_Severe`），且分拣气缸 A 处于完全缩回（安全）位置（`bCylinderA_Retracted`），那么启动气缸 A（`bAction_CylinderA` := TRUE）将药盒推入废料箱 A。
    *   如果药盒只是“标签轻微偏移”（`bDefect_Label`），且此时分拣气缸 B 就绪（`bCylinderB_Retracted`），则启动气缸 B 将药盒推入人工返修区 B。
    *   如果两气缸均发生报警故障（`bCylinder_Alarm`），则立即暂停整条主输送带（`bConveyorRun` := FALSE）。

#### 块接口声明：
```
VAR_INPUT
    bRejectTrigger : Bool;     // 相机抓拍判定信号
    bDefect_Severe : Bool;     // 严重破损缺陷
    bDefect_Label : Bool;      // 标签轻微偏移缺陷
    bCylinderA_Retracted : Bool; // 1号分拣气缸处于缩回原位
    bCylinderB_Retracted : Bool; // 2号分拣气缸处于缩回原位
    bCylinder_Alarm : Bool;    // 气缸硬件故障汇总
END_VAR

VAR_OUTPUT
    bAction_CylinderA : Bool;  // 1号分拣气缸电磁阀驱动
    bAction_CylinderB : Bool;  // 2号分拣气缸电磁阀驱动
    bConveyorRun : Bool;       // 输送线电机运行输出
END_VAR
```

#### SCL 代码实现：
```scl
FUNCTION "FC_SorterRouting" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// 默认状态设置：输送线默认保持运行
	#bConveyorRun := NOT #bCylinder_Alarm;
	
	// ==========================================
	// 组合逻辑判定
	// ==========================================
	IF #bCylinder_Alarm THEN
	    // 硬件故障，强制复位所有执行电磁阀，停输送线
	    #bAction_CylinderA := FALSE;
	    #bAction_CylinderB := FALSE;
	    RETURN; 
	END_IF;
	
	// 仅在相机拍到废品触发时进行路由决策
	IF #bRejectTrigger THEN
	    
	    // 分支 1：严重缺陷处理
	    IF #bDefect_Severe AND #bCylinderA_Retracted THEN
	        #bAction_CylinderA := TRUE;
	        #bAction_CylinderB := FALSE; // 互锁，禁止气缸 B 误动
	        
	    // 分支 2：标签轻微缺陷处理
	    ELSIF #bDefect_Label AND #bCylinderB_Retracted THEN
	        #bAction_CylinderA := FALSE;
	        #bAction_CylinderB := TRUE;
	        
	    // 防御分支：如果是未知缺陷，或分拣气缸被占用，安全策略是停线等待，防夹爆
	    ELSE
	        #bConveyorRun := FALSE; 
	        #bAction_CylinderA := FALSE;
	        #bAction_CylinderB := FALSE;
	    END_IF;
	    
	ELSE
	    // 无废品通过时，分拣气缸复位回原位
	    #bAction_CylinderA := FALSE;
	    #bAction_CylinderB := FALSE;
	END_IF;
	
END_FUNCTION
```

---

### 案例 5：轴承稀油站低油压报警防抖与声光报警控制 (LAD 转换 SCL + 定时器集成)

**场景描述**：
我们在大功率电机控制中，必须对轴承箱的稀油润滑站进行监视。这是一个将复杂 LAD 经典电路（起保停 + 硬件故障自锁 + 闪烁定时器 + 警铃延时防抖）重构成精炼 SCL 的典型代表。
*   **控制工艺**：
    1.  当压力传感器检测到油压低信号（`bOilPressure_Low`）时，不能立即报警，必须**持续低压达 3 秒**（防抖过滤，使用 `TON` 定时器），以排除由于管道瞬间空气气泡引起的误报。
    2.  确认低压后，**锁定**报警标志（`bAlarm_Locked`）。此时，声光报警灯闪烁（`bLight_Flash`），电铃报警（`bBell_Active`）。
    3.  操作员按下“消音”按钮（`bMute`），电铃熄灭，但报警闪烁灯保持常亮，直到压力恢复正常，且操作员按下“复位”按钮（`bReset`）后，报警全部解除。

#### 块接口声明（FB_LubricationAlarm）：
该块包含计时器，所以必须采用 **FB**。

```
VAR_INPUT
    bOilPressure_Low : Bool;   // 压力过低传感器输入
    bMute : Bool;              // 消音按钮
    bReset : Bool;             // 报警复位按钮
    bPulse_1Hz : Bool;         // 系统自带时钟脉冲（用于闪烁）
END_VAR

VAR_OUTPUT
    bLight_Output : Bool;      // 指示灯输出
    bBell_Output : Bool;       // 电铃报警输出
END_VAR

VAR
    // 定时器多重背景实例化
    tonDelay {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME;
    bAlarm_Locked : Bool;      // 报警自锁状态静态变量
    bBell_Muted : Bool;        // 电铃已消音标志静态变量
END_VAR
```

#### SCL 代码实现：
```scl
FUNCTION_BLOCK "FB_LubricationAlarm"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 低油压 3s 延时防抖过滤
	// ==========================================
	#tonDelay(IN := #bOilPressure_Low,
	          PT := T#3s);
	
	// ==========================================
	// 2. 故障自锁逻辑 (类似于 LAD 的自锁起保停电路)
	// ==========================================
	IF #tonDelay.Q THEN
	    #bAlarm_Locked := TRUE; // 锁定报警状态
	END_IF;
	
	// 解锁判定
	IF #bReset AND NOT #bOilPressure_Low THEN
	    #bAlarm_Locked := FALSE; // 只有在压力恢复，且按下复位时，才能清除锁定的报警
	    #bBell_Muted := FALSE;   // 重置消音标志
	END_IF;
	
	// ==========================================
	// 3. 电铃消音与驱动逻辑
	// ==========================================
	IF #bAlarm_Locked THEN
	    // 响应消音按钮
	    IF #bMute THEN
	        #bBell_Muted := TRUE;
	    END_IF;
	    
	    // 驱动电铃输出：有报警，且未按下消音
	    #bBell_Output := NOT #bBell_Muted;
	    
	    // 驱动指示灯输出：报警锁定时，如果消音了，灯常亮；如果未消音，灯闪烁
	    IF #bBell_Muted THEN
	        #bLight_Output := TRUE; // 常亮表示已确认
	    ELSE
	        #bLight_Output := #bPulse_1Hz; // 闪烁提醒
	    END_IF;
	    
	ELSE
	    // 无报警，全部复位
	    #bBell_Output := FALSE;
	    #bLight_Output := FALSE;
	END_IF;
	
END_FUNCTION_BLOCK
```

---

## 7. 常见错误与避坑指南 (Senior Tips)

### 7.1 拼写与标点符号错误
SCL 是严格以分号 `;` 结尾的。
*   `IF` 条件后面是 `THEN`，**不要加分号**。
*   `ELSE` 后面**不要加分号**。
*   `END_IF` 后面**必须加分号**。

```scl
// ❌ 错误示范
IF #bStart; THEN  // 错误 1：THEN 前加了分号
    #bOut := TRUE;
ELSE;             // 错误 2：ELSE 后加了分号
    #bOut := FALSE;
END_IF            // 错误 3：END_IF 漏了分号
```

### 7.2 单一分支导致的状态滞留（遗漏 ELSE）
如 2.1 节所述，在需要做物理输出驱动时，切记要考虑条件不满足时的处理。
如果你的变量是 `VAR_OUTPUT` 或者是全局 DB 变量，**一旦你漏掉了 `ELSE`，这个变量就会变成一个隐形的“锁存器”，在外界条件消失后依然保持最后状态。**

---

## 8. 课后练习

请独立思考并完成以下两个经典现场练习：

### 练习 1：双轴伺服门架同步防扭偏联锁
双伺服驱动的高速门架（X1轴，X2轴）在并排运行时，两轴的位置偏差（绝对值）绝对不能大于 $2.0$ mm，否则会导致龙门架发生严重的物理结构扭歪，从而报废。
请编写一个 SCL FC：
*   **输入**：
    *   `rPos_X1` (Real)：1轴实时物理位置 (mm)
    *   `rPos_X2` (Real)：2轴实时物理位置 (mm)
    *   `bServo_Enabled` (Bool)：伺服处于使能运行状态
*   **输出**：
    *   `bSynchronize_Error` (Bool)：报警输出（当偏差 $> 2.0$ mm 且处于使能状态时输出）
    *   `bStop_Trigger` (Bool)：紧急刹车断电动作线圈

### 练习 2：多级冷却风扇智能节能顺序启停控制
为了给变频器柜降温，柜内装有 3 台轴流冷却风扇。我们根据主柜内的实时温度（`rInverterTemp`）进行节能控制：
1.  温度 $\le 35.0$°C：风扇全部停止。
2.  $35.0\text{°C} <$ 温度 $\le 45.0$°C：仅启动 1 号风扇。
3.  $45.0\text{°C} <$ 温度 $\le 55.0$°C：启动 1、2 号风扇。
4.  温度 $> 55.0$°C：由于温度极高，3台风扇全部开满，并发出“高温预警”布尔信号。
*   **附加挑战**：当温度从高处下跌通过临界点时，为了防止温度在 $45.0$°C 边缘轻微波动导致 2 号风扇频繁启停，引入 $1.0$°C 的**滞后回差（Deadband）**。即：启动 2 号风扇需要温度跌破 $44.0$°C 时，才允许关闭。

---

## 总结

这一章，我们彻底征服了 SCL 语言中威力和使用频次最高的核心——`IF` 条件判断控制。

我们不仅理解了它在 CPU 底层通过“条件跳转”优化执行效率的硬件逻辑，也解剖了诸如“LAD 转 SCL 状态遗漏”和“箭形嵌套代码”等工程毒瘤的深层根源。更通过 5 个涵盖多泵站联锁、阶梯电加热、机械手安全区校验、废品路由以及低油压自锁闪烁报警的综合实战案例，打通了你将工艺转化为纯文本逻辑的思维脉络。

请记住，**高超的逻辑控制，不在于你写了多少层复杂的 IF，而在于你如何克制地利用 ELSE、卫语句和组合逻辑，把一个充满未知的工艺现场约束得稳健如磐石。**

下一章，我们将跨入 SCL 控制流中的另一个核心：**《SCL多路分支CASE语句完全手册》**。届时，我将带你见识如何用它写出极具艺术感的状态机（State Machine），彻底告别乱如麻的 `IF-ELSE` 条件嵌套。

加油，下期见！