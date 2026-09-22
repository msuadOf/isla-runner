REPOSITORY = ghcr.io/msuadof
IMAGE = $(REPOSITORY)/isla

all: image

image:
	DOCKER_BUILDKIT=1 \
	docker build --no-cache --tag $(IMAGE):latest .

#===========
GITHUB_URL_SSH=git@github.com:
GITHUB_URL_HTTP=https://github.com/
GITHUB_URL=$(GITHUB_URL_HTTP)

export PATH:=$(abspath isla/isla-sail):$(PATH)
#export PATH=/home/baiyifan/workplace-local/isla-runner/isla/isla-sail:$PATH
$(info export PATH=$(PATH))
submodules:
	./init.sh --submodules-only

download-repo-sail-riscv: submodules
repo-sail-riscv:download-repo-sail-riscv repo-isla
	(cd sail-riscv && cmake -B build -S . -DCMAKE_BUILD_TYPE=Release && time cmake --build build --target generated_isla_rv32d generated_isla_rv64d)
	@echo " - rv32d.ir: You will see file in $(abspath sail-riscv/build/model/rv32d.ir)"

REPO_DEP+=repo-sail-riscv

sail/README.md repo-sail:
	-git clone $(GITHUB_URL)rems-project/sail.git
	cd sail && git checkout 446fb477c508853595ccc937ed60765aa685ae31
	cd sail && opam install . --deps-only -y && $(MAKE) install
REPO_DEP+=repo-sail

download-repo-isla: submodules
repo-isla: download-repo-isla repo-sail
	cd isla/isla-sail && $(MAKE)
REPO_DEP+=repo-isla

repos: $(REPO_DEP)

distclean: clean
	@echo "Source checkouts are preserved; deinitialize submodules explicitly if required."
clean:
	-$(MAKE) -C sail clean
	-$(MAKE) -C isla/isla-sail clean

.PHONY: all image submodules download-repo-sail-riscv download-repo-isla repo-sail-riscv repo-sail repo-isla repos distclean clean
