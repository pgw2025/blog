---
title: "第十一章：UDT 用户自定义数据类型工业应用与大型项目数据管理"
date: 2026-07-24T10:50:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们一起攻克了“结构体（STRUCT）”的核心理念，并用它构建了一个经典的电机三层数据模型。你应该已经初步感受到了面向对象建模的魅力。"
---


在上一章中，我们一起攻克了“结构体（STRUCT）”的核心理念，并用它构建了一个经典的电机三层数据模型。你应该已经初步感受到了面向对象建模的魅力。

但是，你在实际项目中很快会遇到一个新的瓶颈：
假设你在一个 PLC 内写了 50 个设备数据包，全是在各自 FB 里面手写的 `STRUCT`。突然，工艺主任在现场对你说：“小张，所有的电机我们都需要增加一个‘变频器过载早期预警限制’参数。”

这时候你就会傻眼。因为你的结构体是临时、匿名声明在各个 FB 内部的，你必须硬着头皮**手动修改这 50 个 FB 里的结构体，然后重新核对每一行引脚。**

这在大型工业项目中是绝对不可接受的。

为了实现真正的标准化和极速重构，我们必须将“数据结构”提升为 PLC 全局的数据模板——**用户自定义数据类型（User-Defined Types，简称 UDT）**。

在西门子体系中，UDT 已经成为了大型项目（超过 1000 个 I/O 点）数据流管理的绝对核心。今天，师父带你彻底厘清 UDT 与 STRUCT 的宿命区别，掌握 UDT 的嵌套和继承式复用，并手写一个生产线级别的**“多工位智能装配生产线主数据模型”**。

---

## 1. UDT 与 STRUCT 的本质宿命区别

很多初学者觉得 UDT 只是换了个名字的 STRUCT，这是一个极大的误区。作为高级工程师，你需要用高级语言中 **“类（Class）” 与 “实例（Instance）”** 的眼光来审视它们：

| 维度 | 结构体 (STRUCT) | 用户数据类型 (UDT) |
| :--- | :--- | :--- |
| **本质定位** | **匿名的、即时创建的数据容器**（Instance） | **全局唯一的、强类型化的数据模板**（Blueprint / Class） |
| **声明位置** | 声明在 FB/FC 局部变量表，或 DB 内部 | 声明在 CPU 目录下的“PLC 数据类型”中，**全局可见** |
| **复用能力** | **极差**。即使两个 STRUCT 成员一模一样，博途也认为它们类型不兼容 | **极佳**。可以在任意 DB、FB、FC、甚至是 HMI（触摸屏）中无限次重复实例化调用 |
| **一处修改，全局更新** | **不支持**。修改一处，所有其他匿名结构体必须手动挨个修改 | **支持（核心绝活）**。修改 UDT 模板，**所有实例化的 DB、FB 接口及 HMI 标签自动瞬间同步更新** |
| **引脚传递性能** | 作为 FC/FB 的引脚时，如果作为非 In_Out 传递，可能会产生临时内存拷贝 | 在优化块中作为 `IN_OUT` 传输时，**天然采用 6 字节高效指针引用传递，算力开销为 0** |

```
 STRUCT 模式 (数据碎片化，维护地狱):
 ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
 │ Motor_1       │     │ Motor_2       │     │ Motor_3       │
 │ - bStart      │     │ - bStart      │     │ - bStart      │
 │ - rSpeed      │     │ - rSpeed      │     │ - rSpeed      │  <--- 修改任何一个成员，你必须
 └───────────────┘     └───────────────┘     └───────────────┘       逐一去手动改写这 100 个实体

 UDT 模式 (中央集权，一处修改全局自适应):
 ┌──────────────────────────────────────────────┐
 │             UDT_MotorModel (中央模板)         │
 │    - bStart : Bool;  - rSpeed : Real;        │ <--- 在这里添加一个新参数：bAlarmLimit
 └──────────────────────┬───────────────────────┘
                        │ 一键编译
         ┌──────────────┼──────────────┐
         ▼              ▼              ▼
 ┌───────────────┐     ┌───────────────┐     ┌───────────────┐
 │ Motor_1       │     │ Motor_2       │     │ Motor_3       │
 │ - bStart      │     │ - bStart      │     │ - bStart      │
 │ - rSpeed      │     │ - rSpeed      │     │ - rSpeed      │
 │ - bAlarmLimit │     │ - bAlarmLimit │     │ - bAlarmLimit │ <--- 100个电机实体瞬间自适应更新！
 └───────────────┘     └───────────────┘     └───────────────┘
```

