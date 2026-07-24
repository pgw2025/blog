---
title: "第二十一章：用 SCL 实现模块化编程与标准气缸通用 FB 模板设计"
date: 2026-07-24T12:40:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们爬上了顺序控制的最高峰——有限状态机（FSM）。你现在已经能够用优雅的 `CASE` 结构去卡死一个复杂包装机的所有工艺节拍了"
---



在上一章中，我们爬上了顺序控制的最高峰——有限状态机（FSM）。你现在已经能够用优雅的 `CASE` 结构去卡死一个复杂包装机的所有工艺节拍了。

但是，当你面对一个拥有上千个 I/O 点、包含上百个气缸、几十个变频器的大型工业项目时，仅靠手写状态机是不够的。如果你依然针对每一个工位、每一个气缸去量身手写一遍控制逻辑，你很快就会陷入 **“拷贝粘贴地狱”**。

在大型工程项目中，电气工程师最核心的价值，不是写了多少行代码，而是**构建了一套高度复用、安全闭环、一键调用的“标准库（Global Library）”**。

这就是我们今天要去攻克的终极关隘——**模块化编程（Modular Programming）**。

在现代 TIA 博途开发体系中，我们利用 **SCL 语言、自定义数据类型（UDT）和功能块（FB）的完美合体**，可以在 PLC 内部模拟出面向对象（OOP）的**“设备对象封装（Device Object Encapsulation）”**。

今天，师父将带你跨入系统架构师的行列。我们将拆解“类似对象思想”的 PLC 落地哲学、数据封装的黑盒子原理，并手写一个在各大汽车、锂电大厂标准库中出镜率最高的黄金模板——**“标准化双作用气缸通用控制功能块（FB）”**。

---

## 1. 类似对象（Object-Like）思想：PLC 里的面向对象折中哲学

在 PC 端（如 C#、C++、Java），面向对象编程（OOP）拥有三大特征：封装、继承、多态。
由于 PLC 承担着毫秒级高确定性的安全控制，且内存（SRAM）极其昂贵，我们无法在 PLC 内部无限制地去动态创建和销毁对象。

因此，工业自动化领域发展出了一套具有 PLC 特色的 **“类似对象（Object-Like）编程哲学”**：

```
                类似对象 (Object-Like) 在博途中的物理映射
                
   PC 端的 OOP 概念                  博途 PLC 中的物理映射
 ┌───────────────────┐             ┌──────────────────────────────────────────────┐
 │   1. 类 (Class)   │    ───>     │  FB (控制算法) + UDT (数据结构)               │
 ├───────────────────┤             ├──────────────────────────────────────────────┤
 │ 2. 实例 (Instance)│    ───>     │  背景 DB (SRAM工作内存中的物理分配)           │
 ├───────────────────┤             ├───────────────────────────────────────────-──┤
 │ 3. 属性 (Property)│    ───>     │  UDT 内部的变量 (如 stCfg.tTimeout)           │
 ├───────────────────┤             ├──────────────────────────────────────────────┤
 │ 4. 方法 (Method)  │    ───>     │  SCL 中的条件执行分支 (如 气缸伸出动作)        │
 └───────────────────┘             └──────────────────────────────────────────────┘
```

### 1.1 类似对象的三大优势
1.  **逻辑高内聚（High Cohesion）**：
    气缸的所有控制动作、超时报警、传感器防抖、模拟手动强制，**全部集中在一个 FB 内部处理**。不向外部世界漏掉任何逻辑碎片。
2.  **数据高封装（Information Hiding）**：
    外部 HMI 或者是主控逻辑不需要知道气缸内部的计时器跑到了多少毫秒，它们只能通过 UDT 接口去读写指令和状态。**设备内部的秘密被牢牢锁在黑盒子里。**
3.  **极速标准化**：
    一旦你的“标准气缸FB”开发完成并存入库（Library）中。现场哪怕有 200 个气缸，你只需要拖放 200 个 FB 实例，**调用时间缩短到几分钟，且 200 个气缸的安全性、可靠性完全一致。**

---

## 2. 标准化设备数据封装模型（以气缸为例）

要做模块化，第一步必须建立**统一的数据接口规范**。

一个大厂级的标准设备 UDT，在数据结构上必须严格遵循**四维模型（控制、反馈、状态、参数）**，且所有子变量名、命名空间必须在全公司项目内严格统一。

