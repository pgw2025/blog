---
title: "10-STL 的变量作用域"
date: 2026-07-05T10:50:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","STL编程"]
categories: ["工业自动化","PLC","西门子STL系列教程"]
author: "Will"
summary: "在软件工程中，**变量作用域（Variable Scope）** 是定义变量生命周期和可见性的核心规则。在通用高级语言中，我们习惯于局部变量和全局变量的概念。。"
---


在软件工程中，**变量作用域（Variable Scope）** 是定义变量生命周期和可见性的核心规则。在通用高级语言中，我们习惯于局部变量和全局变量的概念。

然而，在西门子 S7 处理器底层的实时、确定性操作系统（RTOS）中，变量作用域的划分直接与物理存储器硬件紧密相扣。

由于工业控制系统要求极高的实时性与**确定性执行时间（Deterministic Execution Time）**，CPU 绝不能像 PC 操作系统那样在堆（Heap）中执行复杂的动态内存分配和垃圾回收，因为这会产生不可预测的扫描周期延迟。

为了保证所有子程序执行时间都是恒定的常数 $O(1)$，西门子硬件设计了**局域数据堆栈（L-Stack）**与**背景数据块（DI 寄存器通道）**两套截断式物理存储机制。

本教程将带你深入到 S7 CPU 内部，剖析 **TEMP（临时）**、**STAT（静态）**、**IN（输入）**、**OUT（输出）** 以及 **IN_OUT（输入输出）** 变量在物理存储、参数传递及内存寿命上的本质区别。

---

### 技术兼容性及声明

*   **S7-300/400 (Classic & TIA Portal)**：其物理微码指令集直接基于本教程所述的 L 堆栈管理指针（SP）与 DI 背景寄存器寻址运行。
*   **S7-1500 (TIA Portal)**：完整支持本教程变量作用域模型。但在“优化访问”模式下，系统通过高级编译器对 TEMP 和 STAT 进行了底层寄存器级的静态分配优化，免去了绝对物理偏移量开销。
*   **S7-1200 (TIA Portal)**：**不支持 STL 语言。** 但其在 SCL、LAD 编程中，关于 TEMP、STAT、IN、OUT、IN_OUT 变量的作用域划分、内存生命周期和数据传递机制，与本教程分析的底层物理原理 100% 完全相同。

---

## 1. TEMP 与 LOCAL DATA (L-Stack)：瞬时高速缓冲区

**TEMP（临时变量）** 是最基础的局域变量，生命周期最短。

### 1.1 TEMP 的物理本质：L 堆栈与 SP 指针

在物理本质上，**所有的 TEMP 变量全部存放在 CPU 内部的局域数据堆栈（L-Stack，Local Data Stack）中**。

当操作系统（OS）或父程序调用一个子程序（如 FC1）时：
1.  **物理开辟**：CPU 硬件中的**堆栈指针（SP，Stack Pointer）**会自动向上累加（加上海量偏移量），从而在 L-Stack 中为 FC1 动态“划拨”出一块专属的、被称为 **Local Data Frame（局域数据帧）**的物理 RAM 空间。
2.  **物理注销**：当该块执行完退块指令（`BEU`/`BEC`）返回时，SP 指针自动向下回落。刚才分配给该块的 L-Stack 空间**在物理上被即时注销（释放），变为自由堆栈空间。**

### S7 CPU L 栈空间动态滑移分配图

```
+-----------------------------------------------------------------------------------+
| L-Stack Frame Allocation and "Memory Ghost" Phenomenon                            |
|                                                                                   |
| 1. OS Calls Block A (FC100):                                                      |
|   SP Pointer moves up ───> [ FC100 L-Stack Frame ]                                |
|   - TEMP1 is assigned at L0.0. User writes 16#AABB to TEMP1.                      |
|                                                                                   |
| 2. Block A Exits:                                                                 |
|   SP Pointer moves down. Memory space at [ L-Stack ] is freed but NOT cleared.    |
|   The bits [16#AABB] physically remain on the hardware.                           |
|                                                                                   |
| 3. OS Calls Block B (FC200) immediately after:                                    |
|   SP Pointer moves up again ───> [ FC200 L-Stack Frame ] (Overlaps same memory!)     |
|   - TEMP_B is assigned at L0.0.                                                   |
|   - **If User reads TEMP_B before writing to it, TEMP_B value is 16#AABB!**       |
|     (This is the "Memory Ghost" / "垃圾数据残留" fault)                           |
+-----------------------------------------------------------------------------------+
```