---

## 2. 在博途环境下创建与管理 UDT

在 TIA Portal 中，UDT 是独立于程序块存在的全局组件。

### 2.1 创建步骤
1.  打开博途项目，在左侧项目树中展开 PLC 设备。
2.  找到 **“PLC 数据类型” (PLC data types)** 文件夹，双击 **“添加新数据类型” (Add new data type)**。
3.  重命名你新建的数据类型。西门子标准规范中，**一律以大写 `UDT_` 作为前缀**（例如 `UDT_CylinderModel`）。
4.  双击打开，像在 DB 块里一样，在表格中输入你的子变量名、数据类型和起始值。

---

### 2.2 UDT 嵌套（UDT in UDT）：拼积木的艺术

真正的工业标准化，是将底层的 UDT 像乐高积木一样，一层一层往上拼装。

例如，我们要对一个标准的 **“加工工位（Station）”** 进行数据建模：
*   这个工位配有 2 个气缸（Cylinder）、1 个旋转电机（Motor）。
*   我们可以先建立底层的 UDT：`UDT_Cylinder`、`UDT_Motor`。
*   然后再建立中层工位的 UDT：`UDT_Station`，并在内部直接调用底层的 UDT：

```scl
// 结构体声明结构示范：UDT_Station_Process
TYPE "UDT_Station_Process"
VERSION : 0.1
   STRUCT
      stInCylinder : "UDT_Cylinder";  // 直接嵌套调用气缸 UDT
      stPushCylinder : "UDT_Cylinder"; // 直接嵌套调用气缸 UDT
      stSpindleMotor : "UDT_Motor";    // 直接嵌套调用电机 UDT
      bStationReady : Bool;            // 工位整体就绪
   END_STRUCT
END_TYPE
```
这种嵌套结构，使得程序的数据链路与现场的物理机械结构达到了完美的 **“数字孪生（Digital Twin）”**。

---

## 3. UDT 带来的大型项目数据管理革命

在超过 500 个 I/O 点的大型项目中，数据流杂乱、触摸屏（HMI/SCADA）变量关联繁琐是拖延工期的两大元凶。UDT 完美地解决了这两个痛点。

### 3.1 战术一：中央主数据块（Central DB）集中管理

在大型项目中，不要在每个 FB 的背景 DB 里零散存储生产线数据。
**大厂黄金准则**：
1.  建立一个唯一的、全局可见的 **“生产线数据中心 DB”**（例如命名为 `DB_LineData`）。
2.  在 `DB_LineData` 中，使用工位 UDT，将整条生产线的运行状态、故障信息、工艺配方打包集中存储。
3.  任何 FC/FB 在运行时，都通过引脚以 `IN_OUT` 的形式，直连指向这个数据中心对应的工位节点。

```
 ┌────────────────────────────────────────────────────────┐
 │            DB_LineData  (整线中央数据中心)              │
 ├────────────────────────────────────────────────────────┤
 │  • stStation1 : "UDT_Station_Feed"    ───────────────┐  │
 │  • stStation2 : "UDT_Station_Process" ─────────────┐ │  │
 │  • stStation3 : "UDT_Station_Sort"    ───────────┐ │ │  │
 └──────────────────────────────────────────────────┼─┼─┼─┘
                                                    │ │ │ 指针直连传入
                                                    ▼ ▼ ▼
                                          ┌───────────────────┐
                                          │  FB_LineController│
                                          │  (整线工艺调度块)  │
                                          └───────────────────┘
```

---

