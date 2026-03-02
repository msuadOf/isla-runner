REPOSITORY = ghcr.io/msuadof
IMAGE = $(REPOSITORY)/isla

all: image

image:
	DOCKER_BUILDKIT=1 \
	docker build --no-cache --tag $(IMAGE):latest .

#===========
export PATH:=$(abspath isla/isla-sail):$(PATH)
$(info export PATH=$(PATH))
sail-riscv/README.md download-repo-sail-riscv:
	-git clone https://github.com/riscv/sail-riscv.git
repo-sail-riscv:download-repo-sail-riscv repo-isla
	-git apply --directory sail-riscv/model sail-riscv.patch
	(cd sail-riscv && cmake -B build -S . -DCMAKE_BUILD_TYPE=Release && time cmake --build build --target generated_isla_rv32d)

REPO_DEP+=repo-sail-riscv

sail/README.md repo-sail:
	-git clone https://github.com/rems-project/sail.git
	cd sail && git checkout 446fb477c508853595ccc937ed60765aa685ae31
	cd sail && opam install . --deps-only -y && $(MAKE) install
REPO_DEP+=repo-sail

isla/README.md download-repo-isla:
	-git clone https://github.com/rems-project/isla.git
repo-isla: download-repo-isla repo-sail
	cd isla/isla-sail && $(MAKE)
REPO_DEP+=repo-isla

repos: $(REPO_DEP)

distclean:
	-rm -rf sail isla sail-riscv
clean:
	-$(MAKE) -C sail clean
	-$(MAKE) -C isla/isla-sail clean

.PHONY: all image