现在，我们先在博途“PLC数据类型”中，为气缸建立这套黄金主数据 UDT —— **`UDT_StandardCylinderModel`**：

```scl
// 全局自定义数据类型：标准气缸数据模型
TYPE "UDT_StandardCylinderModel"
VERSION : 0.1
   STRUCT
      Ctrl : STRUCT              // 1. 控制指令层 (Ctrl)
         bAutoMode : Bool;       // 自动/手动模式切换 (TRUE=自动, FALSE=手动)
         bAuto_Extend : Bool;    // 自动模式：指令驱动气缸伸出 (PLC 联锁触发)
         bAuto_Retract : Bool;   // 自动模式：指令驱动气缸缩回
         bHmi_Extend : Bool;     // 手动模式：HMI 按钮触发气缸伸出
         bHmi_Retract : Bool;    // 手动模式：HMI 按钮触发气缸缩回
         bReset : Bool;          // 故障一键复位
      END_STRUCT;
      
      Fbk : STRUCT               // 2. 物理硬件反馈层 (Fbk)
         bSensor_Extended : Bool; // 传感器反馈：气缸已伸出到位 (DI)
         bSensor_Retracted : Bool;// 传感器反馈：气缸已缩回到位 (DI)
         bInterlock_Ok : Bool := TRUE; // 安全工艺联锁条件 (为 FALSE 时，气缸严禁动作)
      END_STRUCT;
      
      Sts : STRUCT               // 3. 运行状态输出层 (Sts)
         bOut_Extend : Bool;     // PLC 物理输出：驱动伸出电磁阀阀 (DO)
         bOut_Retract : Bool;    // PLC 物理输出：驱动缩回电磁阀阀 (DO)
         bExtended : Bool;       // 状态汇总：气缸处于伸出状态
         bRetracted : Bool;      // 状态汇总：气缸处于缩回状态
         bFault : Bool;          // 状态汇总：气缸动作超时卡阻报警
         dwDiagCode : DWord;     // 诊断双字：用于 HMI 画面极速文本显示 (1:过载, 2:伸出超时, 3:缩回超时, 4:双位冲突)
      END_STRUCT;
      
      Cfg : STRUCT               // 4. 工艺参数配置层 (Cfg)
         tExtend_Timeout : Time := T#5s;  // 气缸伸出动作超时设定值
         tRetract_Timeout : Time := T#5s; // 气缸缩回动作超时设定值
         bSimulateMode : Bool;            // 仿真测试模式 (为 TRUE 时，屏蔽物理传感器，内部模拟动作)
      END_STRUCT;
   END_STRUCT;
END_TYPE
```

---

## 3. 标准化设备程序：双作用气缸通用 FB 模板设计

有了 UDT 的数据骨架，现在我们在 SCL 中编写它的大脑——**`FB_StandardCylinder`**。

### 3.1 工业现场气缸控制的灵魂诉求
一个看似简单的气缸，在安全工业生产中必须考虑以下防撞防御设计：
1.  **工艺安全物理联锁（Interlock Protection）**：
    在设备运动前，必须验证 `#stCyl.Fbk.bInterlock_Ok`。
    例如：只有在保护安全门处于完全关闭（`bDoorClosed` = TRUE）的前提下，气缸才允许伸出。如果门开了，气缸无条件停机，防止切断工人的手指。
2.  **双线圈输出互锁（Solenoid Interlock）**：
    双作用气缸配有两个控制线圈。如果“伸出线圈”和“缩回线圈”同时通电，气动阀内部气路会发生混乱，甚至烧毁电磁阀。
    *逻辑要求*：伸出与缩回物理驱动，必须在代码最底层进行**强行互锁**。
3.  **动作超时自锁诊断（Watchdog Timer）**：
    气缸运动（例如伸出）时，如果超过了设定时间（`tExtend_Timeout`，如 5 秒）到位限位依然没有触发。
    *逻辑要求*：必须立刻**切断所有阀门输出（卸载气压）**，锁定汇总故障，防止气阀长时间堵转过热，等待人工确认复位。
4.  **无物理硬件仿真测试（Simulation Mode）**：
    在设备还没运抵现场、或者传感器还没接线期间。如果开启了仿真模式（`bSimulateMode` := TRUE），程序必须在内部用定时器**自动模拟气缸的伸出和缩回动作**。这极大地便于我们在办公室进行全线的离线逻辑联锁测试。

