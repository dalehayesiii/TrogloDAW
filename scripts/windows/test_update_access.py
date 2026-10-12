"""Native-test-only isolated credential probes; never prints a credential."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
import credentials  # noqa: E402

mode, owner, other = sys.argv[1:]
own_target = credentials.installation_target(owner)
other_target = credentials.installation_target(other)
if mode == "save":
    credentials.save("synthetic_never_used_release_token", own_target)
    credentials.save("synthetic_other_installation_token", other_target)
elif mode == "verify":
    try:
        assert credentials.read(own_target) is None, "Uninstall retained its saved release access"
        assert credentials.read(other_target) is not None, (
            "Uninstall removed another installation's access"
        )
    finally:
        credentials.remove(own_target)
        credentials.remove(other_target)
elif mode == "cleanup":
    credentials.remove(own_target)
    credentials.remove(other_target)
else:
    raise ValueError("Unknown native credential test mode")
print("Isolated native credential boundary passed.")
