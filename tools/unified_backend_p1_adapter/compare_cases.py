#!/usr/bin/env python3
import argparse
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('generated')
parser.add_argument('oracle')
args = parser.parse_args()
generated = [line.split() for line in subprocess.check_output([args.generated], text=True).splitlines()]
oracle = [line.split() for line in subprocess.check_output([args.oracle], text=True).splitlines()]
assert len(generated) == len(oracle), (len(generated), len(oracle))
for got, expected in zip(generated, oracle):
    assert got[:2] == expected[:2], (got, expected)
    print(' '.join(expected))
print(f'{len(oracle)} independent-process native numeric comparisons: PASS')
