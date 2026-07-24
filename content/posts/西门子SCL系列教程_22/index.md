---
title: "第二十二章：SCL 工业报警系统设计与百台设备级环形 FIFO 历史存储器"
date: 2026-07-24T12:50:00+08:00
draft: false
tags: ["工控技术", "PLC 编程", "西门子","SCL编程"]
categories: ["工业自动化","PLC","西门子SCL系列教程"]
author: "Will"
summary: "在上一章中，我们一起攻克了模块化编程的至高阵地，学会了用标准 UDT 和全局库去构建高内聚的“标准设备对象”。"
---


在上一章中，我们一起攻克了模块化编程的至高阵地，学会了用标准 UDT 和全局库去构建高内聚的“标准设备对象”。

今天，我们要去攻克任何大中型自动化项目中最核心的安全长城——**工业级报警系统（Industrial Alarm System）**。

在真实的工厂车间里，当设备发生异常（如气缸卡死、电机热过载、管道超压）时，PLC 必须在一毫秒内做出以下雷霆响应：
1.  **捕捉并锁存（Latch）**：哪怕物理故障信号只闪烁了 10ms，PLC 也必须牢牢锁死该报警，绝对不能让它悄无声息地溜走。
2.  **拉响警铃（Siren）**：驱动中控室的物理警笛，直到操作员按下“消音确认（Mute / ACK）”按钮。
3.  **HMI 状态流转**：将报警推送到触摸屏（HMI / SCADA）上。报警必须有明确的生命周期状态（已触发未确认、已确认未消除、已消除未复位）。
4.  **历史记录归档（FIFO History Log）**：在 PLC 内部的工作内存中，以 **先进先出（FIFO）环形存储器** 的形式，精准记录下最近发生的所有报警历史事件（包括哪个设备、哪个通道、什么时间、是触发还是恢复）。

如果现场有 100 台设备，每台设备有 8 个报警点。如果你的程序里散落着 800 个零散的报警位，你的逻辑就会彻底失控。

今天，师父将带你拆解大厂级报警管理的“生命周期哲学”，构建高效的“二进制位打包 HMI 通信模型”，并手写一个生产级的**“100台设备智能报警管理与 50 组 DTL 时间戳环形历史存储系统（SCL）”**。

---

## 1. 工业报警管理的生命周期哲学

在成熟的工业工程中，一个报警绝对不是一个简单的“1 和 0”布尔变量。它拥有一个严密的 **有限状态生命周期**：

```
                    工业级报警生命周期状态机模型
                    
                       物理故障产生
                            │
                            ▼
              ┌──────────────────────────┐
              │     1. 已触发 / 未确认   ├───────┐ (物理警笛拉响，HMI红灯闪烁)
              └─────────────┬────────────┘       │
                            │                    │
                操作员按下  │ ACK / 确认         │ 物理故障自动恢复
                (消音/确认) │                    │ (但操作员未确认)
                            ▼                    ▼
              ┌──────────────────────────┐ ┌──────────────────────────┐
              │     2. 已确认 / 挂起     │ │    3. 已消除 / 未确认    │
              └─────────────┬────────────┘ └─────────────┬────────────┘
                            │                            │
            物理故障自动恢复│                            │ 操作员按下 ACK
                            │                            │
                            ▼                            ▼
              ┌──────────────────────────────────────────┐
              │            4. 完全恢复 / 归档            │ (报警从活动列表中消失，
              │            (复位并写入历史)              │  写入历史 FIFO 数据区)
              └──────────────────────────────────────────┘
```

为了完美描述这个生命周期，我们在 UDT 中为每一个报警通道设计了三个核心控制位：
*   `.bTrigger`：物理传感器输入的当前实时触发电平。
*   `.bLatched`：报警锁存状态（只要 `#bTrigger` 闪过一次，就锁死为 `TRUE`）。
*   `.bAcked`：操作员确认状态（按下 ACK 确认按钮后置为 `TRUE`，静音警笛）。

---