---

### 1.2 知识点 1 代码：实战复现并破除由于“未初始化 TEMP”引发的内存幽灵故障

下面我们用纯 STL 逻辑，编写两个在主程序 OB1 中被连续调用的 FC 块，直接在现场物理复现由于“未初始化 TEMP”导致的垃圾数据残留故障。

#### 完整 STL 代码

```stl
FUNCTION "FC100_Writer_Block" : VOID
TITLE = 写入者块：向 L 栈中强制填入脏数据
VAR_TEMP
   t_Temp_Var : WORD ;        // 临时变量，物理分配在 LW0 位置
END_VAR
BEGIN
NETWORK
TITLE = 故意写入特定的脏数据
      L     W#16#AABB;        
      T     #t_Temp_Var;      // 将 16#AABB 强行写入本地 L 栈的 LW0
END_FUNCTION


FUNCTION "FC200_Reader_Block" : VOID
TITLE = 读取者块：未初始化直接读取，捕获内存幽灵
VAR_TEMP
   t_Read_Var : WORD ;        // 同样物理分配在 LW0 位置
END_VAR
VAR_OUTPUT
   Ghost_Data : WORD ;        // 输出捕获到的垃圾数据
END_VAR
BEGIN
NETWORK
TITLE = 犯错示范：未初始化，直接读取临时变量并输出
      // 致命错误：t_Read_Var 在本块内完全没有经过任何 L、=、S、R 写入指令，
      // 我们直接执行 Load 读取它！
      L     #t_Read_Var;      // 物理上，它直接读取了 L 栈中 LW0 地址的数据
      T     #Ghost_Data;      // 将捕获到的数据传出
END_FUNCTION
```

#### 在 OB1 中的连续调用与寄存器/内存状态跟踪表

假设我们在 OB1 内部，紧紧相邻地连续调用这两个块：
```stl
CALL "FC100_Writer_Block" ;   // 先执行写入
CALL "FC200_Reader_Block" ( Ghost_Data := "System_Monitor".Captured_Data ); // 紧跟其后执行读取
```

| 步骤 | 执行指令行 | L 栈物理地址 LW0 状态 | ACCU 1 状态 | RLO | 状态字 /FC | 底层硬件堆栈微观剖析 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | (开始前) | `16#0000` | `16#0000` | `0` | `0` | 系统干净。 |
| **1** | 进入 FC100 | `16#0000` | `16#0000` | `0` | `0` | **开辟堆栈 A**：SP 指针累加，为 FC100 分配 L 帧。此时 `LW0` 位置初始化为 RAM 原生随机电平（假设为0）。 |
| **2** | `L W#16#AABB` | `16#0000` | `16#AABB` | `0` | `0` | 将 `16#AABB` 载入 ACCU 1。 |
| **3** | `T #t_Temp_Var`| `16#AABB` | `16#AABB` | `0` | `0` | **物理写入 L 栈**：数据 `16#AABB` 被写入 FC100 L 帧的 `LW0` 地址。 |
| **4** | 退出 FC100 | `16#AABB` | `16#AABB` | `0` | `0` | **注销堆栈 A**：SP 指针回落。FC100 的 L 栈失效。**但硬件电平保持原状，`16#AABB` 依然残留在物理芯片上！** |
| **5** | 进入 FC200 | `16#AABB` | `16#AABB` | `0` | `0` | **开辟堆栈 B**：由于是紧跟调用，SP 指针再次累加，为 FC200 分配的 L 帧**物理位置与刚才 FC100 完全重合！** 此时，FC200 的 `t_Read_Var`（分配在 `LW0`）直接继承了刚才残留的 `16#AABB`。 |
| **6** | `L #t_Read_Var`| `16#AABB` | `16#AABB` | `0` | `0` | **幽灵读取发生**：由于未执行过初始化写入，直接读 `LW0`。ACCU 1 意外获得了脏数据 `16#AABB`！ |
| **7** | `T #Ghost_Data`| `16#AABB` | `16#AABB` | `0` | `0` | 输出 `"Captured_Data" = 16#AABB`。验证了垃圾残留的存在。 |

