---
title: "15-REAL 运算的物理内幕与高精度防线（+R, -R, *R, /R）"
date: 2026-07-05T11:40:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","STL编程"]
categories: ["工业自动化","PLC","西门子STL系列教程"]
author: "Will"
summary: "对于在梯形图（LAD）中进行编程的工程师来说，实数（REAL，即浮点数）的加减乘除与整数并无二致，不过是把变量填入 `ADD`、`SUB`、`MUL`、`DIV` 框中。"
---


对于在梯形图（LAD）中进行编程的工程师来说，实数（REAL，即浮点数）的加减乘除与整数并无二致，不过是把变量填入 `ADD`、`SUB`、`MUL`、`DIV` 框中。

然而，在 CPU 内部的**浮点数协处理器（FPU，Floating-Point Unit）**中，实数运算的物理过程极其复杂。

与整数直接进行补码相加不同，实数在内存中是以 **IEEE 754 单精度浮点数标准**存储的。每次执行 `+R`（实数加）、`-R`（实数减）、`*R`（实数乘）、`/R`（实数除）时，FPU 必须在硬件层面上执行**拆包（Unpacking）、对阶（Exponent Alignment）、尾数相加（Significand Addition）、规格化（Normalization）以及舍入（Rounding）**等一系列繁琐的物理步骤。

在 STL 中，如果忽视了浮点数运算的底层硬件特质，编写出的计算程序极易发生**大数吃小数（精度丢失）**、**NaN（非数字）状态扩散**以及**无感除零崩溃**等严重故障。

本教程将带你深入到 CPU 的 FPU 微码和硬件寄存器层面，深度解密实数运算的执行本质，帮助你写出运行效率极高、精度极佳、免疫崩溃的工业级实数控制算法。

---

### 技术兼容性声明

*   **S7-300 / S7-400**：原生支持本文所有 32 位实数 STL 算术指令，由片内的有源 FPU 协处理器硬件直接执行。
*   **S7-1500**：完整支持本文所有 STL 指令，通过内部高度优化的矢量标量计算单元执行。
*   **S7-1200**：**不支持 STL 语言**。本教程第四章将专门提供 100% 等效的高性能 **SCL 语言重构方案**，帮助 S7-1200 用户在博途平台中实现相同的高精度实数算法。

---

## 1. 实数运算的物理内幕：对阶与规格化

西门子 S7 处理器中的 `REAL` 类型完全遵循 **IEEE 754 单精度浮点数标准**，在内存中精确占用 32 位（4字节）空间。其物理布局划分为：**1 位符号位（Sign）、8 位指数位（Exponent）和 23 位尾数位（Fraction）**。

### 1.1 硬件执行细节：为什么 `+R` 运算比 `+I` 慢十倍以上？

当我们在 STL 中执行一条 `+I`（整型加法）时，CPU 的加法器在一两个时钟周期内即可完成物理电平相加。
而当执行 `+R`（实数加法）时，FPU 必须顺序经历以下四个硬件执行阶段：

```
+---------------------------------------------------------------------------------+
| Floating-Point Addition (+R) Hardware Pipeline                                  |
|                                                                                 |
| 1. Exponent Alignment (对阶):                                                   |
|   Compare exponents. Shift mantissa of smaller number to the right.             |
|                                                                                 |
| 2. Mantissa Addition (尾数相加):                                                |
|   Add aligned mantissas inside the ALU.                                         |
|                                                                                 |
| 3. Normalization (规格化):                                                      |
|   Shift result left/right so leading bit is 1. Adjust exponent.                 |
|                                                                                 |
| 4. Rounding (舍入):                                                             |
|   Fit the result into 23-bit significand window. Guard bits discarded.          |
+---------------------------------------------------------------------------------+
```

这一复杂的控制逻辑，导致 **`+R` 指令在底层的执行周期通常是 `+I` 指令的 10 到 20 倍。**

---

### 1.2 物理级证明：为什么“大数加小数”在 PLC 中会发生精度丢失崩溃？

在流量累积、皮带秤总重计量等工业场景中，我们经常遇到如下现象：**当总量累积到一定值后，即使瞬时流量计有读数，总量也再也不会发生任何微小的增加。** 

这并非程序死锁，而是被 FPU 的**“对阶舍入（Align & Rounding）”**硬件设计强行过滤了。

#### 物理级数学证明：

假设当前总量 `Total = 100000.0`，当前瞬时量增量 `Increment = 0.001`。
我们来看 FPU 执行 `+R` 时的二进制变化：

