---
title: "第九章：SCL 数组完全教程与百台电机级控制架构"
date: 2026-07-24T10:20:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在前几章中，我们一起攻克了 SCL 中的 `IF` 分支、`CASE` 状态机以及 `FOR` / `WHILE` 循环。你现在已经掌握了控制流的基础。但是，当你在实际现场面对大量同类型设备时，孤立的变量声明会让你的代码迅速膨胀。"
---


在前几章中，我们一起攻克了 SCL 中的 `IF` 分支、`CASE` 状态机以及 `FOR` / `WHILE` 循环。你现在已经掌握了控制流的基础。但是，当你在实际现场面对大量同类型设备时，孤立的变量声明会让你的代码迅速膨胀。

比如，一个现场有 100 台输送线电机。如果你声明为：
`#bMotor1_Start`、`#bMotor2_Start`……一直到 `#bMotor100_Start`。
这不仅意味着你需要重复写 100 遍几乎相同的控制逻辑，更糟糕的是，**你根本无法利用循环语句对它们进行索引式管理**。

这就是我们需要掌握的数据结构——**数组（Array）**。

数组是将**相同数据类型**的元素，按照连续的物理内存排列组合成的一个集合。它是 SCL 工业级编程中不可或缺的基石。

今天，师父带你由浅入深，从一维数组、多维数组的底层内存对齐，一直讲到数组初始化战术，并带你手写一个真正用于工厂生产的**“100台电机顺序起动与磨损均衡（运行时间最少优先）管理系统”**。

---

## 1. 一维数组的物理本质与声明

一维数组是最基础的线性结构，像一排等距排列的储物箱，每个箱子都有一个唯一的门牌号（索引）。

### 1.1 一维数组的声明语法

在博途的数据块（DB）或 FB/FC 的变量区中，一维数组的声明格式如下：

```scl
<变量名> : Array[<下限>..<上限>] of <数据类型>;
```

```scl
// 示例
#arrPressures : Array[1..10] of Real;      // 声明 10 个浮点数数组
#arrLimits : Array[0..99] of Int;          // 声明 100 个整型数组
#arrStatus : Array[-5..5] of Bool;         // 西门子支持下限为负数，共有 11 个元素
```

*师父的建议*：在实际工程中，除非特殊工艺算法（如偏置计算），**强烈建议将数组下限统一设置为 `1`（符合工业设备编号习惯）或 `0`（符合计算机寻址习惯）**。

---

### 1.2 💡 编译器的底层秘密：寻址与对齐

你可能好奇，当你在 SCL 中写下 `#arrPressures[#i]` 时，CPU 是如何从物理上找到这个数据的？

在 CPU 内部，数组是以**连续物理地址**存放的。

#### 1) 在非优化块（标准块）中：
数据严格按照字节地址排列。对于一个 `Array[1..10] of Real` 而言，每个 `Real` 占用 4 个字节：
*   元素 1 地址：`DB1.DBD0`
*   元素 2 地址：`DB1.DBD4`
*   元素 `i` 地址：`BaseAddress + (i - 下限) * 元素大小（4字节）`

**缺点**：每次访问 `#arrPressures[#i]`，CPU 都要在后台执行一次乘法和加法寻址公式，运算效率较低，且容易因为非字对齐产生硬件性能损耗。

#### 2) 在优化块中：
西门子编译器完全接管了内存。它会根据 CPU 寄存器的宽度（S7-1500 是 32/64 位），将数组元素直接对齐到最适合硬件高速访问的边界。
**在优化块中使用 SCL 动态下标访问，效率是非优化块的数倍。**

---

## 2. 多维数组：工业多维空间矩阵的构建

在一些复杂的现场，一维数组可能不够用。比如一个立体仓库（立体车库），有 3 个排，每个排有 10 根立柱，每根立柱有 5 层货架。
这就需要 **多维数组**。

### 2.1 多维数组的声明与维度物理对应

在博途中，我们用逗号 `,` 分隔不同的维度：

```scl
<变量名> : Array[<维1下限>..<维1上限>, <维2下限>..<维2上限>] of <数据类型>;
```

```scl
// 示例：2D 数组（代表 3排 10列 的立体货架，存放货包 ID）
#arrWarehouse_2D : Array[1..3, 1..10] of Int; 

// 示例：3D 数组（代表 3排 10列 5层 的立体货架）
#arrWarehouse_3D : Array[1..3, 1..10, 1..5] of Int;
```