### 3.2 战术二：触摸屏（HMI/SCADA）变量的“一键秒关联”

传统的 HMI 编程，你需要在 PLC 关联表中，把 PLC 里的几百个报警位、启动位手动和触摸屏进行一一拉线关联，极其耗时且极易出错。

**在博途平台下的极致体验**：
1.  如果你的 PLC 变量是基于 UDT 构建的（如 `DB_LineData.stStation1`）。
2.  你可以在触摸屏（WinCC / Comfort Panel）的“HMI 数据类型”中，直接导入对应的 `UDT_Station_Feed`。
3.  在 HMI 画面上，你只需将 PLC 里的 `stStation1` **整根线拖拽** 给 HMI 的 UDT 实例。
4.  **1 秒钟，上百个子变量（启动、反馈、速度、电流、报警）全部自动完成通信配对！** 这将为你节省 90% 以上的 HMI 画图关联时间。

---

## 4. 工业级综合案例：智能汽车总装生产线数据中心架构

现在，我们将展现大厂高级项目经理的顶层设计能力。

### 4.1 工业场景描述
你正在负责一条汽车锂电池包总装生产线。该生产线由 **3 个核心工位** 拼接而成：
1.  **工位 1：自动上料工位（Station_Feed）**。
    包含：1 个升降双作用气缸（`stLiftCylinder`）、1 个真空吸盘机械手（`stVacuumSucker`）、1 个入口光电检测。
2.  **工位 2：激光焊接工位（Station_Process）**。
    包含：1 个大功率主轴变频电机（`stSpindleMotor`）、1 个安全夹紧气缸（`stClampCylinder`）、1 个红外测温仪（`rLaserTemp`）。
3.  **工位 3：智能分拣及出料工位（Station_Sort）**。
    包含：1 段变频输送带电机（`stConveyor`）、1 个气动推料气缸（`stPusher`）、1 个 Modbus RFID 扫码枪。

我们要使用 UDT，在博途中搭建出**整条生产线的数据孪生主数据块**，并编写一个全局诊断和汇总的 SCL 主程序。

---

### 4.2 步骤一：创建底层基础气缸 UDT（UDT_Cylinder）

在博途“PLC数据类型”中，双击“添加新数据类型”，命名为 `UDT_Cylinder`：

```scl
TYPE "UDT_Cylinder"
VERSION : 0.1
   STRUCT
      Ctrl_Extend : Bool;     // 电磁阀驱动：气缸伸出 (DO)
      Ctrl_Retract : Bool;    // 电磁阀驱动：气缸缩回 (DO)
      Fbk_Extended : Bool;    // 传感器反馈：气缸已伸出到位 (DI)
      Fbk_Retracted : Bool;   // 传感器反馈：气缸已缩回到位 (DI)
      bFault : Bool;          // 气缸动作超时卡死故障
      tTimeoutLimit : Time := T#5s; // 气缸动作超时报警设定值
   END_STRUCT
END_TYPE
```

---

### 4.3 步骤二：创建底层基础电机 UDT（UDT_Motor）

创建 PLC 数据类型，命名为 `UDT_Motor`：

```scl
TYPE "UDT_Motor"
VERSION : 0.1
   STRUCT
      Ctrl_Start : Bool;      // 驱动电机启动 (DO)
      rSpeedSet : Real;       // 速度给定值 (RPM)
      Fbk_Running : Bool;     // 电机运行反馈 (DI)
      Fbk_Fault : Bool;       // 电机硬件故障报警 (DI)
      rActualSpeed : Real;    // 实际转速 (RPM)
      rCurrent : Real;        // 实际运行电流 (A)
   END_STRUCT
END_TYPE
```

---

### 4.4 步骤三：创建三个中层工位 UDT

#### 1. 建立上料工位 UDT：`UDT_Station_Feed`
```scl
TYPE "UDT_Station_Feed"
VERSION : 0.1
   STRUCT
      stLiftCylinder : "UDT_Cylinder";  // 嵌套调用气缸 UDT
      stVacuumSucker : STRUCT           // 匿名吸盘结构
         bSuckerOn : Bool;
         bVacuumOK : Bool;
      END_STRUCT;
      bPartPresent : Bool;              // 入口物料检测
      bStationReady : Bool;             // 工位就绪状态
   END_STRUCT
END_TYPE
```

