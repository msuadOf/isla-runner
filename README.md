# isla-runner

isla is part of the project `sail`. But it often has impatible version with `isla`.

The project is meant to gether the versions of `sail`/`sail-riscv`/`isla` all together.

And yes, this repo focus riscv only.

## Initialize

Clone with the two version-linked repositories in one step:

```
git clone --recurse-submodules <isla-runner-url>
```

For an existing clone, initialize or validate the workspace:

```
./init.sh
```

Use SSH clone URLs when your GitHub credentials require them:

```
./init.sh --ssh
```

Isla and Sail-RISC-V are submodules. Their exact commits come from the parent repository's gitlinks, not from a moving branch. `init.sh` initializes a missing submodule, but an existing checkout is only validated: a matching dirty checkout is preserved, while a different HEAD stops with an error. Use `./init.sh --submodules-only` when the other independent repositories are not needed.

Sail, assembly-gen, difftest, and the XiangShan upstream checkout remain independently branch-managed. For those repositories, the script refuses to modify local changes. It does not install dependencies, build Sail/Isla, generate IR, or apply `sail-riscv.patch` automatically. The patch remains a historical/manual recipe.

Submodules normally initialize at detached HEAD. Create or switch to a development branch inside a submodule before making commits there. Do not run `git submodule update` over a dirty submodule unless you have first preserved its work.

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