---

### 3.2 步骤一：接口变量区声明（FB_StandardCylinder）

我们在静态区声明多重背景定时器。所有的气缸数据，全部通过 `IN_OUT` 数据引脚传入。

```
VAR_INPUT
    bPulse_1Hz : Bool;          // 用于汇总报警指示灯闪烁
END_VAR

VAR_IN_OUT
    stCyl : "UDT_StandardCylinderModel"; // 核心：整套气缸的物理数据模型
END_VAR

VAR
    // ==========================================
    // 静态变量区 (Private STAT) - 内置多重背景
    // ==========================================
    bRun_Extend_Latch : Bool;   // 手动模式：伸出动作自锁标志
    bRun_Retract_Latch : Bool;  // 手动模式：缩回动作自锁标志
    bFaultActive : Bool;        // 故障锁定状态
    
    // 内置多重背景定时器
    tonExtendWatchdog : TON_TIME;  // 伸出动作超时
    tonRetractWatchdog : TON_TIME; // 缩回动作超时
    tonSimExtend : TON_TIME;       // 仿真模式：模拟伸出时间
    tonSimRetract : TON_TIME;      // 仿真模式：模拟缩回时间
END_VAR

VAR_TEMP
    bActual_Extended : Bool;    // 临时变量：当前实际判定到的伸出限位
    bActual_Retracted : Bool;   // 临时变量：当前实际判定到的缩回限位
END_VAR
```

---

### 3.3 步骤二：SCL 核心代码实现

