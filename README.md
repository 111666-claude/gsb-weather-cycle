# weather-cycle

天气循环：随机转移、持续时间与属性修正，只用 Python 标准库。

```
python3 -m weathercycle.cli --sample table
python3 -m weathercycle.cli --sample modifier
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **权重先归一化**：每一行的权重和必须是 1（不足要按比例补齐）。`--sample table` 里 sunny 行按口径是
  `sum=1.00`，现在给 `sum=0.90`（导致 roll 落在 0.9~1.0 时永远选中最后一项）。
- **属性修正**：雨天移动速度 ×0.8（减速）、雪天 ×0.7，其它 ×1.0。
  `--sample modifier` 按口径是 `rain_modifier=0.80`，现在给 `1.20`。
- **持续时间**：每种天气的持续时长在配置范围内随机（最小值到最大值之间），不是固定值。
- 不变量：每行权重归一化后和为 1；同一个种子给出同一串天气；修正系数只影响速度、不改变撞击判定；
  同一批转移重复回放结果相同。
- 规模：10 万个 NPC 每秒 10 万次天气查询 1 秒内完成，内存 O(状态数)。

## 实现口径

- `pick` 先把每行权重归一化（和为 1），再按累计分布采样，尾部不再恒落最后一项。
- `speed_modifier`：雨天 0.8、雪天 0.7、其它 1.0，只影响速度。
- `duration`：在 `DURATIONS` 配置的 [最小, 最大] 范围内随机。
- `simulate`：同一种子回放同一串天气。

## 输出

```
state=rain sum=1.00
state=snow sum=1.00
state=sunny sum=1.00
rain_modifier=0.80 snow_modifier=0.70
```

## 目录

```
weathercycle/cycle.py   转移与修正
weathercycle/cli.py     命令行入口
tests/                  unittest 用例
```