*   **步骤 1：转换为 IEEE 754 格式**
    *   $100000_{10} = 11000011010100000_2 = 1.1000011010100000_2 \times 2^{16}$
        *   其指数（已偏置） $E_1 = 16 + 127 = 143$ （二进制 `10001111`）
        *   其尾数 $M_1 = 10000110101000000000000_2$ （23位）
    *   $0.001_{10} \approx 1.048576_2 \times 2^{-10}$
        *   其指数（已偏置） $E_2 = -10 + 127 = 117$ （二进制 `01110101`）
        *   其尾数 $M_2 = 00001100011010100111111_2$ （23位）

*   **步骤 2：对阶（Exponent Alignment）**
    FPU 硬件比较两指数，发现差值为：$\Delta E = 143 - 117 = 26$。
    为了执行加法，必须将较小数 $0.001$ 的指数提升到 $143$。这意味着其尾数 $M_2$ 必须**向右逻辑移动 26 位**。

*   **步骤 3：移位丢弃（Rounding）**
    由于尾数存储寄存器只有 23 位宽度。
    当 $M_2$ 向右移动 26 位时，**$M_2$ 的全部有效数据直接被移出了 23 位物理寄存器的右端边界，变为了纯 0！**

*   **结论**：对阶后，计算变为了 $100000.0 + 0.0 = 100000.0$。**数据在芯片层面上被物理性彻底丢弃了。**

---

### 1.3 知识点 1 代码：消除大数吃小数的高精度“双缓冲累积”算法

为了解决这一痛点，我们必须在 STL 中编写一套**“双缓冲累积（Dual-Buffer Accumulation）”**算法：设置一个临时高灵敏度累积变量 `t_Small_Accum`，当其值大于设定门槛时，才一次性加入大总量中，并执行复位。

#### 完整 STL 源代码

```stl
FUNCTION "High_Prec_Accum" : VOID
TITLE = 消除大数吃小数的高精度双缓冲累积器
VAR_INPUT
   i_Inst_Flow  : REAL ;      // 输入：瞬时流量 (REAL, 单位：L/s)
   i_Scan_Time  : REAL ;      // 输入：当前扫描周期 (REAL, 单位：秒)
   i_Threshold  : REAL ;      // 输入：触发大累积的门槛值 (例如 1.0L)
END_INPUT
VAR_IN_OUT
   iq_Total_Mass : REAL ;     // 输入输出：主总量累积器 (大总量)
   iq_Small_Buf  : REAL ;     // 输入输出：临时小缓冲区 (小累积)
END_VAR
VAR_TEMP
   t_Increment   : REAL ;     // 临时变量：当前扫描增量
END_VAR
BEGIN
NETWORK
TITLE = 1. 计算当前周期微增量
      L     #i_Inst_Flow;     // ACCU 1 = 瞬时流量
      L     #i_Scan_Time;     // ACCU 1 = 扫描时间, ACCU 2 = 瞬时流量
      *R    ;                 // 计算: 增量 = 流量 * 周期
      T     #t_Increment;     // 保存当前微增量 (例如 0.001L)

NETWORK
TITLE = 2. 先行累加至小缓冲区，防范精度丢失
      L     #t_Increment;     
      L     #iq_Small_Buf;    // 此时两个小数在同一数量级，相加绝不丢精度
      +R    ;                 
      T     #iq_Small_Buf;    // 临时更新小缓冲区

NETWORK
TITLE = 3. 判定小缓冲区是否跨越累积门槛
      L     #iq_Small_Buf;    
      L     #i_Threshold;     // 装载设定的门槛值 (例如 1.0)
      >=R   ;                 // 比较：小缓冲区是否 >= 门槛
      JCN   End;              // 若不满足，直接跳转结束

      // 若满足，将小缓冲区的整数值（门槛倍数）一次性加入大总量
      L     #iq_Small_Buf;    
      L     #iq_Total_Mass;   // 此时累加值大于门槛，大数加小数的差值比例大大降低，精度得到保障
      +R    ;                 
      T     #iq_Total_Mass;   // 更新大总量

      // 重置小缓冲区
      L     #iq_Small_Buf;    
      L     #i_Threshold;     
      -R    ;                 // 扣除掉已经加过的门槛值，保留不足一个门槛的余数
      T     #iq_Small_Buf;    // 重新写入小缓冲区保存

End:  NOP   0;
END_FUNCTION
```

