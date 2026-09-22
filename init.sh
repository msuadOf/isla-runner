#!/usr/bin/env bash

# Initialize or update the repositories used by this workspace.
#
# Existing branch-managed repositories must be clean. Existing submodules are
# never updated in place: matching checkouts are preserved, including local
# changes, and mismatched HEADs cause a fail-closed error.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USE_SSH=0
SUBMODULES_ONLY=0

usage() {
    cat <<'EOF'
Usage: ./init.sh [--ssh] [--submodules-only]

Initialize Isla and Sail-RISC-V at the commits recorded by the parent
repository. Existing checkouts are only validated and are never checked out,
reset, pulled, or cleaned. The remaining independent repositories are cloned
or fast-forwarded on their configured branches; Sail is then pinned to the
workspace's compatible commit.

Options:
  --ssh   Use git@github.com:<owner>/<repository>.git clone URLs.
  --submodules-only
          Only initialize/validate Isla and Sail-RISC-V; skip other repositories.
  -h, --help
          Show this help message.
EOF
}

gitlink_revision() {
    local relative_dir="$1"
    local entry
    local mode
    local revision
    local stage
    local indexed_path

    entry="$(git -C "$ROOT_DIR" ls-files --stage -- "$relative_dir")"
    [[ -n "$entry" ]] || die "$relative_dir has no gitlink in the parent repository index"
    [[ "$(printf '%s\n' "$entry" | wc -l)" -eq 1 ]] || die "$relative_dir has unresolved or duplicate index entries"
    read -r mode revision stage indexed_path <<< "$entry"
    [[ "$mode" == "160000" && "$stage" == "0" && "$indexed_path" == "$relative_dir" ]] || \
        die "$relative_dir is not a resolved submodule gitlink in the parent repository index"
    printf '%s\n' "$revision"
}

initialize_submodule() {
    local relative_dir="$1"
    local expected_repository="$2"
    local repository_dir="$ROOT_DIR/$relative_dir"
    local revision
    local origin_url
    local status_output

    revision="$(gitlink_revision "$relative_dir")"
    printf '\n==> %s (submodule %s)\n' "$relative_dir" "$revision"

    if [[ ! -e "$repository_dir" ]] || \
       { [[ -d "$repository_dir" ]] && [[ -z "$(find "$repository_dir" -mindepth 1 -print -quit)" ]]; }; then
        git -C "$ROOT_DIR" config "submodule.$relative_dir.url" "$(github_url "$expected_repository")"
        git -C "$ROOT_DIR" submodule update --init -- "$relative_dir"
    fi

    [[ -d "$repository_dir/.git" || -f "$repository_dir/.git" ]] || \
        die "$relative_dir exists but is not a Git worktree; refusing to replace it"
    origin_url="$(git -C "$repository_dir" remote get-url origin)"
    [[ "$(github_repository "$origin_url")" == "$expected_repository" ]] || \
        die "$relative_dir origin is $origin_url, expected GitHub repository $expected_repository"
    git -C "$repository_dir" rev-parse --verify --quiet "${revision}^{commit}" >/dev/null || \
        die "$relative_dir does not contain parent-recorded commit $revision"
    [[ "$(git -C "$repository_dir" rev-parse HEAD)" == "$revision" ]] || \
        die "$relative_dir HEAD differs from parent-recorded commit $revision; refusing to update it"

    status_output="$(git -C "$repository_dir" status --porcelain --untracked-files=normal)"
    if [[ -n "$status_output" ]]; then
        printf 'warning: %s has local changes; preserving them because HEAD matches the gitlink\n' "$relative_dir" >&2
    fi
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

    # shellcheck disable=SC2016 # Expanded by each git-submodule child shell.
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
        --submodules-only)
            SUBMODULES_ONLY=1
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

submodules=(
    "isla|ariscv/isla"
    "sail-riscv|msuadOf/sail-riscv"
)

for specification in "${submodules[@]}"; do
    IFS='|' read -r relative_dir repository <<< "$specification"
    initialize_submodule "$relative_dir" "$repository"
done

if [[ "$SUBMODULES_ONLY" -eq 1 ]]; then
    printf '\nSubmodules match the parent repository gitlinks.\n'
    exit 0
fi

repositories=(
    "sail|rems-project/sail|sail2|446fb477c508853595ccc937ed60765aa685ae31"
    "assembly-gen|msuadOf/assembly-gen|dev|"
    "difftest|msuadOf/difftest|dev|"
    "difftest-xiangshan/xiangshan|OpenXiangShan/XiangShan|kunminghu-v3|"
)

for specification in "${repositories[@]}"; do
    IFS='|' read -r relative_dir repository branch pinned_revision <<< "$specification"
    initialize_repository "$relative_dir" "$repository" "$branch" "$pinned_revision"
done

printf '\nSubmodules match their gitlinks; independent repositories are initialized on their configured branches.\n'