---

### 1.3 工程经验：深入解读 S7-300 因 L 堆栈超限引起的 OB80 与 CPU 意外停机故障

在经典 S7-300 系统中，局域数据堆栈（L-Stack）的总空间极其狭小（例如 CPU 315-2DP 仅分配了 `256 字节` 的 L 栈空间给 OB1 这个优先级类）。

*   **毁灭性的后果场景**：
    假设你在 OB1 调用了 FC1，FC1 声明了 100 字节的 Temp 变量；FC1 中途又调用了 FC2，FC2 又声明了 100 字节的 Temp 变量；FC2 接着调用了 FC3。
    当程序执行到 FC3 的调用入口时，由于连续的嵌套导致 **L 栈深度累计达到了 300 字节，超出了该优先级类允许的最大物理上限（256 字节）。**
    
    此时，CPU 的堆栈控制器会瞬间由于 **Local Data Stack Overflow（局域堆栈溢出）** 硬件故障，强制挂起用户程序，并触发调用 `OB80`（时间/堆栈故障中断）。如果在你的 CPU 中没有下装空的 `OB80`，**PLC 会在微秒级瞬间进入 STOP（停止）状态**，造成生产线意外瘫痪。
*   **工程预防法则**：
    1.  **绝不滥用大长度 TEMP 变量**：在 FC 内部，严禁声明超大长度的有源临时数组（例如 `TEMP_ARRAY : ARRAY[0..200] OF INT`）。对于大体积数据，必须声明在全局共享数据块（Shared DB）中。
    2.  **合理控制调用嵌套深度**：在 S7-300 项目中，调用层级深度建议控制在 3 级以内。

---

## 2. STAT (Static)：私有保持性存储空间

**STAT（静态变量）** 是功能块（FB，Function Block）的专属资产。

### 2.1 STAT 的物理本质：Instance DB 与 DI 寄存器

与存放在不具有保持性的 L 栈上的 TEMP 变量不同，**STAT 变量在物理上全部存放在与之绑定的背景数据块（Instance DB）中**。

当 FB 运行时：
1.  **物理寻址通道**：当前背景 DB 编号被锁死在 CPU 的 **DI 寄存器** 中。
2.  **基准漂移控制**：多重背景下，子实例的基准偏移量被装载到 **AR2 地址寄存器** 中。
3.  **读写机制**：FB 内部对 STAT 变量的读写，底层全部被编译为：`DIX [AR2, P#offset]`（即**背景数据寄存器间接寻址**）。
    由于背景数据块是永久存放在 CPU 专用的工作存储区（RAM）或保持存储区中的，因此 **STAT 变量具有完美的断电记忆特性和扫描周期保持性**。

---

### 2.2 知识点 2 代码：高可靠性电机点按锁存控制（自锁/点动混合逻辑）

下面我们使用 STAT 变量在 FB 内部实现一个工业上最常用的电机“点按/自锁”切换控制块。我们将观察 STAT 变量是如何通过 **AR2** 寄存器实现保持性读写的。

#### 完整 STL 代码（FB30_Motor_Latch）

```stl
FUNCTION_BLOCK "Motor_Latch_Control"
TITLE = 基于静态变量的保持性电机控制
VAR_INPUT
   IN_Btn_Start : BOOL ;      // 输入：启动按钮
   IN_Btn_Stop  : BOOL ;      // 输入：停止按钮
   IN_Mode_Latch : BOOL ;     // 输入：模式选择（1=锁存/自锁，0=点动）
END_INPUT
VAR_OUTPUT
   OUT_Motor_Contactor : BOOL ; // 输出：电机运行接触器
END_VAR
VAR
   stat_Saved_State : BOOL ;  // 静态变量：运行状态保持器 (STAT)
END_VAR
BEGIN
NETWORK
TITLE = 1. 计算自保锁存状态并写入静态变量
      A     #IN_Btn_Start;    // 读取启动信号
      O     #stat_Saved_State;// 或者是刚才保存在静态变量中的运行状态 (实现自锁并联)
      AN    #IN_Btn_Stop;     // 且停止按钮未动作
      =     #stat_Saved_State;// 将新状态写入静态变量保持器。
                              // 底层实际执行: = DIX [AR2, P#0.0] (写入背景 DB)

NETWORK
TITLE = 2. 模式切换与最终控制输出
      A     #IN_Mode_Latch;   // 1. 如果选择了自锁模式
      A     #stat_Saved_State;// 2. 则输出直接依据刚才计算出的自锁状态
      
      O(    ;                 // 3. 否则 (点动模式)
      AN    #IN_Mode_Latch;   
      A     #IN_Btn_Start;    // 4. 输出完全同步于物理启动按钮的状态
      AN    #IN_Btn_Stop;     
      )     ;
      
      =     #OUT_Motor_Contactor; // 驱动最终输出
END_FUNCTION_BLOCK
```