```scl
FUNCTION_BLOCK "FB_StandardCylinder"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 无条件安全联锁保护与故障一票否决
	// ==========================================
	// 工艺物理联锁判定 (反馈中 stCyl.Fbk.bInterlock_Ok 为 FALSE 代表不具备动作条件)
	IF NOT #stCyl.Fbk.bInterlock_Ok THEN
	    #stCyl.Sts.bOut_Extend := FALSE;
	    #stCyl.Sts.bOut_Retract := FALSE;
	    #bRun_Extend_Latch := FALSE;
	    #bRun_Retract_Latch := FALSE;
	    // 处于安全联锁停机状态，但不锁定故障（一旦联锁恢复，气缸可以重新动作）
	    #stCyl.Sts.dwDiagCode := 16#0000_0001; // 诊断码 1: 物理工艺联锁未通过
	    RETURN; // 极速退出，防止后续动作
	END_IF;
	
	// 如果存在超时锁定故障，强制断电阀门
	IF #bFaultActive THEN
	    #stCyl.Sts.bOut_Extend := FALSE;
	    #stCyl.Sts.bOut_Retract := FALSE;
	END_IF;
	
	// ==========================================
	// 2. 仿真测试模式自适应切换 (Simulation Mode)
	// ==========================================
	// 如果开启了仿真，我们无视真实的 DI 限位，利用内部定时器仿真动作
	IF #stCyl.Cfg.bSimulateMode THEN
	    
	    // 模拟伸出：当输出合闸，延迟 2 秒认为动作到位
	    #tonSimExtend(IN := #stCyl.Sts.bOut_Extend, PT := T#2s);
	    #bActual_Extended := #tonSimExtend.Q;
	    
	    // 模拟缩回
	    #tonSimRetract(IN := #stCyl.Sts.bOut_Retract, PT := T#2s);
	    #bActual_Retracted := #tonSimRetract.Q;
	    
	ELSE
	    // 正常生产模式：读取真实的物理传感器
	    #bActual_Extended := #stCyl.Fbk.bSensor_Extended;
	    #bActual_Retracted := #stCyl.Fbk.bSensor_Retracted;
	END_IF;
	
	// ==========================================
	// 3. 自动与手动控制逻辑 (双线圈底层物理互锁)
	// ==========================================
	IF NOT #bFaultActive THEN
	    
	    // ------------------------------------------
	    // A. 自动模式逻辑 (PLC 自动工艺联锁)
	    // ------------------------------------------
	    IF #stCyl.Ctrl.bAutoMode THEN
	        // 在自动下，PLC 的自动指令决定输出
	        #stCyl.Sts.bOut_Extend := #stCyl.Ctrl.bAuto_Extend AND (NOT #stCyl.Ctrl.bAuto_Retract);
	        #stCyl.Sts.bOut_Retract := #stCyl.Ctrl.bAuto_Retract AND (NOT #stCyl.Ctrl.bAuto_Extend);
	        
	    // ------------------------------------------
	    // B. 手动模式逻辑 (HMI 操作员按钮触发)
	    // ------------------------------------------
	    ELSE
	        // 手动伸出起保停
	        IF #stCyl.Ctrl.bHmi_Extend THEN
	            #bRun_Extend_Latch := TRUE;
	            #bRun_Retract_Latch := FALSE; // 强行清除缩回
	        ELSIF #stCyl.Ctrl.bHmi_Retract THEN
	            #bRun_Extend_Latch := FALSE;
	            #bRun_Retract_Latch := TRUE;
	        END_IF;
	        
	        // 物理输出强行互锁驱动
	        #stCyl.Sts.bOut_Extend := #bRun_Extend_Latch AND (NOT #bRun_Retract_Latch);
	        #stCyl.Sts.bOut_Retract := #bRun_Retract_Latch AND (NOT #bRun_Extend_Latch);
	    END_IF;
	    
	END_IF;
	
	// ==========================================
	// 4. 安全诊断：气缸动作超时看门狗 (WDT)
	// ==========================================
	
	// --- 伸出动作超时计时器 ---
	// 启动：当输出伸出，且伸出限位未到达时
	#tonExtendWatchdog(IN := #stCyl.Sts.bOut_Extend AND (NOT #bActual_Extended),
	                   PT := #stCyl.Cfg.tExtend_Timeout);
	                   
	IF #tonExtendWatchdog.Q THEN
	    #stCyl.Sts.bOut_Extend := FALSE; // 超时，强行关阀断电，防止气爆
	    #bRun_Extend_Latch := FALSE;
	    #bFaultActive := TRUE;
	    #stCyl.Sts.dwDiagCode := 16#0000_0002; // 诊断码 2: 气缸伸出动作超时卡阻
	END_IF;
	
	// --- 缩回动作超时计时器 ---
	#tonRetractWatchdog(IN := #stCyl.Sts.bOut_Retract AND (NOT #bActual_Retracted),
	                    PT := #stCyl.Cfg.tRetract_Timeout);
	                    
	IF #tonRetractWatchdog.Q THEN
	    #stCyl.Sts.bOut_Retract := FALSE;
	    #bRun_Retract_Latch := FALSE;
	    #bFaultActive := TRUE;
	    #stCyl.Sts.dwDiagCode := 16#0000_0003; // 诊断码 3: 气缸缩回动作超时卡阻
	END_IF;
	
	// --- 双限位冲突物理溢出诊断 ---
	// 正常物理结构下，气缸绝对不可能同时既伸出到位，又缩回到位。如果同时触发，判定传感器物理损坏或接线断开。
	IF #bActual_Extended AND #bActual_Retracted THEN
	    #stCyl.Sts.bOut_Extend := FALSE;
	    #stCyl.Sts.bOut_Retract := FALSE;
	    #bRun_Extend_Latch := FALSE;
	    #bRun_Retract_Latch := FALSE;
	    #bFaultActive := TRUE;
	    #stCyl.Sts.dwDiagCode := 16#0000_0004; // 诊断码 4: 双位限位同时触发冲突
	END_IF;
	
	// ==========================================
	// 5. 故障一键复位
	// ==========================================
	IF #stCyl.Ctrl.bReset THEN
	    // 确认物理双位冲突和联锁故障已恢复后，才允许解锁
	    IF NOT (#bActual_Extended AND #bActual_Retracted) THEN
	        #bFaultActive := FALSE;
	        #stCyl.Sts.dwDiagCode := 16#0000_0000; // 恢复正常状态
	        // 复位计时器
	        #tonExtendWatchdog(IN := FALSE, PT := #stCyl.Cfg.tExtend_Timeout);
	        #tonRetractWatchdog(IN := FALSE, PT := #stCyl.Cfg.tRetract_Timeout);
	    END_IF;
	END_IF;
	
	// ==========================================
	// 6. 汇总状态输出
	// ==========================================
	#stCyl.Sts.bExtended := #bActual_Extended;
	#stCyl.Sts.bRetracted := #bActual_Retracted;
	
	// 汇总故障
	IF #bFaultActive THEN
	    #stCyl.Sts.bFault := #bPulse_1Hz; // 闪烁报警
	ELSE
	    #stCyl.Sts.bFault := FALSE;
	END_IF;
	
END_FUNCTION_BLOCK
```