## 2. 100 台设备报警数组的二进制 HMI 优化模型

如果我们在 SCL 内部，为 HMI 定义了 800 个散落的 `Bool` 报警变量。
当触摸屏（SCADA）去和 PLC 进行以太网 Profinet 通信时，它必须在后台对这 800 个不连续的 Bool 变量地址进行高频轮询。**这会瞬间吃满 PLC 以太网芯片的背板通信总线，造成触摸屏画面严重滞后卡顿。**

### 2.1 大厂黄金规范：二进制位打包（Bit Packing）

为了追求极致的通信效率，我们拒绝传输零散的 Bool。
*   我们给每台设备分配一个 **`WORD`（字，16位）** 或 **`DWORD`（双字，32位）** 作为报警字。
*   将设备内部的各种报警（如过载、超时、粘连），通过 SCL 的 **Slice（`.X`）** 片段寻址技术，强行写入这个报警字的对应 Bit 位上。
*   **HMI 端**：只建立一个 `Array[1..100] of Word` 的连续变量通信包。**一键通信下载，整个过程只需一个通信事务周期即可全部带走！**

我们先在博途“PLC数据类型”中建立两套 UDT：

#### 1. UDT_DeviceAlarm (单个设备的报警管理核心)
```scl
TYPE "UDT_DeviceAlarm"
VERSION : 0.1
   STRUCT
      bTrigger_Overload : Bool;  // 1. 物理触发源：热过载
      bTrigger_Timeout : Bool;   // 2. 物理触发源：动作超时
      bTrigger_Interlock : Bool; // 3. 物理触发源：安全连锁断开
      
      bLatched : Bool;           // 报警已被自锁标志
      bAcked : Bool;             // 报警已被消音确认标志
      wAlarmWord : Word;         // 二进制报警打包字（第0位:过载, 第1位:超时, 第2位:连锁）
   END_STRUCT
END_TYPE
```

#### 2. UDT_AlarmEvent (用于写入 FIFO 历史日志的单条报警记录)
因为要记录时间，我们选用西门子高精度的系统时间类型 **`DTL`**（占用 12 字节，包含年、月、日、时、分、秒、纳秒）：

```scl
TYPE "UDT_AlarmEvent"
VERSION : 0.1
   STRUCT
      iDeviceID : Int;           // 发生报警的设备编号 (1..100)
      iEventState : Int;         // 事件状态代码 (1:触发, 2:确认, 3:恢复)
      iAlarmType : Int;          // 报警类型代码 (1:过载, 2:超时, 3:连锁)
      dtTimestamp : DTL;         // 高精度系统时钟时间戳
   END_STRUCT
END_TYPE
```

---

## 3. 历史报警记录：先进先出（FIFO）环形存储器

PLC 的工作内存（RAM）极其珍贵，我们不可能在 PLC 内部像 SQL 数据库那样无限制存储几十万条报警。
我们通常在 PLC 数据工作内存中，开辟一个固定大小（如 50 组）的 **环形 FIFO 存储数组**：
*   当发生新报警事件时，数据被推入（PUSH）数组的尾部。
*   如果 50 个存储空间全满，**最老的一条历史记录会被自动挤出、覆盖销毁**（先进先出）。

```
           PLC 环形 FIFO 历史存储器内存演练图 (Size = 5)
           
  上电初始空闲:   [ 空 ] [ 空 ] [ 空 ] [ 空 ] [ 空 ]  --> 指针 iWritePointer = 1
  
  发生第1次事件:  [ 事件1 ] [ 空 ] [ 空 ] [ 空 ] [ 空 ] --> 指针 iWritePointer = 2
  
  连续发生5次:    [ 事件1 ] [ 事件2 ] [ 事件3 ] [ 事件4 ] [ 事件5 ] --> 数组写满
  
  第6次事件发生:  [ 事件6 (覆盖事件1) ] [ 事件2 ] [ 事件3 ] [ 事件4 ] [ 事件5 ] --> 循环回滚覆盖！
```