#### 逐行剖析与背景寄存器状态跟踪表

假设：
FB30 的背景 DB 编号为 `DB30`。
`stat_Saved_State` 变量被编译器分配在 FB 内部变量声明表的第 1 个字节第 0 位（即相对偏移 `P#0.0`）。
当前电机处于自锁模式，且上次扫描结束时电机已经启动（即 `stat_Saved_State` 目前在背景 `DB30.DBX0.0` 中的物理状态为 `1`）。
当前扫描周期内，操作员没有按下任何按钮：`IN_Btn_Start = 0`，`IN_Btn_Stop = 0`。

| 步骤 | 执行指令行 | DI 寄存器 | AR2 指针状态 | 状态字 RLO | 静态变量物理值 DB30.DBX0.0 | 底层物理硬件读写内幕解析 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **0** | (开始前) | `30` | `P#0.0` | `0` | `1` | 背景 DB30 被锁入 DI。AR2 载入多重背景基准指针 `P#0.0`。数据状态保持为 `1`。 |
| **1** | `A #IN_Btn_Start` | `30` | `P#0.0` | `0` | `1` | 首检：由于启动按钮未按下，RLO 变为了 `0`。`/FC` 置 `1`。 |
| **2** | `O #stat_Saved_State`| `30` | `P#0.0` | `1` | `1` | **连续或操作（间接读取背景 DB）**：
CPU 解码器识别到 `stat_Saved_State` 是静态变量。底层实际执行：`O DIX [AR2, P#0.0]`。
调取 `DI=30`，偏移 `0.0` 处的值（`1`），与当前 RLO（`0`）执行“或”操作。新 RLO 变为了 `1`。 |
| **3** | `AN #IN_Btn_Stop` | `30` | `P#0.0` | `1` | `1` | 与非操作：由于停止按钮未动作，与非结果保持 `1`。 |
| **4** | `= #stat_Saved_State`| `30` | `P#0.0` | `1` | `1` | **物理写回背景 DB**：
底层执行：`= DIX [AR2, P#0.0]`。将计算结果 `1` 再次写入 `DB30.DBX0.0`。成功将运行状态锁存。 |

---

### 2.3 工程经验：冷启动（Cold Restart）与暖启动（Warm Restart）对 STAT 变量初始值的物理冲击差异

当现场发生突然停电，随后电力恢复，或者工程师在上位机（HMI）上手动执行 CPU 复位重载时，**STAT 变量的复位行为完全决定于 CPU 的启动模式选择。**

*   **暖启动（Warm Restart，OB100 唤醒）**：
    这是最普遍的现场启动模式。
    当 CPU 执行暖启动时，操作系统**会极力保护工作存储区中的所有非易失性数据**。
    因此，存放于背景数据块中的 **STAT 变量会完整保留停电前瞬间的数值状态**。电机自锁标志、工艺报警锁存、运行步骤值通通不会丢失，避免了现场设备因断电重启而发生重置初始化。
*   **冷启动（Cold Restart，OB102 唤醒）**：
    如果执行了冷启动。
    操作系统**会无情地将整个工作存储区清空，并重新从只读的装载存储区（Flash卡）中加载数据结构。**
    此时，所有的 STAT 变量将**被强制重置为它们在离线定义时写入的“初始值（Initial Value）”**。所有的历史锁存状态彻底丢失。
*   **黄金法则**：
    在编写一些绝对不允许因断电重启而初始化（否则极易引发机械越位）的关键控制 FB 时，其核心状态 STAT 变量，**必须在其 FB 接口定义表中，将其“Retain（保持性）”属性明确勾选为保持。** 并在 `OB100` 暖启动块中，编写设备恢复时的安全检测和防冲突保护算法。

