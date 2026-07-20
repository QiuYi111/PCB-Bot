# pcbflow 编排工具与 PCB 核心 Skill 接入设计

## 目标

为 PCB 项目提供一个可重复、可缓存、可验收的本地流程入口，统一执行
Circuit-Synth/KiCad 分析、Gerber 检查、EMC/热分析、跨文件核对和制造发布
前检查。工具不修改 KiCad 源文件，只生成带 manifest 的分析产物和门禁报告。

## 设计决策

1. 工具放在当前项目内，以 Python 标准库为核心，避免新增网络依赖。
2. 分析器通过配置的脚本路径调用；不同机器缺少 KiCad CLI、SPICE 或数据手册
   时，记录为 `blocked`/`not_performed`，不能静默跳过。
3. 每次运行生成 `analysis/pcbflow/<run_id>/`，以输入文件 SHA256 做缓存和溯源。
4. 状态分为 `pass`、`warning`、`blocked`、`not_performed`；只有没有 blocker 且
   所有必需步骤完成时，才允许输出 `fab_ready`。
5. 将电机负载、电源电流、保险丝和主电源走线等领域规则放进可配置的
   `pcbflow.json`，而不是硬编码到分析器。

## 命令接口

```text
pcbflow preflight --project <path> [--target jlcpcb]
pcbflow review --project <path> [--target jlcpcb] [--full]
pcbflow release --project <path> [--target jlcpcb]
pcbflow status --run <run-dir>
```

`review` 运行可用的原理图、PCB、跨文件、Gerber、EMC 和热分析，并执行原生
KiCad DRC；`release` 在 review 的 `fab_ready` gate 通过且源文件 SHA256 未变化
后生成发布 zip；`preflight` 只检查环境、输入文件和可用性。

## 产物契约

```text
analysis/pcbflow/<run_id>/
  manifest.json
  preflight.json
  schematic.json       # 可用时
  pcb.json              # 可用时
  cross.json            # 两者都可用时
  gerbers.json          # 存在 Gerber 时
  emc.json              # 原理图和 PCB 都可用时
  thermal.json          # 原理图和 PCB 都可用时
  gate_report.json
  report.md
```

每个 gate 包含 `id`、`severity`、`status`、`evidence`、`recommendation`。

## 首批门禁

- `input_files`: 找到 KiCad 源文件，且未将 generated/release 文件误当作唯一源。
- `toolchain`: 记录 Python、KiCad CLI、SPICE、数据手册目录的可用性。
- `schematic_analysis` / `pcb_analysis` / `cross_analysis`: 记录 analyzer 结果；
  analyzer warning 不等价于 native DRC pass。
- `power_budget`: 有电机电压、电阻、数量和相数时计算最大 5V 电流。
- `layer_stack`: 源 PCB 与 Gerber 层数一致；目标为 JLC 时必须包含 In1/In2。
- `gerber_analysis`: 铜层、阻焊、丝印、Edge.Cuts、PTH/NPTH 由 Gerber analyzer 检查。
- `native_drc`: 若 KiCad CLI 不可用，状态必须为 `blocked`，不可报 pass。
- `manufacturer_mapping`: 未匹配器件、手工焊接器件和封装替换必须列出。

## Skill 接入

`pcb` 作为入口，在新建、审查、制造准备任务开始时先调用
`pcbflow preflight/review`；`kicad-happy` 继续负责细节分析，并消费
`pcbflow` 的 run manifest。`circuit-synth` 在生成 KiCad 文件后触发同一流程。
全局 skill 只增加短路由和状态要求，详细实现放在
项目工具和 references 中，保持 SKILL.md 小于 200 行。

## 验证策略

- 单元测试覆盖路径发现、命令构造、SHA256、门禁聚合和电机电流计算。
- 用当前 24V 项目运行一次 `preflight` 和一次 `review`。
- 验证 `kicad-cli` 存在但 DRC 崩溃时仍报告 blocker；SPICE、datasheet、lifecycle
  缺失时报告为明确缺口。
- 验证工具不会修改 `.kicad_sch`、`.kicad_pcb` 或 `.kicad_pro`。