*高级硬件寻址优点*：这种环形队列不进行大面积的物理内存“平移拷贝”（平移内存极度消耗 CPU 扫描时钟）。我们**只需在后台移动写指针（Write Pointer），进行循环覆盖寻址即可**，效率达到最高。

---

## 4. 工业级综合案例：百台设备智能报警中心与环形历史存储系统

现在，我们把 100 台设备的报警字位打包、生命周期自锁、全局消音、以及高精度 `DTL` 系统时间戳环形 FIFO 存储器全部融合成一个高强度的全局 FB —— **`FB_AlarmCenter`**。

### 4.1 步骤一：块接口声明（FB_AlarmCenter）

（我们在静态变量区声明 50 个元素的历史归档数组，并在常数区定死所有状态和事件代码）：

```
VAR_INPUT
    bHmi_GlobalAck : Bool;      // 触摸屏一键全局消音确认按钮 (ACK)
    bPhysicalReset : Bool;      // 控制箱物理复位解除自锁按钮 (Reset)
END_VAR

VAR_OUTPUT
    bOut_Siren : Bool;          // 物理输出：控制室警笛驱动线圈 (DO)
    iActiveAlarmsCount : Int;   // 状态显示：当前全厂活动的报警总数
    iHistoryLogPointer : Int;   // 诊断：当前 FIFO 历史写入指针位置
END_VAR

VAR_IN_OUT
    arrDevices : Array[1..100] of "UDT_DeviceAlarm"; // 核心：100台设备的报警数据源
END_VAR

VAR
    // ==========================================
    // 静态变量区 (Private STAT)
    // ==========================================
    // 1. 报警历史 FIFO 环形缓冲区 (存储最近 50 条历史记录)
    arrHistoryLog : Array[0..49] of "UDT_AlarmEvent";
    iWritePointer : Int := 0;   // 环形写指针
    
    // 2. 状态防抖与边沿检测标志 (必须为 Static)
    arrPrevTrigger_Overload : Array[1..100] of Bool; // 记录上一个周期的过载状态（用于捕捉上升/下降沿）
    arrPrevTrigger_Timeout : Array[1..100] of Bool;
    arrPrevTrigger_Interlock : Array[1..100] of Bool;
END_VAR

VAR_TEMP
    i : Int;                    // 遍历计数
    dtSystemTime : DTL;         // 临时高精度系统时间戳
    iRetTimeVal : Int;          // 读取系统时间系统函数返回值
    bSirenActive_Temp : Bool;   // 警笛激活临时变量
    bEdge_FP : Bool;            // 边缘判定辅助
    bEdge_FN : Bool;
END_VAR

VAR_CONST
    // ==========================================
    // 标准 UDT 状态常数
    // ==========================================
    EV_TRIGGER : Int := 1;      // 事件：报警触发
    EV_ACKED : Int := 2;        // 事件：操作员确认
    EV_CLEARED : Int := 3;      // 事件：报警物理消除恢复
    
    ALARM_OVERLOAD : Int := 1;  // 报警：热过载
    ALARM_TIMEOUT : Int := 2;   // 报警：超时
    ALARM_INTERLOCK : Int := 3; // 报警：连锁断开
END_VAR
```

---

### 4.2 步骤二：SCL 核心代码实现