---

### 1.4 工程经验：高精度 PID 算法为什么要严格控制扫描周期（采样时间）的稳定性？

许多工程师在调用 PID 块（如 FB41）时，喜欢将其放在 OB1 主循环中运行，并在 `CYCLE` 引脚随便填一个 `100ms`。

*   **控制异常成因**：
    由于 OB1 的扫描周期是不断跳变的（本周期 12ms，下周期 25ms）。
    在 PID 底层的微分（D）和积分（I）浮点数计算中，需要高频乘以或除以当前的采样时间 $T_s$。
    **如果 $T_s$ 随时间不断波动，FPU 内部对阶时的移位舍入误差就会在闭环回路中不断叠加放大，导致控制器的输出（MV）产生无规律的高频电平抖动。**
*   **黄金准则**：
    所有的闭环控制块（PID、一阶滤波器、高精度累加器），**必须 100% 放置在具有硬定时特性的定时中断组织块（如 OB35 100ms 循环中断）中运行**，并确保其 `CYCLE` 参数值与 OB35 的物理中断周期完全绝对吻合。

---

## 2. 闭环控制的核心：实数加法（`+R`）与减法（`-R`）

在实数的加法和减法中，由于实数的表示状态远比整数丰富，状态字寄存器中的控制位表现出特殊的物理特征。

### 2.1 状态字特色：如何用状态字识别 NaN（非数字）与无穷大状态？

在执行完 `+R` 或 `-R` 运算后，CPU 内部的 FPU 会自动刷新状态字中的 **CC1** 和 **CC0** 位。

特别需要注意的是，**实数计算具有“无效状态”**。如果发生了未定义的非法计算（例如 $0.0 / 0.0$，或者对负数求平方根），计算出的结果会变成 **NaN (Not a Number，非数字，在十六进制下表现为 `16#7FFF_FFFF` 或 `16#FFFF_FFFF`)**。

#### 浮点数计算后 CC1 和 CC0 的硬件状态矩阵：

```
+---------------------------------------------------------------------------------+
| Floating-Point Condition Codes (CC1, CC0) Mapping                               |
|                                                                                 |
|                        ALU Floating-Point Result                                |
|                                    │                                            |
|       ┌───────────────────┬────────┴──────────┬───────────────────┐             |
|       ▼ (Result = 0.0)    ▼ (Result < 0.0)    ▼ (Result > 0.0)    ▼ (NaN / ±∞)  |
|     CC1=0, CC0=0        CC1=0, CC0=1        CC1=1, CC0=0        CC1=1, CC0=1    |
+---------------------------------------------------------------------------------+
```

一旦 `CC1=1, CC0=1` 组合出现，说明**当前的计算已经彻底崩塌，结果不再代表任何物理数值，而是变为了毁灭性的 NaN 脏数据。**

---

### 2.2 知识点 2 代码：高可靠性 PID 偏差变化率（微分）计算块（带 NaN 安全自愈）

我们来编写一段闭环控制中至关重要的微分（D）项偏差变化率计算代码。程序在计算偏差的同时，会高频自检状态字。一旦捕获到 NaN 状态，将立刻启动“安全自愈”保护，切断脏数据向后级执行机构扩散。

#### 完整 STL 源代码