---

## 3. IN 与 OUT：参数传递的物理通道

**IN（输入）** 和 **OUT（输出）** 变量是块与外部世界进行数据交互的接口。

然而，在 CPU 的物理实现层面上，**FC 块的 IN/OUT 参数传递，与 FB 块的 IN/OUT 参数传递，有着天壤之别。**

### 3.1 接口参数传递物理机制对比表

```
+---------------------------------------------------------------------------------+
| Parameter Passing Mechanisms: FC vs. FB (Elementary Types)                      |
|                                                                                 |
| 【FC Parameter Passing: Pass-by-Value (值传递)】                                  |
|   Caller Call FC ───> Copies value to Temp/Registers ───> FC reads locally      |
|   (Fast, stateless, temporary memory lifecycle)                                 |
|                                                                                 |
| 【FB Parameter Passing: Mapped to Instance DB】                                 |
|   Caller Call FB                                                                |
|     ├── 1. Compiler-generated code copies caller's value into Instance DB (DI)  |
|     ├── 2. FB executes and reads/writes directly in Instance DB (DI)            |
|     └── 3. Caller copies output value from Instance DB back to caller's dest    |
|   (Stateless reference, fully retained within DB)                               |
+---------------------------------------------------------------------------------+
```

#### FC 块的 IN/OUT 机制：值传递（Pass by Value）
对于 BOOL、INT 等基础类型，当我们在 OB1 中调用 FC102 并挂载实参时，系统直接将实参的当前值拷贝到 **V 栈（前序 L 栈）或物理寄存器**中送入 FC102。
在 FC 运行结束后，系统再将 L 栈中的临时输出值拷贝覆盖到外部实参（值传递）。

#### FB 块的 IN/OUT 机制：背景 DB 媒介传递
在 FB 内部，你定义的每一个 `IN` 和 `OUT` 变量，**在物理上都存在于背景 DB 中**。
当调用 FB 时，编译器会自动生成两段隐式的“接口搬运代码”：
1.  **进入块前**：自动将调用引脚上的实参值拷贝到背景 DB 的 IN 变量物理区中。
2.  **执行块逻辑**：FB 内部的代码直接读写背景 DB。
3.  **退出块后**：自动将背景 DB 中 OUT 变量的最新值，拷贝写回到外部引脚挂载的实参中。

---

### 3.2 知识点 3 代码：实战复现并解密 FC 的“OUTPUT 变量未写满读取陷阱”

由于 FC 的 OUT 变量在退块前完全存放在不具有保持性的 L 栈中。如果我们在 FC 内部，**在没有对 OUT 变量执行写入（赋值）前，就去读取它，或者在某些跳转分支中漏掉了对 OUT 变量的写入**，会发生什么？

我们来编写一段代码，复现这一经典的“FC OUTPUT 悬空”引发的严重工程故障。

#### 完整 STL 代码（FC105_Output_Trap）

```stl
FUNCTION "FC105_Output_Trap" : VOID
TITLE = 复现 FC 块输出参数未写满导致的逻辑劫持
VAR_INPUT
   IN_Trigger : BOOL ;        // 输入：触发信号
END_INPUT
VAR_OUTPUT
   OUT_Signal : BOOL ;        // 输出：报警控制线圈
END_VAR
BEGIN
NETWORK
TITLE = 犯错逻辑：条件跳转分支中，漏掉对 OUT 变量的写入
      A     #IN_Trigger;      
      JC    SET_OUT;          // 若触发，跳转去置位

      // 重点隐患：如果条件不满足，程序不执行任何对 #OUT_Signal 的写入，
      // 直接通过 BEU 提前退块！
      BEU   ;                 // 此时，L 栈中分配给 #OUT_Signal 的地址空间处于悬空未写状态！

SET_OUT: SET;
      =     #OUT_Signal;      // 满足条件时，写入 1
END_FUNCTION
```

#### 在 OB1 中的调用及内存污染状态跟踪表

假设：
FC105 的输出变量 `OUT_Signal` 被分配在局部 L 栈的 `L2.0` 位置。
在 OB1 中，我们这样调用它：
`CALL "FC105_Output_Trap" ( IN_Trigger := "Tag_Trigger_In", OUT_Signal := "Tag_Physical_Horn" );`
第一个扫描周期中：`"Tag_Trigger_In" = 1`。
第二个扫描周期中：`"Tag_Trigger_In"` 变为 `0`（按钮松开）。

