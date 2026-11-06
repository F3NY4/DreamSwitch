#!/usr/bin/env bash
set -euo pipefail
PACKAGE=org.dreamswitch.emulator
OUT="${1:-dreamswitch_diagnostics}"
mkdir -p "$OUT"
adb devices -l | tee "$OUT/devices.txt"
adb shell getprop ro.product.model | tee "$OUT/model.txt"
adb shell getprop ro.build.version.release | tee "$OUT/android.txt"
adb shell dumpsys SurfaceFlinger | grep -Ei 'vulkan|gles' | head -30 > "$OUT/graphics_summary.txt" || true
adb logcat -c
adb shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1
sleep 12
adb logcat -d -v time > "$OUT/launch.log"
if grep -Ei 'FATAL EXCEPTION|Fatal signal|SIGSEGV|VK_ERROR_DEVICE_LOST' "$OUT/launch.log"; then
  echo 'WARNING: potential crash; inspect launch.log' >&2
else
  echo 'No matching fatal marker; this does NOT prove game compatibility.'
fi