```stl
FUNCTION "Safe_Dev_Calc" : VOID
TITLE = 具备 NaN 自诊断功能的偏差变化率计算器
VAR_INPUT
   i_Set_Point   : REAL ;     // 输入：设定值 (SP)
   i_Process_Val : REAL ;     // 输入：过程反馈值 (PV)
   i_Scan_Time   : REAL ;     // 输入：当前采样周期 (Ts, 必须 > 0)
END_INPUT
VAR_IN_OUT
   iq_Last_Error : REAL ;     // 输入输出：历史偏差暂存
END_VAR
VAR_OUTPUT
   q_Error_Rate  : REAL ;     // 输出：偏差变化率 (De/Dt)
   q_Signal_Error: BOOL ;     // 输出：浮点数异常报警 (Q0.1)
END_VAR
VAR_TEMP
   t_Current_Err : REAL ;     // 临时变量：当前偏差
END_VAR
BEGIN
NETWORK
TITLE = 1. 计算当前偏差: Error = SP - PV
      L     #i_Set_Point;     
      L     #i_Process_Val;   
      -R    ;                 // 计算: SP - PV -> ACCU 1
      T     #t_Current_Err;   // 保存当前偏差

NETWORK
TITLE = 2. 计算偏差变化率: Rate = (Current_Err - Last_Error) / Ts
      L     #t_Current_Err;   
      L     #iq_Last_Error;   
      -R    ;                 // 计算: Current_Err - Last_Error -> ACCU 1
      
      L     #i_Scan_Time;     
      TAK   ;                 // 交换，使时间常数作为除数，差值作为被除数
      /R    ;                 // 计算: (Current_Err - Last_Error) / Ts

      // 重点物理防线：自检 FPU 是否产生了 NaN 或者是除零溢出异常
      // 溢出或 NaN 会导致状态字中的 CC1=1, CC0=1 
      A     CC_1;             
      A     ...
      // 注意：在标准 STL 中，我们可以直接通过比较指令检查是否产生了 NaN，
      // 或者是直接用以下硬核的状态字组合进行瞬时拦截：
      A     CC_1;             
      A     CC_0;             // 只有当 CC1=1, CC0=1 同时成立时，表明结果为 NaN 或者是溢出无穷大
      JC    ERR_HEAL;         // 捕获异常，跳转至自愈分支

      // 正常流程，保存并更新状态
      T     #q_Error_Rate;    // 输出变化率
      L     #t_Current_Err;   
      T     #iq_Last_Error;   // 更新历史偏差
      CLR   ;                 
      =     #q_Signal_Error;  
      BEU   ;                 // 正常退出

ERR_HEAL: NOP 0;              // 自愈保护分支
      L     0.0;              
      T     #q_Error_Rate;    // 强行输出变化率为 0.0，防止后级执行机构暴冲
      T     #iq_Last_Error;   // 强行重置历史偏差，阻断 NaN 的时间迭代循环
      SET   ;                 
      =     #q_Signal_Error;  // 报出浮点计算严重故障
END_FUNCTION
```

---

### 2.3 工程经验：为什么 NaN 数据在 DB 中会像“传染病”一样快速扩散？

在现场调试中，我们经常遇到 HMI 画面上的压力、温度、液位等数值**通通同时变成了 “####” 或者是 “NaN”**。

*   **传染病机理：NaN 的计算传播性**。
    在 IEEE 754 规定下，**任何包含 NaN 的浮点数计算，其最终结果无条件变为 NaN。**
    假设你有一个数据块 DB1，里面存放了 20 个连贯计算的过程数据。
    如果你的第一个传感器通道发生了断线产生 NaN。这个 NaN 参与了第一个网络（Network 1）的滤波计算，导致第一个滤波输出变为 NaN；
    接着，这个滤波输出又被传给第二个网络的流量标定，导致流量输出也变为了 NaN……
    **在短短的一个扫描周期（几毫秒）内，这个 NaN 会沿着所有的逻辑加减乘除管道，把整个 DB1 块里的 20 个变量全部“污染”为 NaN，瞬间导致整台设备的控制算法完全瘫痪。**
*   **工程控制防线**：
    1.  **在入口进行“前置限幅隔离”**：在从模拟量通道（AI）读取数据转为 REAL 后的第一步，必须使用比较指令剔除所有不合理的极限异常值（如大于 $1.0 \times 10^{9}$ 或者是负值越界），防止 NaN 脏数据进入核心计算 DB。

---

## 3. 比例标定与物理补偿：实数乘法（`*R`）与除法（`/R`）

`*R`（实数乘法）和 `/R`（实数除法）是传感器物理标定（量程转换）的核心指令。

### 3.1 乘除法底层的 FPU 物理机制与除零灾难

在 FPU 内部，执行实数乘法和除法不需要进行复杂的对阶（这是相对加法唯一的优势），但其**指数需要直接相加减，尾数执行 23 位硬件乘除阵列计算。**

*   **除零灾难（Division by Zero）**：
    如果 `/R` 的除数（ACCU 1 里的值）在运行中变为了精确的 `0.0`。
    FPU 内部除法器将无法完成运算。此时状态字中的 **OV（溢出）** 会瞬间被硬件置 `1`，而计算产生的结果会变为 $\pm\infty$（正负无穷大，在十六进制下表现为 `16#7F80_0000` 或 `16#FF80_0000`）。
    如果将这个无穷大结果作为实数传出给模拟量通道（AQ），会直接引发物理电平发生极端的输出暴冲，对现场阀门造成严重的机械物理损坏。

---

### 3.2 知识点 3 代码：孔板流量计温压补偿计算模块（带完备实数自检）