#### 2. 建立焊接工位 UDT：`UDT_Station_Process`
```scl
TYPE "UDT_Station_Process"
VERSION : 0.1
   STRUCT
      stSpindleMotor : "UDT_Motor";     // 嵌套调用电机 UDT
      stClampCylinder : "UDT_Cylinder"; // 嵌套调用气缸 UDT
      rLaserTemp : Real;                // 激光温度反馈
      bStationReady : Bool;
   END_STRUCT
END_TYPE
```

#### 3. 建立分拣工位 UDT：`UDT_Station_Sort`
```scl
TYPE "UDT_Station_Sort"
VERSION : 0.1
   STRUCT
      stConveyor : "UDT_Motor";         // 嵌套调用电机 UDT
      stPusher : "UDT_Cylinder";        // 嵌套调用气缸 UDT
      sRFID_Data : String[20];          // RFID 扫描数据
      bStationReady : Bool;
   END_STRUCT
END_TYPE
```

---

### 4.5 步骤四：创建顶层生产线主数据 UDT（UDT_ProductionLine）

现在，我们将三个工位打包，合并成整条生产线的主 UDT：

```scl
TYPE "UDT_ProductionLine"
VERSION : 0.1
   STRUCT
      Header : STRUCT                   // 生产线总报头数据
         sLineName : String := 'Car_Battery_Line_1'; // 生产线名称
         bLineEStop : Bool;             // 整线紧急停止
         bLineAutoMode : Bool;          // 整线全自动模式
      END_STRUCT;
      
      Station1_Feed : "UDT_Station_Feed";       // 工位 1 数据节点
      Station2_Process : "UDT_Station_Process"; // 工位 2 数据节点
      Station3_Sort : "UDT_Station_Sort";       // 工位 3 数据节点
      
      Summary : STRUCT                  // 生产数据汇总
         diTotalPassedCount : DInt;     // 整线合格品累计计数
         diTotalFailedCount : DInt;     // 整线废品累计计数
         bLineHasFault : Bool;          // 整线任意工位有故障报警
      END_STRUCT;
   END_STRUCT
END_TYPE
```

---

### 4.6 步骤五：在全局 DB 块中进行一键实例化

我们在 PLC 程序块中，新建一个全局数据块（Global DB），命名为 **`DB_ProductionLineData`**。
在 DB 内部，我们**只需声明一个变量**：

```scl
// 全局 DB：DB_ProductionLineData
// 优化的块访问启用
VAR
    stMyLine : "UDT_ProductionLine"; // 瞬间完成整条生产线、成百上千个底层物理变量的数据骨架搭建！
END_VAR
```

---

### 4.7 步骤六：编写全局诊断与工艺联锁的 SCL 程序 (FC_LineDiagnostics)

现在，我们在 SCL 中编写一个高层诊断 FC，通过点“.”运算符深入数据结构的每一个末梢，实现全局联锁诊断和状态汇总。

