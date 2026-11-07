#!/usr/bin/env python3
"""沿用合流严格生成器，把本轮原始输出放到 output。"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'agents/float_memory_merge_20261103/validation'))
import generate
# 原生成器除输出根目录外保持不变；不复用旧缓存。
generate.HERE = ROOT / 'output/memory-enum-20261107'
if __name__ == '__main__':
    generate.main()
