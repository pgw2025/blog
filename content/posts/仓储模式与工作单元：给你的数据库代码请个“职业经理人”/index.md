---
title: "仓储模式与工作单元：给你的数据库代码请个“职业经理人”"
date: 2026-05-30T19:10:00+08:00
draft: false
images: ["/images/post/repo-uow-guide.jpg"]
tags: ["后端开发", "架构模式", "Repository", "Unit of Work", ".NET"]
categories: ["后端开发"]
series: ["现代后端架构系列"]
author: "GW"
summary: "直接在业务逻辑里写 SQL/LINQ 语句？那太乱了！仓储模式（Repository）和工作单元（Unit of Work）能让你的数据库操作变得井然有序。本文将用大白话带你搞懂这两个模式的底层逻辑与实战写法。"
---

# 仓储模式与工作单元：给你的数据库代码请个“职业经理人”

在写代码的时候，你是否遇到过这种情况：为了存一个订单，你在 Service 类里写了一大堆数据库操作代码。如果以后数据库换了（比如从 SQL Server 换到 MySQL），或者你想写个单元测试，发现代码纠缠在一起，根本拆不开。

这时候，你就需要 **仓储模式 (Repository)** 和 **工作单元 (Unit of Work)** 来救场了。

---

## 一、 仓储模式 (Repository)：专业的“仓库管理员”

### 1. 原理：别管货是怎么放的
想象你开了一家超市，你（业务逻辑层）想进一批可乐。你不需要亲自去仓库搬梯子找货，你只需要对**仓库管理员 (Repository)** 说：“给我拿 10 箱可乐”。

管理员知道可乐在 A 区还是 B 区，是用叉车还是手搬。**你只负责提要求，他负责拿货。**

### 2. 为什么要用它？
- **解耦**：业务代码里看不到任何数据库引擎的影子（如 SQL、Entity Framework）。
- **好测试**：你可以模拟一个“假管理员”，不需要真的连数据库也能跑测试。
- **好维护**：以后改了数据库表结构，只需要改管理员的拿货逻辑，不需要动业务逻辑。

---

## 二、 工作单元 (Unit of Work)：精明的“记账会计”

### 1. 原理：要么全成，要么全撤
仓库管理员只管拿货和放货，但如果一次业务涉及多个操作（比如：减库存 + 生成订单 + 扣余额），其中一个失败了怎么办？

**工作单元 (UoW)** 就像一个会计。他看着所有管理员干活：
- 管理员 A 拿了货。
- 管理员 B 记了账。
- 管理员 C 准备收钱。
如果中间有人掉链子，会计会大喊一声：“全部撤销（回滚）！”如果大家都干完了，会计最后点点头：“**保存 (Save)**”，这笔交易才算数。

---

## 三、 代码实现 (.NET 示例)

### 1. 定义管理员接口 (IRepository)
```csharp
public interface IOrderRepository
{
    Order GetById(int id);
    void Add(Order order);
}
```

### 2. 管理员的具体干活流程
```csharp
public class OrderRepository : IOrderRepository
{
    private readonly MyDbContext _context;
    public OrderRepository(MyDbContext context) => _context = context;

    public void Add(Order order) => _context.Orders.Add(order);
    public Order GetById(int id) => _context.Orders.Find(id);
}
```

### 3. 定义会计接口 (IUnitOfWork)
```csharp
public interface IUnitOfWork : IDisposable
{
    IOrderRepository Orders { get; }
    IUserRepository Users { get; }
    int Complete(); // 最后的统一保存
}
```

### 4. 会计的具体实现 (UnitOfWork)
这就是会计真正“管账”的地方。他持有所有的管理员（仓储）和账本（DbContext）。

```csharp
public class UnitOfWork : IUnitOfWork
{
    private readonly MyDbContext _context;

    public UnitOfWork(MyDbContext context)
    {
        _context = context;
        // 在这里实例化所有的管理员，并让他们共用同一个账本（context）
        Orders = new OrderRepository(_context);
        Users = new UserRepository(_context);
    }

    public IOrderRepository Orders { get; private set; }
    public IUserRepository Users { get; private set; }

    public int Complete()
    {
        // 只有这里调用了 SaveChanges，之前的操作才会真正入库
        return _context.SaveChanges();
    }

    public void Dispose()
    {
        _context.Dispose();
    }
}
```

---

## 四、 怎么用？(Service 层调用)

在大白话的世界里，你的业务逻辑现在变成了这样：

```csharp
public class OrderService
{
    private readonly IUnitOfWork _uow;
    public OrderService(IUnitOfWork uow) => _uow = uow;

    public void CreateOrder(Order order)
    {
        // 1. 让订单管理员加个订单
        _uow.Orders.Add(order);
        
        // 2. 让用户管理员改下积分
        var user = _uow.Users.GetById(order.UserId);
        user.Points += 10;

        // 3. 最后让会计统一点头
        _uow.Complete(); 
    }
}
```

---

## 五、 实用技巧与注意事项

### 1. EF Core 本身就是 UoW 吗？
没错。其实 `DbContext` 本身就实现了仓储和工作单元模式。
- `DbSet<T>` 是仓储。
- `SaveChanges()` 是工作单元的提交。
**那为什么要再封一层？** 为了让代码更纯粹，完全不依赖具体的数据库框架，方便后期维护和多数据库适配。

### 2. 不要搞“泛型仓储”过度设计
很多新手喜欢写一个 `BaseRepository<T>` 处理所有的增删改查。
**建议**：如果业务简单，可以这么搞；如果业务复杂，还是建议为每个核心业务写专门的接口，这样代码意图更清晰。

### 3. 生命周期管理
在 .NET DI 容器中，`UnitOfWork` 应该设置为 **Scoped**（一次请求一个实例），确保所有的管理员共用同一个数据库上下文。

---

## 六、 总结

- **仓储模式**：把数据存取逻辑藏起来。
- **工作单元**：把多个存取操作打包成一个事务。

用了这两个模式，你的后端代码将从“杂乱的脚本”进化为“优雅的工业级架构”。

> （注：本文由 GW 整理。写出整洁的代码，就是给自己未来的头发买保险！）