```scl
FUNCTION_BLOCK "FB_AlarmCenter"
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
BEGIN
	// ==========================================
	// 1. 获取 CPU 硬件实时系统时间戳 (DTL 格式)
	// ==========================================
	#iRetTimeVal := RD_SYS_T(#dtSystemTime); // 读取系统时间，写入临时的 dtSystemTime 中
	
	// ==========================================
	// 2. 全局状态初始化
	// ==========================================
	#bSirenActive_Temp := FALSE;
	#iActiveAlarmsCount := 0;
	
	// ==========================================
	// 3. 核心 100 台设备报警循环处理 (FOR 结构)
	// ==========================================
	FOR #i := 1 TO 100 DO
	    
	    // ------------------------------------------
	    // A. 二进制报警位打包字实时改写 (Slice X 寻址)
	    // HMI 报警字：第0位过载, 第1位超时, 第2位连锁
	    // ------------------------------------------
	    #arrDevices[#i].wAlarmWord.X0 := #arrDevices[#i].bTrigger_Overload;
	    #arrDevices[#i].wAlarmWord.X1 := #arrDevices[#i].bTrigger_Timeout;
	    #arrDevices[#i].wAlarmWord.X2 := #arrDevices[#i].bTrigger_Interlock;
	    
	    // ------------------------------------------
	    // B. 自锁与生命周期状态转移机 (核心算法)
	    // ------------------------------------------
	    // 判断该设备是否有任意物理故障触发
	    IF #arrDevices[#i].bTrigger_Overload OR 
	       #arrDevices[#i].bTrigger_Timeout OR 
	       #arrDevices[#i].bTrigger_Interlock THEN
	        
	        // 触发自锁：只要闪烁过，立刻锁死报警标志
	        IF NOT #arrDevices[#i].bLatched THEN
	            #arrDevices[#i].bLatched := TRUE;
	            #arrDevices[#i].bAcked := FALSE; // 新故障进来，重置已确认标志（警笛重响）
	        END_IF;
	        
	        #iActiveAlarmsCount := #iActiveAlarmsCount + 1; // 激活报警计数自增
	    END_IF;
	    
	    // ------------------------------------------
	    // C. 物理警笛激活判定
	    // 规则：只要全厂存在任何“触发了，但操作员未按下确认”的报警，必须拉响警笛
	    // ------------------------------------------
	    IF #arrDevices[#i].bLatched AND (NOT #arrDevices[#i].bAcked) THEN
	        #bSirenActive_Temp := TRUE;
	    END_IF;
	    
	    // ------------------------------------------
	    // D. 响应 HMI 一键全局确认 (Mute / ACK)
	    // ------------------------------------------
	    IF #bHmi_GlobalAck THEN
	        // 如果当前设备处于未确认报警中，将其标定为“已确认”
	        IF #arrDevices[#i].bLatched AND (NOT #arrDevices[#i].bAcked) THEN
	            #arrDevices[#i].bAcked := TRUE;
	            
	            // ------------------------------------------
	            // 核心高阶：写入 FIFO 报警历史区（事件：ACK 确认）
	            // ------------------------------------------
	            #arrHistoryLog[#iWritePointer].iDeviceID := #i;
	            #arrHistoryLog[#iWritePointer].iEventState := #ST_FAULT; // 已确认
	            #arrHistoryLog[#iWritePointer].dtTimestamp := #dtSystemTime;
	            
	            // 写指针自增 1，如果到了 50，回滚到 0 实现环形循环覆盖
	            #iWritePointer := (#iWritePointer + 1) MOD 50;
	        END_IF;
	    END_IF;
	    
	    // ------------------------------------------
	    // E. 响应控制箱物理复位 (Reset)
	    // 规则：只有在物理故障已经恢复、且已被确认过的前提下，才允许彻底复位解除自锁
	    // ------------------------------------------
	    IF #bPhysicalReset THEN
	        // 判断是否所有故障物理源都已恢复
	        IF NOT (#arrDevices[#i].bTrigger_Overload OR 
	                #arrDevices[#i].bTrigger_Timeout OR 
	                #arrDevices[#i].bTrigger_Interlock) THEN
	                
	            IF #arrDevices[#i].bLatched THEN
	                #arrDevices[#i].bLatched := FALSE;
	                #arrDevices[#i].bAcked := FALSE;
	            END_IF;
	        END_IF;
	    END_IF;
	    
	    // ------------------------------------------
	    // F. 高阶：全自动边沿捕捉 -> 写入 FIFO 报警历史 (事件：触发/恢复)
	    // ------------------------------------------
	    // 以过载通道为例：捕捉过载启动的上升沿 (物理触发)
	    IF #arrDevices[#i].bTrigger_Overload AND (NOT #arrPrevTrigger_Overload[#i]) THEN
	        #arrHistoryLog[#iWritePointer].iDeviceID := #i;
	        #arrHistoryLog[#iWritePointer].iAlarmType := #ALARM_OVERLOAD;
	        #arrHistoryLog[#iWritePointer].iEventState := #EV_TRIGGER; // 1: 触发
	        #arrHistoryLog[#iWritePointer].dtTimestamp := #dtSystemTime;
	        #iWritePointer := (#iWritePointer + 1) MOD 50; // 环形滚动
	    END_IF;
	    
	    // 捕捉过载恢复的下降沿 (物理消除)
	    IF NOT #arrDevices[#i].bTrigger_Overload AND #arrPrevTrigger_Overload[#i] THEN
	        #arrHistoryLog[#iWritePointer].iDeviceID := #i;
	        #arrHistoryLog[#iWritePointer].iAlarmType := #ALARM_OVERLOAD;
	        #arrHistoryLog[#iWritePointer].iEventState := #EV_CLEARED; // 3: 消除
	        #arrHistoryLog[#iWritePointer].dtTimestamp := #dtSystemTime;
	        #iWritePointer := (#iWritePointer + 1) MOD 50;
	    END_IF;
	    
	    // 同步刷新历史状态 (用于下个扫描周期的沿判定)
	    #arrPrevTrigger_Overload[#i] := #arrDevices[#i].bTrigger_Overload;
	    #arrPrevTrigger_Timeout[#i] := #arrDevices[#i].bTrigger_Timeout;
	    #arrPrevTrigger_Interlock[#i] := #arrDevices[#i].bTrigger_Interlock;
	    
	END_FOR;
	
	// ==========================================
	// 4. 汇总输出驱动
	// ==========================================
	#bOut_Siren := #bSirenActive_Temp; // 驱动物理警笛线圈
	#iHistoryLogPointer := #iWritePointer; // 输出写指针给 HMI 监控
	
END_FUNCTION_BLOCK
```