| 扫描周期 | 指令步骤 | 触发实参 | L栈地址 L2.0 状态 | 外部输出实参 Q0.0 状态 | RLO | 底层堆栈与值传递动作分析 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Cycle 1** | 进入 FC105 | `1` | `0` | `0` | `0` | 条件满足。 |
| **Cycle 1** | `JC SET_OUT`| `1` | `0` | `0` | `1` | 跳转成立。 |
| **Cycle 1** | `= #OUT_Signal`| `1` | `1` | `0` | `1` | 成功将 L 栈 `L2.0` 写入 `1`。 |
| **Cycle 1** | 退块返回 | `1` | `1` | `1` | `1` | **值传递生效**：退块时，CPU 将 L 栈 `L2.0` 中的 `1` 拷贝到外部实参 `"Tag_Physical_Horn"` 中，喇叭鸣叫。 |
| **Cycle 2** | 进入 FC105 | `0` | `1` (垃圾残留) | `1` | `0` | **Cycle 2 开始**：条件不满足。由于 L 栈被重新分配，`L2.0` 物理上残留了上一周期的 `1`。 |
| **Cycle 2** | `JC SET_OUT`| `0` | `1` | `1` | `0` | 跳转不成立。 |
| **Cycle 2** | `BEU` | `0` | `1` | `1` | `0` | **提前退块（灾难点）**：由于直接退块，**本周期没有执行任何针对 `#OUT_Signal` 的写入！`L2.0` 保持原先的残留值 `1`。** |
| **Cycle 2** | 退块返回 | `0` | `1` | `1` | `0` | **错误的值传递**：系统执行退块拷贝，无情地将 L 栈中残留的 `1` 再次写回实参 `"Tag_Physical_Horn"`。**喇叭即使触发按钮松开，也永远无法停止！** |

---

### 3.4 工程经验：如何消除 FC 输出参数的“悬空”状态

要彻底根治上述由于跳转分支漏写导致的 FC 输出悬空污染问题，必须遵循以下工程黄金准则：

*   **毁灭性的写法（必须杜绝）**：在 FC 内部使用 `S`（置位）或 `R`（复位）指令来控制 `OUTPUT` 变量。因为 `S`/`R` 只有在条件满足时才会写入，条件不满足时会使变量处于悬空未写状态。
*   **安全的黄金写法**：在 FC 内部控制 `OUTPUT` 变量，**100% 必须使用 `=`（赋值）指令**。因为 `=` 指令不管 RLO 是 `1` 还是 `0`，都会在每个扫描周期强行对该变量执行一次确定性的物理写入，彻底消除了临时堆栈垃圾残留的影响。

---

## 4. IN_OUT：输入输出参数与指针引用双向通道

**IN_OUT（输入输出变量）** 在整个西门子变量作用域体系中是最特殊的一个。它代表的是**双向传参（Bidirectional Parameter Channel）**。

### 4.1 IN_OUT 的物理本质：引用传递（Pass by Reference）

与前面“值传递”（需要拷贝复制）的机制完全不同，**IN_OUT 变量在物理底层采用的是 100% 的“引用传递”（Pass by Reference / 传址）机制**。

无论你在 IN_OUT 引脚上挂载的是一个简单的 `BOOL`，还是一个高达几百字节的复杂 `STRUCT`（结构体）：
1.  **不占用拷贝时间**：CPU 绝对不会在进入块和退出块时，对该变量进行任何大块内存的数据拷贝。
2.  **指针传递**：系统在调用该块时，会自动生成一个 **6 字节的 POINTER（指针）** 传入块内，该指针精确锁定了外部实参的实际物理内存首地址。
3.  **穿透读写**：FC 内部对该 `IN_OUT` 变量的每一次读取和写入，底层全部通过 **AR1** 进行指针解包，**直接、实时地穿透块边界，改写外部引脚上实参的值。**

---

### 4.2 知识点 4 代码：利用 IN_OUT 变量开发高可靠性的动态过程数据监控泵

本例设计一个用于实时计算多通道模拟量最大值和平均值的监控泵。我们使用 `IN_OUT` 参数来传递全局数据块中的复杂历史数据结构（STRUCT）。

