# isla-runner

isla is part of the project `sail`. But it often has impatible version with `isla`.

The project is meant to gether the versions of `sail`/`sail-riscv`/`isla` all together.

And yes, this repo focus riscv only.

## Initialize

Initialize or update the dependent repositories on their configured branches. Sail is then pinned to the compatible `446fb477c508853595ccc937ed60765aa685ae31` revision:

```
./init.sh
```

Use SSH clone URLs when your GitHub credentials require them:

```
./init.sh --ssh
```

The script refuses to modify a repository with local changes. It initializes source repositories only; it does not install dependencies, build Sail/Isla, generate IR, or apply `sail-riscv.patch`.

## Run

Without Docker, initialize the repositories and compile `sail`/`sail-riscv`/`isla`. You can use `isla/isla-sail/isla-sail` to generate IR.

```
./init.sh
make -j`nproc` repos
```
use Docker:
```
NOT USEABLE YET
```

## Time
一个ir大约需要花8-10分钟来产生