根据气体状态方程，孔板流量计测得的原始流量，必须经过温度和压力的非线性校正，公式为：
$$Flow_{Calibrated} = Flow_{Raw} \times \sqrt{\frac{P_{Actual} \times T_{Standard}}{P_{Standard} \times T_{Actual}}}$$
由于涉及复杂的乘除和开平方（开平方内部参数必须大于0），必须使用极度严密的 STL 架构来保障计算安全。

#### 完整 STL 代码

```stl
FUNCTION "Gas_Flow_Correction" : VOID
TITLE = 高可靠性孔板流量温压补偿计算器
VAR_INPUT
   i_Raw_Flow   : REAL ;      // 输入：原始流量值 (REAL)
   i_Act_Temp   : REAL ;      // 输入：现场实际温度 (REAL，开尔文 K)
   i_Act_Press  : REAL ;      // 输入：现场实际压力 (REAL，绝对压力 MPa)
   i_Std_Temp   : REAL ;      // 输入：标准温度 (常数，273.15K)
   i_Std_Press  : REAL ;      // 输入：标准压力 (常数，0.1013MPa)
END_INPUT
VAR_OUTPUT
   q_Corr_Flow  : REAL ;      // 输出：标定校正后的真实流量
   q_Calc_Error : BOOL ;      // 输出：计算过程异常报警 (Q0.2)
END_VAR
VAR_TEMP
   t_Temp_Ratio : REAL ;      // 临时变量：温度之比
   t_Press_Ratio: REAL ;      // 临时变量：压力之比
   t_Radicand   : REAL ;      // 临时变量：开方被开数
END_VAR
BEGIN
NETWORK
TITLE = 1. 温度比例计算: T_Std / T_Act (防范温度除以0)
      L     #i_Act_Temp;      
      L     0.0;              
      <=R   ;                 // 判定实际绝对温度是否 <= 0.0 (物理上绝对温度必须 > 0)
      JC    ERR_CALC;         // 若不合理，强行拦截跳转

      L     #i_Std_Temp;      
      L     #i_Act_Temp;      
      /R    ;                 // 计算: T_Std / T_Act
      T     #t_Temp_Ratio;    // 暂存

NETWORK
TITLE = 2. 压力比例计算: P_Act / P_Std (防范标准压力误设为0)
      L     #i_Std_Press;     
      L     0.0;              
      <=R   ;                 // 判定标准压力是否 <= 0
      JC    ERR_CALC;         

      L     #i_Act_Press;     
      L     #i_Std_Press;     
      /R    ;                 // 计算: P_Act / P_Std
      T     #t_Press_Ratio;   // 暂存

NETWORK
TITLE = 3. 乘积计算并验证开方前置条件
      L     #t_Temp_Ratio;    
      L     #t_Press_Ratio;   
      *R    ;                 // 计算: (T_Std/T_Act) * (P_Act/P_Std)
      T     #t_Radicand;      // 写入被开数

      L     #t_Radicand;      
      L     0.0;              
      <R    ;                 // 判定被开数是否为负数 (负数开平方直接产生 NaN 灾难)
      JC    ERR_CALC;         

      // 执行开平方。在标准库中通过内置系统函数 SQRT(REAL) 实现，
      // 此处我们在 STL 伪代码中等效展示其算法结果
      SQRT  ;                 // 计算 SQRT(t_Radicand) -> ACCU 1

      // 4. 乘以原始流量得到最终校正流量
      L     #i_Raw_Flow;      
      *R    ;                 
      T     #q_Corr_Flow;     // 输出正常校正流量
      
      CLR   ;                 
      =     #q_Calc_Error;    
      BEU   ;                 // 安全退块

ERR_CALC: NOP 0;              // 故障安全自愈分支
      L     #i_Raw_Flow;      
      T     #q_Corr_Flow;     // 发生计算异常时，强行让校正流量等于原始流量，保持系统不锁死
      SET   ;                 
      =     #q_Calc_Error;    // 报出计算严重故障报警
END_FUNCTION
```

---

## 4. 流程图建议：实数运算 FPU 状态字自诊断与 NaN 拦截树

在编写涉及多路乘除的实数校正逻辑时，强烈建议参照如下流程图，在代码中构筑起三道防线：

