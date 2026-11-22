# 存钱 · 每月流水可视化设计稿

文件：

```text
hoshinoumi-cashflow-v35.9.html  交互设计稿
hoshinoumi-cashflow-v35.9.png   预览图
```

## 画板

```text
桌面：存钱页顶部 KPI + 近 12 个月流水图 + 本月分类
手机：390×844 存钱页 + 流水图 + 本月分类 + 底栏
```

## 交互

```text
近 12 / 6 个月切换
上个月 / 下个月
点击柱子选月份，KPI 和分类同步
桌面悬停 tooltip
空态切换
```

## 视觉

```text
收入：蓝色柱
支出：浅红柱
净结余：墨绿折线
分类：蓝色横向条形
金额仅主人可见
CNY
```

## API

```text
GET /api/savings/cashflow?months=12&month=YYYY-MM
```

## 版本

```text
v35.9.1.19  API
v35.9.1.20  桌面
v35.9.30.16 手机
```