---

## 5. 深度解剖实战代码的“工业级安全与网络优化思维”

这套百台设备级的智能报警系统，融合了大厂级大型项目设计中极其宝贵的工程防错理念。

### 5.1 环形指针回滚算法 `MOD 50` 的数学美学（第 52 行）
在代码中，每次向 FIFO 写入事件后，我们执行了这一行：
`#iWritePointer := (#iWritePointer + 1) MOD 50;`
这是环形队列中最高效、最不易越界的硬件回滚算法。
*   当 `#iWritePointer` = `48` 时：`(48 + 1) MOD 50` = `49`；
*   当 `#iWritePointer` = `49` 时：`(49 + 1) MOD 50` = `0`。
**指针在没有任何 `IF-ELSE` 条件跳转的情况下，自动回滚到 0 号物理空间，实现了对最老历史数据的自动覆盖。** 这对于 PLC 这种极度讲究扫描时间的实时系统，性能极高。

---

### 5.2 精准防抖与毫秒级时钟记录（第 13 行）
我们使用了西门子内置高精度读取系统时间指令 `RD_SYS_T`，将读取到的 `DTL` 直接原封不动赋给 `#arrHistoryLog[#iWritePointer].dtTimestamp`。
*底层物理机制*：
这不仅能精准记录到当前发生的年、月、日。更强大的在于，`DTL` 的底层带有**毫秒和纳秒级时钟计数**。这对于事故后的分析具有无可替代的物理闭环意义（例如：可以精准判定 1 号和 2 号泵在跳闸时，到底是哪一个先发生故障、相差了多少毫秒）。

---

## 6. 常见错误与避坑指南 (Senior Tips)

### 6.1 错误一：误将“临时局部变量”作为边沿锁存标志

在第六部分，我们写下了这一行：
`#arrPrevTrigger_Overload[#i] := #arrDevices[#i].bTrigger_Overload;`
有些徒弟在写 SCL 边沿判定时，贪图方便，把 `arrPrevTrigger_Overload` 声明在了 `VAR_TEMP` 临时区。