```
 2D 数组逻辑图 (Array[1..3, 1..10] of Int):
 
          列 1   列 2   列 3   列 4  ...   列 10
        ┌──────┬──────┬──────┬──────┬─────┬──────┐
 排 1   │ [1,1]│ [1,2]│ [1,3]│ [1,4]│ ... │[1,10]│
        ├──────┼──────┼──────┼──────┼─────┼──────┤
 排 2   │ [2,1]│ [2,2]│ [2,3]│ [2,4]│ ... │[2,10]│
        ├──────┼──────┼──────┼──────┼─────┼──────┤
 排 3   │ [3,1]│ [3,2]│ [3,3]│ [3,4]│ ... │[3,10]│
        └──────┴──────┴──────┴──────┴─────┴──────┘
```

### 2.2 多维数组的访问：
```scl
#arrWarehouse_2D[2, 5] := 105; // 向第 2 排、第 5 列的货位写入货物代码 105
```

---

## 3. 数组的两种初始化战术

数组声明后，如果没有初始值，它的内容就是随机的（对于 TEMP）或者默认的 0。在程序启动或配方切换时，我们必须对数组进行初始化。

### 3.1 战术一：静态/编译期初始化（定义默认值）

在博途创建全局 DB 时，你可以在数组声明的“起始值（Start value）”一栏中，写下初始值。

*   **西门子标准语法**：
    *   `[10(1.0)]`：代表数组的前 10 个元素全部初始化为 `1.0`。
    *   `[2(1.0, 2.0)]`：代表元素交替初始化，如 `[1.0, 2.0, 1.0, 2.0]`。
    *   `[1..5 => 10, 6..10 => 20]`：V16+ 支持的高级赋值（1到5号元素为10，6到10号元素为20）。

---

### 3.2 战术二：动态/运行期初始化（SCL 实时擦除）

在实际运行中（如设备刚开机执行 **OB100（启动组织块）**，或者操作员按下“配方复位”按钮时），我们必须在程序运行期间将数组一键擦除。

#### 写法 1：传统 `FOR` 循环（安全，适合个性化赋值）
```scl
FOR #i := 1 TO 10 DO
    #arrPressures[#i] := 0.0; // 依次擦除
END_FOR;
```

#### 写法 2：西门子系统指令 `FILL_BLK`（极速，适合整块连续擦除）
如果你需要对上千个元素的超大数组快速清零，使用系统内置指令 `FILL_BLK`（填充块）可以在一个周期内以接近底层的速度完成擦除。

```scl
// 将常数 0.0 填充到 #arrPressures 数组中，从 1 号元素开始，填充 10 个
FILL_BLK(IN := 0.0,
         COUNT := 10,
         OUT := #arrPressures[1]);
```

---

## 4. 数组访问与动态下标的保护边界

数组最大的威力在于**动态下标访问**。你可以用一个变量来指向数组的任意元素。

```scl
#rCurrentPressure := #arrPressures[#iIndex]; // 动态寻址
```

### 4.1 ⚠️ 危险红线：动态下标失控
我们前面讲过，数组越界（Index Out of Bounds）会导致 CPU 直接停机。
当使用变量作为下标时，**你必须在访问前对该变量进行范围夹逼和限幅保护。**

```scl
//  高安全性的动态下标防御写入
#iSafeIndex := LIMIT(MN := 1, IN := #iIndex, MX := 10); // 强行将下标约束在 1..10 之间

#arrPressures[#iSafeIndex] := #rNewPressure; // 绝对安全的写入，永不越界
```

---

## 5. 工业级综合案例：100台电机智慧管理系统 (FB_MotorGroupManager)

现在，我们把一维数组、自定义结构体（UDT）、`FOR` 循环、最值筛选以及系统定时器完美结合，编写一个用于重工业现场的电机综合控制程序。

### 5.1 工业背景与工艺要求
某污水处理厂配有 100 台大功率曝气泵。为了防止系统出现电气和物理损坏，程序设计必须满足以下严苛工艺：
1.  **一键防电网冲击顺序起动（Sequential Startup）**：
    由于 100 台电机同时起动产生的瞬时涌流（Inrush Current）会拉垮整条街的电网。当操作员启动“一键起动（`bBatchStart`）”时，系统必须**每间隔 2 秒起动一台电机**，直到所有未故障、处于自动模式的电机全部起动。