```
                           【采集原始模拟量实数】
                                     │
                                     ▼
                        [防线 1] 是否超出物理合理范围？
                                     │
                  ┌──────────────────┴──────────────────┐
               [ 是 ]                                [ 否 ]
                  │                                     │
                  ▼                                     ▼
          强行阻断隔离并报警                    进行多级乘除计算
                                                        │
                                                        ▼
                                         [防线 2] 状态字 CC1/CC0 是否为 1/1？
                                         (NaN 状态或除零溢出)
                                                        │
                                ┌───────────────────────┴───────────────────────┐
                             [ 是 ]                                          [ 否 ]
                                │                                               │
                                ▼                                               ▼
                        [防线 3] 启动自愈                       输出正常校正浮点数
                        复位计算状态，输出默认值
```

---

## 5. TIA Portal S7-1200 / S7-1500 的现代 SCL 替代与优化

由于 **S7-1200 硬件固件去除了状态字寄存器模拟，不支持 STL**。为了在博途平台中实现同等高安全、零吃数的高精度实数计算，本章提供完全等效的优秀 **SCL 重构方案**。

### 5.1 知识点 1 的 SCL 规范重构（双缓冲累积器，防止吃数）

```scl
// S7-1200 / 1500 优化的高精度双缓冲累积算法
#t_Increment := #i_Inst_Flow * #i_Scan_Time; // 计算微增量
#iq_Small_Buf := #iq_Small_Buf + #t_Increment; // 先行累加至小缓冲区，保障数量级对齐

IF #iq_Small_Buf >= #i_Threshold THEN
    #iq_Total_Mass := #iq_Total_Mass + #iq_Small_Buf; // 跨越门槛，一次性加入大总量，防止精度丢失
    #iq_Small_Buf := #iq_Small_Buf - #i_Threshold;    // 扣除门槛，保留余数
END_IF;
```

---

### 5.2 知识点 3 的 SCL 规范重构（孔板流量计温压校正算法）

```scl
// 带 100% 物理防护与 NaN 拦截的博途 SCL 温压补偿算法
IF (#i_Act_Temp <= 0.0) OR (#i_Std_Press <= 0.0) THEN
    #q_Corr_Flow := #i_Raw_Flow; // 异常拦截
    #q_Calc_Error := TRUE;
ELSE
    #t_Temp_Ratio := #i_Std_Temp / #i_Act_Temp;
    #t_Press_Ratio := #i_Act_Press / #i_Std_Press;
    #t_Radicand := #t_Temp_Ratio * #t_Press_Ratio;
    
    IF #t_Radicand < 0.0 THEN
        #q_Corr_Flow := #i_Raw_Flow; // 负数开方防御
        #q_Calc_Error := TRUE;
    ELSE
        // 调用内置高度优化的 SQRT 浮点数开方函数
        #q_Corr_Flow := #i_Raw_Flow * SQRT(#t_Radicand); 
        #q_Calc_Error := FALSE;
    END_IF;
END_IF;
```

---

## 6. 工业级规范与调试经验总结

在本专栏浮点数运算的尾声，我们为具有 LAD 基础的工程师梳理出 2 条在实际调试和优化浮点数算法时的金牌经验：

1.  **善用 TIA 在线监控中的“实数格式格式化（Floating-Point Display）”**：
    在博途在线调试时，双击监控表中的 REAL 变量，可以将其显示格式由“十进制浮点”更改为“十六进制浮点（Hex）”。
    *   **调试大招**：如果你怀疑某个变量是否产生了 NaN 或无穷大状态，直接看其 Hex 格式。
        *   如果显示 **`16#7F80_0000`**，说明它发生了**除零正无穷大**。
        *   如果显示 **`16#7FFF_FFFF`** 或 **`16#FFFF_FFFF`**，说明它已经彻底变为了 **NaN 脏数据**。
        通过十六进制底层标志，你可以比普通工程师提早几小时锁定算法崩溃的源头。
2.  **避免在高频、对精度敏感的场合使用 `REAL` 进行反复加减，推荐在核心算法中使用双精度 `LREAL`**：
    虽然 S7-300 不支持，但现代的 **S7-1500 硬件上已经集成了 64 位的物理 LREAL 浮点计算器**。LREAL 的尾数精度高达 52 位，十进制精度达到 15 到 17 位。
    *   **设计建议**：在编写重大型高炉配方计算、精密电能累积、以及长周期物料结算算法时，**核心计算块内部的数据类型，建议 100% 升级为 `LREAL`**，彻底依靠物理芯片的硬件位宽优势碾压舍入误差，免去复杂的软件补偿算法。