*致命后果*：
由于 `TEMP` 区的局部内存会在每个周期结束后被系统彻底收回销毁。下一个周期，这个变量的值是随机的垃圾数据。这会导致你的**边沿判定在每个周期发生严重的误触发**，在后台 FIFO 存储区内疯狂塞满无用的假历史记录，甚至导致 PLC 的工作内存暴涨瘫痪。
**铁律：任何用于边沿检测、沿判定的“历史旧值变量（Prev）”，必须无条件声明在 `VAR`（Static 静态变量区）中！**

---

### 6.2 错误二：HMI 高频频繁轮询报警 Bool 位导致 CPU 通信总线瘫痪
有些徒弟在做 HMI 报警配置时，直接把 PLC 内部那 300 个 `stDevices[i].bTrigger_Overload` 挂到了 HMI 报警表中。
这会导致 SCADA 通信负荷暴增，PLC 的 Profinet 通信连接可能直接中断。
**标准化设计**：
**如本章 3.1 节所示，利用 SCL 将报警点通过 Slice 打包到设备唯一的 `wAlarmWord`（字）中。在 HMI 报警表中，全部定义为“字报警”。通过位偏移（Bit 0、Bit 1）自动定位到具体报警，实现通信压力的 16 倍大瘦身！**

---

## 7. 课后练习

请独立思考并完成以下两个极富工业级报警系统设计深度的高阶练习：

### 练习 1：增加“报警防抖延迟”过滤器 (SCL + 定时器集成)
在现场，有些低压力、低温度报警经常由于模拟量干扰发生“瞬间闪烁报警”（如低于下限 1 毫秒又恢复正常）。
请升级我们的 UDT 和 FB 算法：
*   在 `UDT_DeviceAlarm` 内部增加一个多重背景定时器实例 `tonFilter : TON_TIME;`。
*   修改 SCL 循环：物理故障必须**持续存在 1.5 秒以上**，才允许正式置位 `#arrDevices[#i].bTrigger_Overload` 并触发后续的自锁与 FIFO 日志写入。

### 练习 2：万能报警历史 FIFO 队列检索与一键清除
我们的 FIFO 队列深度为 50 条。由于属于环形滚动，写指针 `#iWritePointer` 会不断递增覆盖。
请编写一个 SCL FC，对该报警历史区进行检索和整理：
*   当操作员在 HMI 上按下“清除报警历史”按钮时，一键使用 `FILL_BLK` 指令将 `arrHistoryLog` 数组完全清空，并将写指针归零。
*   *高阶挑战*：如何通过编写 SCL，实现把当前 50 条历史记录，按照“发生的时间先后顺序”重新排列输出？

---

## 总结

这一章，我们彻底征服了西门子 SCL 编程、乃至整个工业控制安全领域中最核心的积木——**工业级报警管理系统与高精度 FIFO 环形历史存储器设计**。

我们不仅在软件语法层级掌握了它，更从大厂级报警“生命周期（Trigger-Ack-Clear-Reset）”的高度，看清了如何利用自锁、确认机制完成完整的安全闭环；剖析了“HMI 字报警位打包”在优化系统通信总线负载上的关键作用；掌握了利用数学 `MOD` 算法构建高速、零内存平移拷贝的“环形写指针队列”，并共同写出了一个高集成、毫秒级 DTL 时间戳、自动滚动覆盖的“100台设备智能报警管理中心”。

请记住，**高超的安全系统设计，是把现场一切未知的危险状态，用密不透风的时间和数据格网进行死死卡住。写好每一行自锁判定，防住每一个随机沿，你写的程序才能在现场危险发生的一瞬间，稳如磐石。**

下一章，我们将正式进入 SCL 编程中，控制计算机离散时间与物理世界连续时间交互的最核心、最经典，也是各大项目必用的物理级演练阵地：**《SCL控制算法一阶低通滤波实现与动态时间常数补偿》**。

加油，下期见！