---

## 4. 深度解剖实战模板的“模块化重构美学”

徒弟，请端详这个已经完全符合跨国大厂（如大众汽车 VASS 标准、锂电池头部企业标准）交付级别的气缸控制 FB。

### 4.1 诊断双字（dwDiagCode）在 HMI 开发中的秒杀级优势（第 88、100、113 行）
在代码中，我们定义了一个 `DWord` 类型的诊断代码 `#stCyl.Sts.dwDiagCode`。
*   当联锁不满足，写入 `1`；
*   当伸出超时，写入 `2`；
*   当缩回超时，写入 `3`；
*   当双位冲突，写入 `4`。

在触摸屏（HMI）开发中，你**不需要为每个报警建一盏指示灯**。
你只需在 HMI 画面上，拖放一个标准的 **“文本列表（Text List）”**。
将这个文本列表关联到 `#stCyl.Sts.dwDiagCode` 变量。
*   文本列表配置：`1` -> “安全工艺联锁未通过”；`2` -> “1号气缸伸出超时”；`3` -> “1号气缸缩回超时”。
**只要这一个变量，HMI 就能自动瞬间显示出具体精确到秒的物理故障原因！** 这让你的触摸屏开发效率整整提升了 10 倍以上。

---

### 4.2 零物理元件的仿真离线调试机制（第 36~48 行）
在设备开机调试前期，由于设备还在无锡机械厂装配，电气工程师在办公室干着急。
我们的 FB 内置了 `bSimulateMode`：
只要在 `DB_PlantCylinders` 块里将 `bSimulateMode` 批量强制设为 `TRUE`。
当你启动自动主程序逻辑时，这个气缸 FB 会在内存中，在输出启动后的 2s 自动模拟出“到位反馈”。
**你不需要一个物理限位，就能在博途 PLCSIM 上，把整条包装生产线成千上万个复杂的工艺联锁状态机，全部极其丝滑地模拟运行通透！** 这就是工业级模块化编程带给你的极致生产力。

---

## 5. 大型工厂全局库的标准化分发（Global Library）

当你的气缸 FB 和 UDT 标定测试成功后，千万不要让它们只留在这个项目里。

### 5.1 博途“全局库（Global Library）”的一键分发流程

```
 ┌──────────────────────────────────────────────┐
 │             博途项目中的开发块                │
 │  • FB_StandardCylinder                       │
 │  • UDT_StandardCylinderModel                 │
 └──────────────────────┬───────────────────────┘
                        │ 一键拖拽
                        ▼
 ┌──────────────────────────────────────────────┐
 │              博途右侧: 全局库                 │
 │  • Company_Standard_Library.al14  <───-──────┼─── 团队共享，网络分发
 └──────────────────────────────────────────────┘
```

1.  在博途右侧边栏中，切换到 **“库” (Libraries)** 视图。
2.  点击“新建全局库”，重命名（如 `Company_Standard_Library`）。
3.  将我们开发的 `UDT_StandardCylinderModel` 一键拖入到库文件夹下的 **“用户数据类型” (Types)** 中。
4.  将我们开发的 `FB_StandardCylinder` 一键拖入到库下的 **“模板块” (Master copies)** 中。
5.  右键点击该库，选择“保存并关闭”。
**现在，你已经创建了全公司、全项目团队通用的“标准气缸控制库”。** 任何新项目的电气开发，只需打开这个全局库，一键将 FB 和 UDT 拖入到新项目树中，即可瞬间投入生产。

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：升级全局库中 UDT 时造成的项目“大面积报废故障”
如果你的标准库已经下发给现场 5 个调试小组成员使用。三个月后，你升级了 UDT 里面的某一个子成员名称，并更新了全局库。
*致命后果*：
由于 UDT 被改变，调试人员直接更新这个 UDT 后，**项目里所有调用了旧 UDT 的 FB、FC 以及全局数据块都会瞬间呈现出黄色的“地址不一致”报警，导致项目根本无法编译下载！**
**标准更新规范（版本控制）**：
*   在西门子全局库中更新 UDT 时，博途会自动生成版本号（如 `V1.0.1`）。
*   更新完毕后，必须使用博途的 **“更新项目内的所有实例（Update in project）”** 自动化向导。让博途在后台依次遍历所有块，自动完成旧 UDT 向新 UDT 的物理内存无缝重叠迁移，绝不推荐手写手动修改。