```scl
FUNCTION "FC_LineDiagnostics" : Void
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
   VAR_IN_OUT 
      stLine : "UDT_ProductionLine"; // 核心：整条线的数据结构传入 (引用传递)
   END_VAR

   VAR_TEMP 
      bFault_Temp : Bool; // 临时故障汇总变量
   END_VAR


BEGIN
	// ==========================================
	// 1. 整线急停安全联锁
	// ==========================================
	IF #stLine.Header.bLineEStop THEN
	    // 无条件关闭整线所有动力机构
	    #stLine.Station1_Feed.stLiftCylinder.Ctrl_Extend := FALSE;
	    #stLine.Station1_Feed.stLiftCylinder.Ctrl_Retract := FALSE;
	    
	    #stLine.Station2_Process.stSpindleMotor.Ctrl_Start := FALSE;
	    #stLine.Station2_Process.stClampCylinder.Ctrl_Extend := FALSE;
	    
	    #stLine.Station3_Sort.stConveyor.Ctrl_Start := FALSE;
	    #stLine.Station3_Sort.stPusher.Ctrl_Extend := FALSE;
	    RETURN; // 退出，不允许执行后续任何业务逻辑
	END_IF;
	
	// ==========================================
	// 2. 汇总诊断：实时监测整线每一个角落的硬件故障
	// ==========================================
	#bFault_Temp := FALSE;
	
	// A. 诊断工位 1 的升降气缸故障
	IF #stLine.Station1_Feed.stLiftCylinder.bFault THEN
	    #bFault_Temp := TRUE;
	END_IF;
	
	// B. 诊断工位 2 的主轴电机故障和夹紧气缸故障
	IF #stLine.Station2_Process.stSpindleMotor.Fbk_Fault OR 
	   #stLine.Station2_Process.stClampCylinder.bFault THEN
	    #bFault_Temp := TRUE;
	END_IF;
	
	// C. 诊断工位 3 的输送电机和推料气缸故障
	IF #stLine.Station3_Sort.stConveyor.Fbk_Fault OR 
	   #stLine.Station3_Sort.stPusher.bFault THEN
	    #bFault_Temp := TRUE;
	END_IF;
	
	// 将汇总故障结果写入数据中心
	#stLine.Summary.bLineHasFault := #bFault_Temp;
	
	// ==========================================
	// 3. 工艺联锁：防夹防撞自适应闭环
	// ==========================================
	// 焊接工位（工位2）启动主轴旋转的前提条件是：
	// 安全夹紧气缸必须处于完全伸出到位（夹紧）状态，防止离心力把工件甩出发生重大工业事故。
	IF #stLine.Station2_Process.stClampCylinder.Fbk_Extended THEN
	    // 允许启动主轴
	    ;
	ELSE
	    // 强制切断主轴电机，并发出警报
	    #stLine.Station2_Process.stSpindleMotor.Ctrl_Start := FALSE;
	END_IF;
	
END_FUNCTION
```

---

## 5. 深度解剖实战代码的“工业标准化设计思维”

徒弟，请静下心来仔细对比：

在传统的编程中，如果你想把“工位 2 的电机故障”接到主控画面中，你需要在 OB1 里写一堆逻辑，把 `#M100.5` 传给 `#M200.2`。
而在我们基于 UDT 构建的数据中心模型里，**你不需要建立任何中间中转标志位（M点）**。
在 `FC_LineDiagnostics` 中，我们直接读写 `#stLine.Station2_Process.stSpindleMotor.Fbk_Fault`。

### 5.1 这样做在工程上的伟大意义：
1.  **代码即图纸**：
    程序的变量名称与现场机械设计图纸的命名完全对齐。任何一个新来的电气工程师，即使从未看过你的程序，只要他知道焊接工位有一个主轴电机，他就能瞬间猜到它的变量路径是：`stLine.Station2_Process.stSpindleMotor`。
2.  **极速标准化**：
    如果二期工程要在现场增加一条“Car_Battery_Line_2”。
    你只需要在 `DB_ProductionLineData` 里，再多添加一个变量 `stMyLine_2 : UDT_ProductionLine`。**1 秒钟，二期工程成百上千个变量就全部自动生成完毕！** 你的诊断 FC 也可以无缝对二期生产线数据进行一键诊断调用。

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：误在“在线调试运行”阶段修改 UDT 结构
如果你在工厂现场，设备正在轰鸣运转。此时你在线连接博途，修改了 `UDT_Cylinder` 内部的一个变量类型或成员名称并点击下载。
*致命后果*：由于 `UDT_Cylinder` 是底层模板，一旦修改，**所有调用了它的 DB 块全部面临重构重置，PLC 的 CPU 会因为大面积 DB 块地址漂移，瞬间被拉入 STOP 状态！**
*避坑指南*：
*   在大型系统开机前，必须尽可能在办公室对 UDT 结构进行反复论证和定型。
*   如果在现场必须修改，在博途中对相关的 DB 块开启 **“内存保留（Memory Reserve）”** 功能。这样在线添加新变量时，编译器会利用预留的灰色内存，绝不触发 DB 块的初始化和 CPU 的停机。

