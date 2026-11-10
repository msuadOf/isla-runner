#!/usr/bin/env python3
"""Copy the reviewed seven-file adapter set without overwriting other edits."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
sources = {
    'sail_softfloat_types.h': ('tools/unified_backend_p1_adapter/sail_softfloat_types.h', 'f99937abd35262cd3f450593836d06a2f6090a23de09e2cf6abf3a8033977530'),
    'sail_softfloat.h': ('tools/unified_backend_p1_adapter/sail_softfloat.h', '8d42a9fac337e920416e313c657974f82e4d9934002ceb62e519c0328664290f'),
    'sail_softfloat.cpp': ('tools/unified_backend_p1_adapter/sail_softfloat.cpp', 'acaab7023df8dd384e72e1fa2d0bef620c845a29dd95d4e5e8c5e145e5d896b1'),
    'sail_softfloat_wide.h': ('agents/float_support_review/tools/unified_backend_p2_wide/sail_softfloat_wide.h', '966116135755712e470f2374d0b9a38fd688fbf95eac77e8c076a69fa9ac358f'),
    'sail_softfloat_wide.cpp': ('agents/float_support_review/tools/unified_backend_p2_wide/sail_softfloat_wide.cpp', '3e934be4379d627158b4dd2b2cecb54563a51dbd9cda7a579b798a7d5be318e5'),
    'sail_softfloat_extra.h': ('agents/float_support_review/tools/unified_backend_p2_native_extra/sail_softfloat_extra.h', '5a0d4a0eb08aeaff5fee79ad4750ee2b6289e2173d1a7aa48c53eb7627405372'),
    'sail_softfloat_extra.cpp': ('agents/float_support_review/tools/unified_backend_p2_native_extra/sail_softfloat_extra.cpp', '11c18c5fbf904af9e6e581660e1cd0ba25164a6184931f8c6c1464d20bfd77be'),
}

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

if len(sys.argv) < 3:
    raise SystemExit('usage: copy_frozen.py MANIFEST DESTINATION [DESTINATION ...]')
manifest = Path(sys.argv[1]).resolve()
destinations = [Path(arg).resolve() for arg in sys.argv[2:]]
for name, (relative, expected) in sources.items():
    source = root / relative
    if digest(source) != expected:
        raise SystemExit(f'source hash changed: {relative}')
    for destination in destinations:
        if not destination.is_dir():
            raise SystemExit(f'destination missing: {destination}')
        target = destination / name
        if target.exists() and digest(target) != expected:
            raise SystemExit(f'conflicting target retained: {target}')
for name, (relative, expected) in sources.items():
    source = root / relative
    for destination in destinations:
        target = destination / name
        if not target.exists():
            shutil.copy2(source, target)
        assert digest(target) == expected

manifest.parent.mkdir(parents=True, exist_ok=True)
data = {'schema': 1,
        'files': {name: {'source': relative, 'sha256': expected}
                  for name, (relative, expected) in sources.items()},
        'destinations': [str(p.relative_to(root)) if p.is_relative_to(root) else str(p)
                         for p in destinations]}
manifest.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
print(f'copied or verified {len(sources)} files in {len(destinations)} destinations')