2.  **备用机磨损均衡（Wear Leveling）机制**：
    当工艺需要临时额外起动一台备用泵时，系统必须自动遍历这 100 台电机，**寻找其中处于自动模式、没有故障、当前没有运行，且“累计运行时间最少（Minimum Run Hours）”的那台电机启动**。这样能保证 100 台电机的磨损程度完全一致。
3.  **运行数据汇总统计**：
    每个扫描周期必须实时统计出当前：正在运行的电机总数、发生故障的电机总数。

---

### 5.2 步骤一：创建电机结构体（UDT_MotorData）

在博途中添加新数据类型，命名为 `UDT_MotorData`：

```scl
TYPE "UDT_MotorData"
VERSION : 0.1
   STRUCT
      bAutoMode : Bool;       // 自动/手动模式选择
      bRunning : Bool;        // 电机运行反馈信号 (DI)
      bFault : Bool;          // 电机故障综合报警信号 (DI)
      bCmdStart : Bool;       // PLC 输出驱动电机启动线圈 (DO)
      rRunHours : Real;       // 电机累计运行时间 (Hours)
   END_STRUCT
END_TYPE
```

---

### 5.3 步骤二：块接口声明（FB_MotorGroupManager）

我们声明一个全局 FB。100 台电机的数据包装成一个大数组 `Array[1..100] of UDT_MotorData` 存放在全局数据块中，我们通过 `IN_OUT` 将其引入。

```
VAR_INPUT
    bBatchStart : Bool;        // 一键顺序起动请求
    bStartNextWear : Bool;     // 磨损均衡：增开一台最少运行时间的电机请求脉冲
    bResetAll : Bool;          // 故障一键复位
END_VAR

VAR_OUTPUT
    iRunningCount : Int;       // 当前正在运行的电机总数
    iFaultCount : Int;         // 当前处于故障状态的电机总数
    bBatchStartBusy : Bool;    // 顺序起动正在执行中标志
END_VAR

VAR_IN_OUT
    arrMotors : Array[1..100] of "UDT_MotorData"; // 核心：100台电机数据数组
END_VAR

VAR
    // 静态变量
    tonSeqTimer {InstructionName := 'TON_TIME'; LibVersion := '1.0'} : TON_TIME; // 2s顺序起动定时器
    iSeqIndex : Int := 1;      // 顺序起动当前遍历到的电机指针
    bBatchStartActive : Bool;  // 顺序起动激活锁存
    bStartNext_FP : Bool;      // 增开备用机边沿标志
END_VAR

VAR_TEMP
    i : Int;                   // 通用循环计数器
    rMinHoursFound : Real;     // 磨损均衡算法：当前找到的最少运行小时数
    iBestCandidateID : Int;    // 最少运行小时数的电机编号
END_VAR
```

---

### 5.4 步骤三：SCL 代码实现

