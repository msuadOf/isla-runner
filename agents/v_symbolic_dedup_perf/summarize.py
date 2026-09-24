from pathlib import Path
import json,statistics
root=Path(__file__).parent
rows={}
for line in (root/'results.jsonl').read_text().splitlines():
 x=json.loads(line);rows[x['kind'],x['clause'],x['rep']]=x
# harness调整时中断过一次；同一key使用最终日志对应的最后记录，原始记录保留。
(root/'results-final.json').write_text(json.dumps(list(rows.values()),indent=2))
lines=['# V 扩展去重符号执行性能测试','', '## 方法','', '同一 release isarch 副本，RV64/VLEN128/ELEN64，qfaufbv，8 worker。外层、路径与 SMT operation 的预算均为 60 秒；不固定运行态寄存器。HEAD 5f1a0de0 为重构前，新 IR 为未提交的三文件重构。每组交替顺序三轮，历史 IR 同机复跑一轮；保留原 workaround 的 strict=true 并更新 hash/源位置。测试串行运行，主机仍可能有外部负载。','', 'isla 源码有用户未提交修改，本次不重编译执行器；各组均使用同一个已复制二进制，hash 见 metadata.json。历史日志缺少足以复现的 wall-time 记录，因此历史速度比较使用旧 IR 在本次环境的复跑，不能把旧台账路径数当作速度。','', '## 结果','', '| 指令 | 版本 | 轮数 | wall 中位秒 | 完成路径中位数 | 成功路径中位数 | 最大 fork | 峰值 RSS 中位 MiB | 自然结束/超时 |','|---|---|---:|---:|---:|---:|---:|---:|---|']
for clause in ['MOVETYPEV','MASKTYPEI','VREV8_V','VIMCTYPE']:
 for kind,label in [('base','重构前'),('new','重构后'),('history','历史 IR 复跑')]:
  xs=[x for x in rows.values() if x['clause']==clause and x['kind']==kind and x['rep']<10]
  if not xs:continue
  med=lambda k:statistics.median(x[k] for x in xs)
  rss=statistics.median(int(x['time'].splitlines()[-1].split()[-1])/1024 for x in xs)
  lines.append(f"| {clause} | {label} | {len(xs)} | {med('wall'):.3f} | {med('paths'):g} | {med('success'):g} | {max(x['fork_max'] for x in xs)} | {rss:.0f} | {sum(x['exit']==0 for x in xs)}/{sum(x['exit']==124 for x in xs)} |")
lines+=['','60 秒超时行仅表示固定窗口吞吐，不能比较完整执行耗时；未输出最终 JSON 也不能按已完成路径声称完成指令覆盖。所有记录见 results-final.json，逐轮命令与日志位于 runs/。','', '## helper 隔离对照','', 'direct 以同一份新 IR 为基础，仅将 MOVETYPEV 一处 vector_select_masked 调用换回 isla_vector_select，保留新增 helper 定义和所有位置/符号顺序。']
for kind in ['direct','new']:
 xs=[x for x in rows.values() if x['clause']=='MOVETYPEV' and x['kind']==kind and x['rep']>=10]
 if xs:lines.append(f"- {kind}: {len(xs)} 轮，wall中位 {statistics.median(x['wall'] for x in xs):.3f}s，完成路径 {sorted(set(x['paths'] for x in xs))}，成功路径 {sorted(set(x['success'] for x in xs))}。")
lines+=['','## 结构与限制','', '- IR 结构审查：剔除源码位置与断言位置后，HEAD→重构仅新增一层 MOVETYPEV helper 调用，无新增数据相关 jump。历史 IR→HEAD 除源位置外一致。','- ControlFlowScope 哈希包含源位置/函数ID/PC，源码移动会改变受限分支采样；吞吐微差不能全部归于函数调用开销。','- 原正式 workaround hash 仍绑定历史 IR；部署重构 IR 前必须迁移对应 source regions 与 hash。本次未改正式配置或历史 output。','- 未做全量 V 扩展、extra_ops=false 或极限参数微基准；结果限定于当前生产配置和这四类指令。','- 未发现 SymbolicLength、ExecError 或 panic；外层超时属于预算截断。','', '独立审查详情见 review.md。']
(root/'report.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines[8:25]))
