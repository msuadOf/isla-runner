#!/bin/bash
set -e
cd /tmp/legal2048
LD=/home/baiyifan/workplace-local/isla-runner/ara/work-all/elf/ara.ld
for s in *.S; do
  n=${s%.S}
  riscv64-unknown-elf-gcc -march=rv64gcv -mabi=lp64d -nostdlib -static -T "$LD" -o "$n.elf" "$s"
done
ls -1 *.elf
