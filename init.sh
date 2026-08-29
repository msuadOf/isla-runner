#!/usr/bin/env bash

# Initialize or update the repositories used by this workspace.
#
# Existing repositories must be clean: this script intentionally refuses to
# overwrite local experiments or uncommitted work.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_SSH=0

usage() {
    cat <<'EOF'
Usage: ./init.sh [--ssh]

Clone missing workspace repositories and check out their configured branches.
For existing repositories, fetch origin, switch to the configured branch, and
fast-forward it. Sail is then pinned to the workspace's compatible commit.
The script stops before changing any repository with local changes or a
different origin repository.

Options:
  --ssh   Use git@github.com:<owner>/<repository>.git clone URLs.
  -h, --help
          Show this help message.
EOF
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

github_url() {
    local repository="$1"

    if [[ "$USE_SSH" -eq 1 ]]; then
        printf 'git@github.com:%s.git\n' "$repository"
    else
        printf 'https://github.com/%s.git\n' "$repository"
    fi
}

github_repository() {
    local remote_url="$1"

    remote_url="${remote_url%.git}"
    remote_url="${remote_url#https://github.com/}"
    remote_url="${remote_url#ssh://git@github.com/}"
    remote_url="${remote_url#git@github.com:}"
    printf '%s\n' "$remote_url"
}

ensure_clean_worktree() {
    local repository_dir="$1"
    local status_output
    local dirty_submodules

    status_output="$(git -C "$repository_dir" status --porcelain --untracked-files=normal)"
    [[ -z "$status_output" ]] || die "$repository_dir has local changes; commit, stash, or remove them before rerunning init.sh"

    dirty_submodules="$(git -C "$repository_dir" submodule foreach --quiet --recursive 'if test -n "$(git status --porcelain --untracked-files=normal)"; then printf "%s\\n" "$displaypath"; fi')"
    [[ -z "$dirty_submodules" ]] || die "$repository_dir has local changes in submodule(s): $dirty_submodules"
}

pin_revision() {
    local repository_dir="$1"
    local branch="$2"
    local revision="$3"

    git -C "$repository_dir" rev-parse --verify --quiet "${revision}^{commit}" >/dev/null || die "$repository_dir does not contain pinned revision $revision"
    git -C "$repository_dir" merge-base --is-ancestor "$revision" "origin/$branch" || die "$revision is not reachable from origin/$branch in $repository_dir"
    git -C "$repository_dir" switch --detach "$revision"
}

switch_to_branch() {
    local repository_dir="$1"
    local branch="$2"
    local pinned_revision="$3"

    git -C "$repository_dir" fetch --prune origin

    if git -C "$repository_dir" show-ref --verify --quiet "refs/heads/$branch"; then
        git -C "$repository_dir" switch "$branch"
    else
        git -C "$repository_dir" switch --track -c "$branch" "origin/$branch"
    fi

    git -C "$repository_dir" pull --ff-only origin "$branch"

    if [[ -n "$pinned_revision" ]]; then
        pin_revision "$repository_dir" "$branch" "$pinned_revision"
    fi

    git -C "$repository_dir" submodule sync --recursive
    git -C "$repository_dir" submodule update --init --recursive
}

initialize_repository() {
    local relative_dir="$1"
    local expected_repository="$2"
    local branch="$3"
    local pinned_revision="$4"
    local repository_dir="$ROOT_DIR/$relative_dir"
    local origin_url

    printf '\n==> %s (%s)\n' "$relative_dir" "$branch"

    if [[ ! -e "$repository_dir" ]]; then
        mkdir -p "$(dirname "$repository_dir")"
        git clone --branch "$branch" --recurse-submodules "$(github_url "$expected_repository")" "$repository_dir"

        if [[ -n "$pinned_revision" ]]; then
            pin_revision "$repository_dir" "$branch" "$pinned_revision"
            git -C "$repository_dir" submodule sync --recursive
            git -C "$repository_dir" submodule update --init --recursive
        fi

        return
    fi

    [[ -d "$repository_dir/.git" || -f "$repository_dir/.git" ]] || die "$relative_dir exists but is not a Git worktree"
    origin_url="$(git -C "$repository_dir" remote get-url origin)"
    [[ "$(github_repository "$origin_url")" == "$expected_repository" ]] || die "$relative_dir origin is $origin_url, expected GitHub repository $expected_repository"

    ensure_clean_worktree "$repository_dir"
    switch_to_branch "$repository_dir" "$branch" "$pinned_revision"
}

while [[ "$#" -gt 0 ]]; do
    case "$1" in
        --ssh)
            USE_SSH=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "unknown option: $1"
            ;;
    esac
    shift
done

repositories=(
    "isla|ariscv/isla|dev-isarch-runall-ext|"
    "sail|rems-project/sail|sail2|446fb477c508853595ccc937ed60765aa685ae31"
    "sail-riscv|msuadOf/sail-riscv|isla/symbol-excution_6_14|"
    "assembly-gen|msuadOf/assembly-gen|dev|"
    "difftest|msuadOf/difftest|dev|"
    "difftest-xiangshan/xiangshan|OpenXiangShan/XiangShan|kunminghu-v3|"
)

for specification in "${repositories[@]}"; do
    IFS='|' read -r relative_dir repository branch pinned_revision <<< "$specification"
    initialize_repository "$relative_dir" "$repository" "$branch" "$pinned_revision"
done

printf '\nAll repositories are initialized on their configured branches.\n'