```scl
FUNCTION_BLOCK "FB_MotorGroupManager"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 数据实时汇总统计（每个周期运行）
	// ==========================================
	#iRunningCount := 0;
	#iFaultCount := 0;
	
	FOR #i := 1 TO 100 DO
	    // 统计运行总数
	    IF #arrMotors[#i].bRunning THEN
	        #iRunningCount := #iRunningCount + 1;
	    END_IF;
	    
	    // 统计故障总数
	    IF #arrMotors[#i].bFault THEN
	        #iFaultCount := #iFaultCount + 1;
	        #arrMotors[#i].bCmdStart := FALSE; // 安全联锁：故障时强制切断输出驱动
	    END_IF;
	    
	    // 一键故障复位
	    IF #bResetAll AND #arrMotors[#i].bFault THEN
	        #arrMotors[#i].bFault := FALSE;
	    END_IF;
	END_FOR;
	
	// ==========================================
	// 2. 一键防冲击：顺序起动控制逻辑
	// ==========================================
	// 捕捉起动按钮上升沿
	IF #bBatchStart AND NOT #bBatchStartActive THEN
	    #bBatchStartActive := TRUE;
	    #iSeqIndex := 1; // 归零，从第一台电机开始顺序检索
	END_IF;
	
	#bBatchStartBusy := #bBatchStartActive;
	
	IF #bBatchStartActive THEN
	    // 驱动顺序起动 2s 定时器
	    #tonSeqTimer(IN := TRUE, PT := T#2s);
	    
	    // 每隔 2s 启动一台
	    IF #tonSeqTimer.Q OR #iSeqIndex = 1 THEN
	        #tonSeqTimer(IN := FALSE, PT := T#2s); // 快速复位定时器以便下一轮重新计时
	        
	        // 寻找下一台可以启动的电机（必须处于自动、未故障、当前未启动状态）
	        WHILE (#iSeqIndex <= 100) DO
	            IF #arrMotors[#iSeqIndex].bAutoMode AND 
	               (NOT #arrMotors[#iSeqIndex].bFault) AND 
	               (NOT #arrMotors[#iSeqIndex].bCmdStart) THEN
	                
	                // 找到了！输出启动，并递增指针，结束本次搜索
	                #arrMotors[#iSeqIndex].bCmdStart := TRUE;
	                #iSeqIndex := #iSeqIndex + 1;
	                EXIT; 
	            END_IF;
	            
	            #iSeqIndex := #iSeqIndex + 1; // 没找到合适的，继续找下一台
	        END_WHILE;
	        
	        // 边界保护：100台全部扫描完毕后，关闭顺序启动流程
	        IF #iSeqIndex > 100 THEN
	            #bBatchStartActive := FALSE;
	            #tonSeqTimer(IN := FALSE, PT := T#2s);
	        END_IF;
	    END_IF;
	END_IF;
	
	// ==========================================
	// 3. 核心算法：备用机磨损均衡（最少运行时间优先启动）
	// ==========================================
	// 仅在外部增开请求信号的上升沿触发一次计算
	IF #bStartNextWear AND NOT #bStartNext_FP THEN
	    
	    // 初始化最少小时数基准为极大值
	    #rMinHoursFound := 999999.0;
	    #iBestCandidateID := -1; // -1 代表尚未找到合适候选
	    
	    // 遍历 100 台电机，寻找磨损最轻的备用机
	    FOR #i := 1 TO 100 DO
	        IF #arrMotors[#i].bAutoMode AND 
	           (NOT #arrMotors[#i].bFault) AND 
	           (NOT #arrMotors[#i].bCmdStart) THEN
	            
	            // 核心比较：当前电机的累计运行时间是否比已找到的最少时间还要少？
	            IF #arrMotors[#i].rRunHours < #rMinHoursFound THEN
	                #rMinHoursFound := #arrMotors[#i].rRunHours;
	                #iBestCandidateID := #i; // 锁死当前最佳候选电机 ID
	            END_IF;
	            
	        END_IF;
	    END_FOR;
	    
	    // 评估最终选拔结果
	    IF #iBestCandidateID <> -1 THEN
	        // 找到了磨损最轻的备用泵，一键启动它！
	        #arrMotors[#iBestCandidateID].bCmdStart := TRUE;
	    END_IF;
	    
	END_IF;
	#bStartNext_FP := #bStartNextWear; // 锁存边沿
	
END_FUNCTION_BLOCK
```

---

## 5. 深度剖析实战代码的“工程师思维”

这段百台电机级别的管理代码，展现了我们在大型系统架构时的顶层设计理念。

### 5.1 为什么将“顺序启动”和“磨损均衡”写在一起？
这就是结构化数据对象（UDT Array）带来的巨大优势。
因为 100 台电机的数据被整齐地放在了同一个 `arrMotors` 数组里，我们在任何时候，都可以用不同的逻辑策略（一个是时间排序，一个是机械磨损排序）去访问同一组底层硬件数据，而**绝不会发生物理数据冲突**。