#### 完整 STL 代码（FC110_Process_Monitor）

```stl
TYPE "History_Data_Struct"
STRUCT
   Last_Average : REAL ;      // 历史平均值
   Max_Peak     : REAL ;      // 历史最大峰值
   Sample_Count : DINT ;      // 采样总次数
END_STRUCT
END_TYPE

FUNCTION "Process_Monitor" : VOID
TITLE = 利用 IN_OUT 执行大体积结构体指针无损读写
VAR_INPUT
   New_Sample : REAL ;        // 新采集的样本值 (REAL)
END_INPUT
VAR_IN_OUT
   Hist_Record : "History_Data_Struct" ; // 历史结构体记录 (IN_OUT)
END_VAR
VAR_TEMP
   t_AR1_Backup : DWORD ;     // 现场保护
END_VAR
BEGIN
NETWORK
TITLE = 1. 指针解包：定位外部实参结构体的物理位置
      TAR1  #t_AR1_Backup;    // 备份 AR1

      // 重点：由于 Hist_Record 是 IN_OUT 复杂参数，
      // L P##Hist_Record 装载的是系统为其分配的 6字节 指针
      L     P##Hist_Record;   
      LAR1  ;                 // 将实参物理指针锁入地址寄存器 AR1。
                              // 此时 AR1 已经直接指向了外部实参 DB 块中的首地址！

      // 重点：如果外部挂接的是 DB 变量，系统已自动将对应的 DB 块锁在了 DB 寄存器中。
      // 我们无需执行 OPN 即可直接读写外部实参数据。

NETWORK
TITLE = 2. 穿透读取外部结构体数据并执行峰值更新
      L     #New_Sample;      
      L     D [AR1, P#4.0];   // 间接读取实参中偏移为 4.0 的变量 (即 Max_Peak)
      >R    ;                 // 比较：新样本是否大于历史最大值
      JCN   Skip;             // 若不满足，跳转

      L     #New_Sample;      
      T     #D [AR1, P#4.0];  // 满足条件：直接穿透写入外部实参 DB 中的 Max_Peak 位置！

Skip: LAR1  #t_AR1_Backup;    // 恢复 AR1
END_FUNCTION
```

#### 逐行剖析与引用传址追踪

假设在 OB1 中，我们这样调用该函数：
`CALL "Process_Monitor" ( New_Sample := "Tag_AI", Hist_Record := "Prod_DB".Engine_1_Record );`
其中，`Engine_1_Record` 物理上存放在 `DB12.DBX30.0`。

*   **`L P##Hist_Record` 执行瞬间**：
    由于是 `IN_OUT` 传址，`ACCU 1` 载入系统生成的、指向 `DB12.DBX30.0` 的指针信息（十六进制为 `16#8400_00F0`，高字节 `84` 代表 DB 存储区，低 24 位为 `P#30.0`）。同时，`DB12` 的编号被 CPU 硬件自动锁死在内部 **DB 寄存器** 中。
*   **`LAR1`**：
    AR1 正式接管实参指针：`AR1 = P#DBX30.0`。
*   **`L D [AR1, P#4.0]`**：
    执行间接物理读取。由于结构体中 `Max_Peak` 定义在偏移 4 字节处（即 `DB12.DBD34`）。
    CPU 实际寻址计算为：`AR1 (P#30.0) + P#4.0 = P#34.0`。
    直接绕过 FC 局部空间，实时读取了外部 `DB12.DBD34` 中的数据。
*   **`T D [AR1, P#4.0]`**：
    同样，直接穿透写入外部 `DB12.DBD34`。

---

### 4.3 工程经验：为什么在异步通信/多周期块（如 TSEND/TRCV）调用中，实参在 IN_OUT 接口上必须保持绝对稳定？

在西门子以太网开放式通信（OUC）中，我们经常使用系统功能块 **`TSEND`** 或 **`TRCV`** 传输数据。它们的数据区接口 `DATA` 被声明为了 `IN_OUT` 类型。