---

### 6.2 错误二：HMI 通信因 UDT 更改而“暗中中断”
有时你修改了 PLC 里的 UDT，PLC 运行正常，但是触摸屏上的按钮和显示却突然全部失效（或显示黄色叹号）。
*原因*：PLC 的 UDT 修改后，其符号寻址的哈希校验值（Hash Value）发生了改变，但 HMI 里的 UDT 模板没有同步编译下载，导致 HMI 在后台用旧的哈希值寻址失败。
**黄金法则：只要动了 UDT，必须对 PLC 和 HMI 进行一键“全部重新编译并全部下载”，绝不能图省事只下载 PLC。**

---

## 7. 课后练习

请独立思考并完成以下两个大型项目架构级练习：

### 练习 1：智能仓储输送分拣工位三维 UDT 架构设计
一个智能立体仓储系统，包含：1个堆垛机提升机（Hoist Motor）、3个过渡接驳输送带（Array of UDT_Motor）、1个安全安全光幕保护信号。
1.  请仿照 4.4 节，为堆垛机、接驳线等基础执行机构设计好底层的 UDT（`UDT_Hoist`、`UDT_Motor`）。
2.  设计中层工位 UDT：`UDT_WarehouseStation`。
3.  编写一个 SCL FC，对堆垛机高度进行防超限诊断：如果堆垛机当前实时高度 `rActualHeight` 超过了设定的最大安全高度限值，立刻强行切断驱动输出并报警。

### 练习 2：汽车焊装夹具多双作用气缸同步气动防撞诊断
在汽车焊装线（Fixture）上，一个拼装夹具（Fixture_Base）配有 4 个大作用力夹紧气缸：
`stCylinder : Array[1..4] of "UDT_Cylinder";`
在夹装车身钢板时，这 4 个夹紧气缸必须在 3 秒（`tSyncLimit`）内完全同步沈出（`Fbk_Extended` 全部为 TRUE）。如果其中某一个气缸由于气路气压不足发生卡阻落后，为了防止车身钢板发生物理受力不均导致扭弯变形，必须立刻做出安全动作。
请编写一个 SCL FC：
*   **输入输出 (In_Out)**：`arrFixtureCyls : Array[1..4] of "UDT_Cylinder"`。
*   **输出**：`bSyncError : Bool`（同步故障线圈）。
*   **要求**：使用 `FOR` 循环遍历这 4 个气缸。如果发现 4 个气缸的到位状态存在不一致（比如部分到位，部分没到位）持续超过 3 秒，立即强制将所有 4 个气缸进行“缩回复位（`Ctrl_Retract` := TRUE）”进行安全卸载，并触发同步故障 `bSyncError`。

---

## 总结

这一章，我们彻底攻克了西门子 SCL 编程、乃至整个现代化工业自动化系统架构中最耀眼的皇冠——**用户自定义数据类型（UDT）在大型项目中的工业应用**。

我们从底层编译和面向对象思想的高度，厘清了 UDT（模板类）与 STRUCT（匿名实例）的物理区别；探讨了 UDT 与 HMI 进行“一键秒关联”的工程高效手段。最后，我们手写了一个汽车锂电池包装配生产线三层嵌套数据孪生主数据块。

请记住，**单机项目写代码，中大型项目写架构。学会用 UDT 去抽象、规范和编织你的数据流，是你成为大型工程项目经理和资深系统架构师的必经之路。**

下一章，我们将彻底迈入 PLC 算法设计的最前线，也是在自动化工程中占据半壁江山的领域：**《SCL控制算法PT1和一阶低通滤波实现》**。届时，我将带你跨越计算机科学与物理模拟量的鸿沟，手把手教你如何用 SCL 代码在 PLC 内部模拟出物理世界的一阶滞后滤波器。

加油，下期见！