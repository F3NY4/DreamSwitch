#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="$ROOT/emulator"
export VCPKG_DISABLE_METRICS=1
export CMAKE_BUILD_PARALLEL_LEVEL=2
if [[ ! -e "$UPSTREAM/.git" ]]; then
  git clone --recursive https://github.com/citron-neo/emulator.git "$UPSTREAM"
fi
python3 -m unittest discover -s "$ROOT/tests" -v
python3 "$ROOT/apply_dreamswitch.py" "$UPSTREAM"
(
  cd "$UPSTREAM/src/android"
  chmod +x gradlew
  ./gradlew assembleMainlineRelease --no-daemon --stacktrace --max-workers=2
)
python3 "$ROOT/scripts/check_apk.py" "$UPSTREAM"/src/android/app/build/outputs/apk/mainline/release/*.apk
