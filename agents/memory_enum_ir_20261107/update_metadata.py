#!/usr/bin/env python3
"""按本轮实际来源及定向验证结果更新根仓版本记录，不写 gitlink。"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'output/memory-enum-20261107'
installed = json.loads((OUT/'installed.json').read_text())
checks = json.loads((OUT/'validation-checks.json').read_text())
path = ROOT/'specs/topic-version.json'
topic = json.loads(path.read_text())
if topic['updated'] != '2026-11-07':
    old = {k:topic[k] for k in ('components','ir','validation','publication','updated','status')}
    topic.setdefault('history', []).append(old)
else:
    assert topic['components']['isla']['commit'] == installed['isla_commit']
    assert topic['components']['sail-riscv']['commit'] == installed['model_commit']
topic['components']['isla'].update(commit=installed['isla_commit'],source_branch='feat/postprocess-enumeration')
topic['components']['sail-riscv'].update(commit=installed['model_commit'],source_branch='feat/sail-riscv-memory-by-model-20261022')
sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
topic['ir']={'path':'isla/rv64d.ir','sha256':sha(ROOT/'isla/rv64d.ir'),
             'provenance':f"d79d8b32模型普通严格检查与四配置SYMBOLIC重生，五入口及配置/命令/工具哈希见isla/ir/provenance/manifest.json（SHA-256 {sha(ROOT/'isla/ir/provenance/manifest.json')}）；RV64启用Svnapot/Svpbmt，RV32禁用；旧bf861b3e哈希与验收保留在history及历史报告"}
passed = all(c['exit']==0 for c in checks if 'superseded_by' not in c)
state = json.loads((OUT/'executeas/inspection.json').read_text())
passed = passed and state['state_ok'] and state['summary']['status']=='finished'
topic['status']='五入口IR已重生，来源哈希已核对；本轮定向验证'+('通过' if passed else '存在失败，见报告')+'；待发布'
topic['publication']={'pushed_this_round':False,'status':'待发布','component_remote_reachability':'本轮未做正式远端回读；旧publication只适用4d085b14/bf861b3e，见history',
                      'root_push_status':'not-run','git_write_operations':'not-run',
                      'pending':'Isla IR/provenance未提交；当前components.isla记录生成工具/执行器源码基准，后续IR提交及根仓gitlink由Claude处理'}
topic['updated']='2026-11-07'
topic['root_branch']='feat/memory-enum'
topic['working_root_base']='29aa47656e437d7f41e87d90a894edd125f429c2'
topic['validation']={'status':'targeted-pass' if passed else 'targeted-failures','date':'2026-11-07',
                     'report':'agents/memory_enum_ir_20261107/final-report.md',
                     'scope':'本轮实际程序和五入口的严格生成、永久IR、定向数值/状态、Schema Union、vstart、ExecuteAs、Make及汇编；不是新独立签收或全域验收',
                     'full_model_control_flow_coverage':'not-measured','hardware_replay':'not-run',
                     'limitations':['未重跑完整77浮点预算及全部访存/异常域',
                                    '未重跑F1新旧对照、三类Poison逐例复放及旧基线长尾；不把旧归因迁记到新模型',
                                    '新Svnapot/Svpbmt/非叶保留位专用运行语义测试未在本轮执行',
                                    '批量从旧T1改为T32，定向预算1200秒；不作为原7200秒性能对照',
                                    '未执行Git写操作和发布；远端可获取性未重新核实']}
path.write_text(json.dumps(topic,indent=2,ensure_ascii=False)+'\n')
print(topic['status'])