### 5.2 顺序启动中的 `WHILE` 与 `EXIT` 协同优化（第 44~54 行）
在顺序启动中，我们写了这一段：
```scl
WHILE (#iSeqIndex <= 100) DO
    IF #arrMotors[#iSeqIndex].bAutoMode ... THEN
        #arrMotors[#iSeqIndex].bCmdStart := TRUE;
        #iSeqIndex := #iSeqIndex + 1;
        EXIT; // 关键：立刻跳出整个 WHILE，让 PLC 进入下一个 2s 延时
    END_IF;
    #iSeqIndex := #iSeqIndex + 1;
END_WHILE;
```
*底层用意*：我们不能在一个扫描周期内把所有合适的电机全启动了，那会造成涌流。
通过在找到**第一台**符合要求的电机并置位启动后，立即执行 `EXIT` 跳出。指针 `#iSeqIndex` 巧妙地停留在当前位置，等待下一个 2 秒定时器到达后，继续从该位置往后检索。这种**“跨周期的异步步进检索”**是状态机与数组遍历结合的艺术。

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：误认为 DB 重新下载后，数组内部的历史数据一定保留
在现场调试时，如果你修改了 UDT 结构，或者在全局数据块中插入了新变量。点击下载时，博途会提示“数据块初始化”。
如果你点击了确定，**100 台电机的累计运行时间（rRunHours）会瞬间全部清空归零！**
*拯救手段*：
1.  在现场调试大项目前，**务必先在博途中在线连接，对含有累计运行时间的 DB 块点击“快照（Snapshot）”**。
2.  将快照值复制写入到起始值中，然后再下载。这样能保住珍贵的历史磨损累计数据。

---

### 6.2 错误二：直接把一整维多维数组作为实参塞给不匹配的形参
```scl
VAR
    arrA : Array[1..10, 1..5] of Int;
    arrB : Array[1..5] of Int;
END_VAR

// ❌ 编译报错：无法将多维切片直接赋给一维
#arrB := #arrA[1]; 
```
*纠正*：在西门子中，无法像高级语言（如 Python）那样直接对多维数组进行单维切片切取。如果你需要传递，必须写 `FOR` 循环，依次拷贝内部的元素。

---

## 7. 课后练习

请独立完成以下两个具有极高实用价值的数组操作练习：

### 练习 1：手写 10 档平滑滑动窗口均值滤波器 (一维数组应用)
传感器采样的原始压力存储在 `rRawPressure : Real`。
为了消除毛刺，请编写一个 **FB** 块：
*   **静态存储区 (Static)**：声明一个 `arrHistory : Array[1..10] of Real;` 用于记录最近 10 次的采样历史值。
*   **工艺逻辑**：
    1.  每个周期开始，将数组内的元素向后“挤一步”：1号元素移到2号，2号移到3号……最后的10号元素被挤出销毁。
    2.  将最新的 `rRawPressure` 写入 1 号位置。
    3.  计算并输出这 10 个历史数据的平均值。
*   *提示：可以使用 FOR 循环往后拷贝，思考一下，为了不覆盖数据，FOR 循环应该从 10 递减到 2，还是从 2 递增到 10？*

### 练习 2：立体仓库空货位一键多维检索器 (多维数组应用)
一个立体仓库共有 `3排`（Row 1..3），每排有 `10列`（Col 1..10）货架。货架状态用二维数组表示：
`arrShelfActive : Array[1..3, 1..10] of Bool;` (为 TRUE 代表货位已被占用，为 FALSE 代表货位空闲)
请编写一个 SCL FC，当新货包入库时，一键扫描货架：
*   **输出**：
    *   `iFoundRow : Int`：找到的第一个空闲货位的排编号。
    *   `iFoundCol : Int`：找到的第一个空闲货位的列编号。
    *   `bFoundSuccess : Bool`：检索成功标志。
*   **要求**：必须从 1 排 1 列开始，逐列、逐排扫描，一旦找到第一个空闲位，**立刻使用 EXIT 彻底跳出双重多维循环**并报告位置，防止无谓消耗 CPU 扫描时间。

---

## 总结

这一章，我们彻底征服了 SCL 语言最核心的数据容器——**数组**。

我们不仅在语法层级掌握了一维和多维数组的声明和寻址机理，更看清了它在优化块与非优化块中底层物理对齐的运行区别。我们共同写出了大厂高弹性、带有变长自适应和防电网冲击顺序起动的“100台电机智慧磨损均衡管理系统”。

请记住，**高超的自动化逻辑，不在于写了多少行代码，而在于你如何利用最精炼的数据结构，把现场成百上千个复杂的物理设备，归拢得像交响乐团一样各司其职。**

下一章，我们将踏入 SCL 编程中另一个高级阵地：**《SCL自定义数据类型UDT深度剖析》**。我们将探讨如何将工艺中零散的数据和设备状态打包分类，构建出符合现代化工业标准、极具复用性的模块化结构体系。

加油，下期见！