---

### 6.2 错误二：直接在手动模式下通过 HMI 修改 `STAT` 层的自锁标志位
我们前面讲过，FB 内部的 `STAT`（如案例中 `bRun_Extend_Latch`）是它的私有财产。
如果你在触摸屏（HMI）的按钮上，直接写入 `fbCylinder_Instance.bRun_Extend_Latch`。
这会破坏 FB 的封装性，使得触摸屏与 FB 内部的自锁逻辑发生严重的多头写冲突，导致接触器在合闸边缘疯狂摩擦。
**记住：要手动控制气缸伸出，触摸屏按钮应该绑定在 `stCyl.Ctrl.bHmi_Extend` 接口引脚上，坚决不准触碰 STAT。**

---

## 7. 课后练习

请独立思考并完成以下两个极富工业级标定美学的高阶模块化编程练习：

### 练习 1：大功率三相变频电磁加热控制标准化 UDT 与 FB 模板设计
在制药厂反应釜中，加热器的控制极其严苛。
1.  设计一个全局 PLC 数据类型（UDT）命名为 `UDT_SmartHeaterModel`，严格遵循“控制、反馈、状态、工艺”四层结构进行设计。
2.  编写一个配套的控制 FB `FB_SmartHeater`：
    *   **控制逻辑**：当有自动启动指令（`bAutoOn`）或手动启动指令（`bHmiOn`）时，驱动加热器固态继电器（`bOut_HeaterRelay` := TRUE）。
    *   **安全要求**：
        1. 反应釜配有搅拌机运行反馈。如果搅拌机当前没有旋转（`bMixerRunning` = FALSE），加热器严禁开启（防止局部高温发生严重炭化甚至爆炸）。
        2. 反应釜实时温度超过 85°C 时，强制关闭加热输出。
    *   **内置超时诊断**：起动 3 秒内，温度如果没发生上升趋势（`rTempTrend` $\le 0.0$），报“加热盘开路损坏故障”，自锁停机并写入 HMI 诊断双字。

### 练习 2：高抗电磁干扰多通道 AI 模拟量标定标准化库模板设计
请基于第十三章的模拟量一阶线性标定公式，封装一个通用的标定 FB `FB_AnalogScaleBatch`：
*   **输入输出**：接受一个变体指针 `arrRawInputs : Variant`（自适应传入 4、8、16 通道的 PLC 原始整型数据组）。
*   **私有静态区 (Static)**：内部为每一个通道集成一个多重背景一阶低通滤波器，用于消除电磁干扰毛刺。
*   **输出**：标定并滤波后的 `Real` 数组。
*   请设计出其最干净的封装架构和最快的执行时钟逻辑。

---

## 总结

这一章，我们彻底征服了西门子 SCL 编程、乃至整个自动化软件工程中最耀眼的圣殿——**用 SCL 与 UDT 结合实现高度结构化、高内聚、高弹性、零开销复用的模块化设备对象设计**。

我们不仅在软件层面掌握了它的设计规范，更深入剖析了它在多重背景（Multi-Instance）和硬件对齐（ S7-1500 优化块）上的极大运算优势。我们共同手写了一个完全自给自足、内置 4 个多重背景定时器、支持全仿真离线调试和 HMI 诊断双字报警的“重工业级标准双作用气缸通用 FB 模板”。最后，师父传授了你如何将 UDT 与 FB 打包发布为全公司全局库（Global Library）进行极速分发的工程艺术。

请记住，**单机写代码，系统写机器，中大项目写标准。学会用结构体（UDT）去物理规范一个设备的行为与属性，将黑盒子（FB）高高矗立于你的项目树中，你写出的代码，才算真正具备了跨国大厂级标准工艺库的灵魂。**

下一章，我们将正式攻克 SCL 在过程控制、模拟量滤波处理领域最核心、最经典，也是大中型项目必用的物理级演练阵地：**《SCL控制算法PT1和一阶低通滤波实现与动态时间常数补偿》**。届时，我将带你跨越计算机离散时间与物理世界连续时间的鸿沟，手把手教你写出大师级的滤波控制算法。

加油，下期见！