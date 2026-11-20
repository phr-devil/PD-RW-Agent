
### 任务 T1_MCS｜MCS-HEMO-26（耳内多模态 vs 同源血压参考）
决策时点与可见证据：决策时点 2026-11-05（02c 之后）。可见证据：dev_audit/{oa_verification_stats.json, ob_reference_recheck.json, subject_level_deltas.csv, n1r_verification.json}；STATE 观测 O3/O8/O12/O22；U9/U10/U11 未决。授权：DEV 只读描述统计，禁止拟合/新数据/SEALED。

**方案 A**
- 推荐为下一实验：`MCS-P1-CROSS-SESSION-ICC`
- 附带标记：无
- 显式标志：无
- 探针级 finding：无

**方案 B**
- 推荐为下一实验：（无：没有可作为下一实验的候选）
- 附带标记：已完成、仅作历史证据：MCS-P1-CROSS-SESSION-ICC；需新授权才可执行：MCS-P3-NEW-INSTRUMENTED-DATA；仅探索性：MCS-P2-DOC-CHECK、MCS-P3-NEW-INSTRUMENTED-DATA
- 显式标志：no_executable_next_probe=true（有合法可区分探针，但当前都不能执行）
- 探针级 finding：MCS-P2-DOC-CHECK：PROBE_UNIT_NOT_INDEPENDENT

**方案 C**
- 推荐为下一实验：`MCS-P1-CROSS-SESSION-ICC`
- 附带标记：仅探索性：MCS-P2-DOC-CHECK、MCS-P3-NEW-INSTRUMENTED-DATA
- 显式标志：无
- 探针级 finding：MCS-P2-DOC-CHECK：PROBE_UNIT_NOT_INDEPENDENT


### 任务 T2_RCT｜RCT-CONTACT-26（触觉材料 vs 传感器实例）
决策时点与可见证据：决策时点 2026-11-07（V1-R 之后）。可见证据：dev_audit/{contrast_table.json, v1r_direction.json, V1R_PREREG.json}；STATE 标记 R1_BRANCH=CLOSED_BY_USER_DECISION、NO_USEFUL_NEXT_PROBE=TRUE。授权：DEV 只读、零拟合；新真值/新数据需单独授权。

**方案 A**
- 推荐为下一实验：（无：没有可作为下一实验的候选）
- 附带标记：已完成、仅作历史证据：RCT-P1-DEV-SLOPE-RERUN、RCT-P2-SENSOR-SWAP；需新授权才可执行：RCT-P3-EXTERNAL-MODULUS-PRESS
- 显式标志：no_executable_next_probe=true（有合法可区分探针，但当前都不能执行）
- 探针级 finding：无

**方案 B**
- 推荐为下一实验：`RCT-P1-DEV-SLOPE-RERUN`
- 附带标记：无
- 显式标志：无
- 探针级 finding：无

**方案 C**
- 推荐为下一实验：`RCT-P1-DEV-SLOPE-RERUN`
- 附带标记：无
- 显式标志：无
- 探针级 finding：无


### 任务 T3_POPU｜项目 48 PoPu（床垫下稀疏压力阵列恢复）
决策时点与可见证据：决策时点 2026-11-20（RUN-004 之后、RUN-005 之前）。可见证据：DEV/runs/RUN-002..004/metrics.json、protocol/PROTO-POPU-POSTUREVALUE-v4-DEV004.json、STATE。授权：本地 CPU 有界 DEV；SEALED/新下载需授权。

**方案 A**
- 推荐为下一实验：`POPU-P1-POSTURE-VARIANTS`、`POPU-P2-RELIABILITY-GATE`
- 附带标记：无
- 显式标志：无
- 探针级 finding：POPU-P1-POSTURE-VARIANTS：PROBE_UNIT_NOT_INDEPENDENT

**方案 B**
- 推荐为下一实验：`POPU-P1-POSTURE-VARIANTS`、`POPU-P2-RELIABILITY-GATE`
- 附带标记：无
- 显式标志：无
- 探针级 finding：无

**方案 C**
- 推荐为下一实验：`POPU-P2-RELIABILITY-GATE`
- 附带标记：已完成、仅作历史证据：POPU-P1-POSTURE-VARIANTS；需新授权才可执行：POPU-P3-SECOND-LIBRARY
- 显式标志：无
- 探针级 finding：POPU-P1-POSTURE-VARIANTS：PROBE_UNIT_NOT_INDEPENDENT