*   **隐患场景与故障**：
    在执行以太网发送时，由于网络延迟，`TSEND` 块通常需要花费数十个甚至上百个 PLC 扫描周期（Scan Cycles）才能完成一个数据包的完整物理发送。在这个漫长的发送中途，`TSEND` 块一直在通过底层引用的 `IN_OUT` 指针，持续、异步地读取你挂载的数据发送缓冲区。
    
    如果你在逻辑中，**在发送还未彻底结束（即 `DONE` 信号未变为 1）前，就迫不及待地通过代码修改了发送缓冲区里的数据。**
*   **灾难性后果**：
    由于 `IN_OUT` 是指针直通引用的。你的每一次中间修改，都会**直接、实时地写到发送缓冲物理区中**。
    这会导致发送出的以太网数据流在中途发生严重畸变和破损，造成接收端上位机解析出完全紊乱的错误指令，引发重大的通信联锁事故。
*   **工程黄金法则**：
    对于所有的异步调用块（涉及通信发送、配方长周期拷贝、高速工艺标定），挂载在其 `IN_OUT` 参数上的外部实参数据，**在计算未彻底完结前，必须无条件锁死，严禁执行任何写入和修改操作！**

---

## 5. S7-1200 SCL 变量作用域等效实现与干净代码开发架构

为了帮助选用 **S7-1200** 平台的工程师编写出同样高执行速度、零变量冲突的高质量程序，我们在此提供 100% 开启优化访问、完全等效于第 4 节结构体双向指针操作的高效 **SCL 代码**。

### S7-1200 / 1500 优化的 SCL 代码（FC110）

```scl
FUNCTION "Process_Monitor_SCL" : VOID
{ S7_Optimized_Access := 'true' } // 启用优化块访问，保证最高执行效率
VERSION : 0.1
VAR_INPUT
   New_Sample : Real;         // 样本输入
END_INPUT
VAR_IN_OUT
   Hist_Record : "History_Data_Struct"; // 使用 IN_OUT 进行引用传递
END_VAR
VAR_TEMP
   t_Temp_Calc : Real;        // 临时变量
END_VAR

BEGIN
    // 在博途优化块模式下，SCL 的 IN_OUT 复杂变量在底层直接被编译为极其高效的
    // "符号引用寄存器"（Reference Map）。我们无需倒腾 AR1，即可实现零拷贝、最高安全级别的直接穿透写。
    
    IF #New_Sample > #Hist_Record.Max_Peak THEN
        #Hist_Record.Max_Peak := #New_Sample; // 直接穿透更新外部实参
    END_IF;
    
END_FUNCTION
```

---

## 总结：现代 PLC 项目的“多维度解耦”变量作用域开发规范

完成了这 10 篇系统性的技术考察后，我们可以总结出一套专为现代化大型、长周期 PLC 项目设计的**“多维度解耦变量作用域划分规范”**：

```
                              【PLC 变量开发决策链】
                                        │
                                        ▼
                                变量是否需要跨周期保持？
                                        │
                       ┌────────────────┴────────────────┐
                    [ 需要 ]                          [ 不需要 ]
                       │                                 │
                       ▼                                 ▼
             变量是否只属于本块私有？              使用 TEMP 变量 (L-Stack)
                       │                       * 强制遵守“先写后读”铁律
             ┌─────────┴─────────┐
          [ 是 ]              [ 否 ]
             │                   │
             ▼                   ▼
     使用 STAT 变量        使用全局 DB 变量
     (Instance DB)       (IN_OUT 引用传参)
```

1.  **TEMP（瞬时数据缓冲区）**：
    凡是只需要在当前扫描周期的当前 Network 中做中间过渡、不参与跨周期保持的变量（如：模拟量标定的中间浮点数、循环计数器），**必须 100% 声明为 TEMP**。并严格死守**“先写入、再读取”**的防御性初始化准则。
2.  **STAT（私有状态保持区）**：
    凡是需要跨周期记忆、代表单个设备运行历史状态的变量（如：故障锁存标志、电机累积运行时间、自动步骤值），**必须声明在 FB 的 STAT 区中。** 严禁跨越 FB 边界去改写其他块的私有 STAT 数据。
3.  **IN_OUT（全局引用桥梁）**：
    凡是需要在多个子系统之间共享、需要执行大体积数据结构传递、且必须实时双向穿透修改的工艺配方、诊断日志结构体，**必须通过 IN_OUT（引用传参）通道进行传递。** 从而彻底省去大块内存拷贝的硬件周期开销，保障 PLC 系统的响应灵敏度。