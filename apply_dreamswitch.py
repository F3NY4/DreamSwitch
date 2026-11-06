#!/usr/bin/env python3
"""DreamSwitch retrofit patch, targeted at citron-neo/emulator Android sources.

Applies ONLY verified, non-destructive text replacements. Refuses mismatched upstream
sources rather than silently inserting code in unknown positions.
"""
from pathlib import Path
import argparse

JAVA = Path('src/android/app/src/main/java/org/citron/citron_emu')
RES = Path('src/android/app/src/main/res')

KEYBOARD_OLD = """    private fun startKeyboardDismissPolling(
        overlayView: View,
        previousVisibility: Int,
        previousAlpha: Float
    ) {
        val handler = Handler(Looper.myLooper()!!)
        val delayMs = 500L

        handler.postDelayed(object : Runnable {
            override fun run() {
                val insets = ViewCompat.getRootWindowInsets(overlayView)
                val isKeyboardVisible = insets?.isVisible(WindowInsets.Type.ime()) == true

                if (isKeyboardVisible) {
                    handler.postDelayed(this, delayMs)
                    return
                }

                // Keyboard was dismissed without a key event. Treat it as cancellation.
                overlayView.visibility = previousVisibility
                overlayView.alpha = previousAlpha
                NativeLibrary.submitInlineKeyboardInput(KeyEvent.KEYCODE_BACK)
                clearInlineConfig()
            }
        }, delayMs)
    }"""
KEYBOARD_NEW = """    private fun startKeyboardDismissPolling(
        overlayView: View,
        previousVisibility: Int,
        previousAlpha: Float,
        session: Long
    ) {
        // Some IMEs (notably when the emulator is busy) take several seconds to appear.
        // Do not mistake an IME that has not opened yet for one the user dismissed.
        val handler = Handler(Looper.getMainLooper())
        val delayMs = 500L
        val initialGraceMs = 8_000L
        val startedAt = SystemClock.uptimeMillis()
        var hasBeenVisible = false
        var hiddenSamples = 0

        handler.postDelayed(object : Runnable {
            override fun run() {
                // An old polling task must never close a newly opened keyboard.
                if (inlineKeyboardSession.get() != session || inlineConfig == null ||
                    !overlayView.isAttachedToWindow
                ) {
                    return
                }
                val insets = ViewCompat.getRootWindowInsets(overlayView)
                val isKeyboardVisible =
                    insets?.isVisible(WindowInsetsCompat.Type.ime()) == true

                if (isKeyboardVisible) {
                    hasBeenVisible = true
                    hiddenSamples = 0
                    handler.postDelayed(this, delayMs)
                    return
                }
                if (insets == null ||
                    (!hasBeenVisible && SystemClock.uptimeMillis() - startedAt < initialGraceMs)
                ) {
                    handler.postDelayed(this, delayMs)
                    return
                }
                // A transition frame can report IME hidden before it has actually closed.
                if (++hiddenSamples < 2) {
                    handler.postDelayed(this, delayMs)
                    return
                }
                overlayView.visibility = previousVisibility
                overlayView.alpha = previousAlpha
                clearInlineConfig()
                NativeLibrary.submitInlineKeyboardInput(KeyEvent.KEYCODE_BACK)
            }
        }, delayMs)
    }"""


def require_replace(s: str, old: str, new: str, p: Path) -> str:
    if new in s:
        return s  # idempotent
    count = s.count(old)
    if count != 1:
        raise RuntimeError(f'{p}: expected exactly one anchor, found {count}. No changes written.')
    return s.replace(old, new, 1)


def run(repo: Path):
    if not (repo / 'src/android/gradlew').exists():
        raise RuntimeError('Pass the root of a full citron-neo/emulator source checkout.')
    original = {}
    updated = {}
    def read(path):
        data=(repo/path).read_text(encoding='utf-8')
        original[path]=data
        return data
    kpath = JAVA / 'applets/keyboard/SoftwareKeyboard.kt'
    theme = JAVA / 'utils/ThemeHelper.kt'
    read(theme)
    if 'Theme.MaterialYou' not in original[theme]:
        raise RuntimeError('Upstream Material You theme missing; source version is unsupported.')
    s = read(kpath)
    s = require_replace(s, 'import android.os.Looper\n',
                       'import android.os.Looper\nimport android.os.SystemClock\n', kpath)
    s = require_replace(s, 'import android.view.WindowInsets\n',
                       'import androidx.core.view.WindowInsetsCompat\nimport java.util.concurrent.atomic.AtomicLong\n', kpath)
    s = require_replace(s, 'private var inlineConfig: KeyboardConfig? = null',
                       'private var inlineConfig: KeyboardConfig? = null\n\n    private val inlineKeyboardSession = AtomicLong(0L)', kpath)
    s = require_replace(s, '        inlineConfig = config\n',
                       '        inlineConfig = config\n        val session = inlineKeyboardSession.incrementAndGet()\n', kpath)
    s = require_replace(s, 'startKeyboardDismissPolling(overlayView, previousVisibility, previousAlpha)',
                       'startKeyboardDismissPolling(overlayView, previousVisibility, previousAlpha, session)', kpath)
    s = require_replace(s, KEYBOARD_OLD, KEYBOARD_NEW, kpath)
    s = require_replace(s, '    fun clearInlineConfig() {\n        inlineConfig = null\n    }',
                       '    fun clearInlineConfig() {\n        inlineConfig = null\n        inlineKeyboardSession.incrementAndGet()\n    }', kpath)
    updated[kpath]=s

    # Isolated DreamSwitch installation: distinct Android application ID and app label.
    # Kotlin / native namespaces remain upstream; only the on-device package name changes.
    gradle = Path('src/android/app/build.gradle.kts')
    gs = read(gradle)
    gs = require_replace(gs,
        'applicationId = "org.citron.citron_emu"',
        'applicationId = "org.dreamswitch.emulator"', gradle)
    gs = require_replace(gs,
        'resValue("string", "app_name_suffixed", "citron-neo: The switch fell off")',
        'resValue("string", "app_name_suffixed", "DreamSwitch")', gradle)
    gs = require_replace(gs,
        'resValue("string", "app_name_suffixed", "citron-neo: The switch fell off Debug")',
        'resValue("string", "app_name_suffixed", "DreamSwitch Debug")', gradle)
    updated[gradle] = gs

    strings = RES / 'values/strings.xml'
    ss = read(strings)
    ss = require_replace(ss,
        '<string name="app_name" translatable="false">citron-neo: The switch fell off</string>',
        '<string name="app_name" translatable="false">DreamSwitch</string>', strings)
    updated[strings] = ss

    # Only main-menu data cards: transparent card fill & outline, NO GPU blur / shader.
    for rel in ['layout/card_installable.xml', 'layout/card_installable_icon.xml', 'layout-w1000dp/card_installable_icon.xml']:
        p=RES/rel
        content=read(p)
        content=require_replace(content,
             '    android:layout_marginVertical="6dp">' if rel == 'layout/card_installable_icon.xml' else '    android:layout_marginVertical="12dp">',
             ('    android:layout_marginVertical="6dp"' if rel == 'layout/card_installable_icon.xml' else '    android:layout_marginVertical="12dp"') + """
    app:cardCornerRadius="28dp"
    app:cardElevation="0dp"
    app:cardBackgroundColor="@color/dream_glass_tint"
    app:strokeWidth="1dp"
    app:strokeColor="@color/dream_glass_stroke">""", p)
        updated[p]=content

    # The existing dialog's progress indicator becomes a low-overhead wave view.
    p=RES/'layout/dialog_progress_bar.xml'
    content=read(p)
    if '<org.citron.citron_emu.ui.widgets.DreamWaveProgressBar' not in content:
        content=require_replace(content,
            '<com.google.android.material.progressindicator.LinearProgressIndicator',
            '<org.citron.citron_emu.ui.widgets.DreamWaveProgressBar', p)
        content=require_replace(content,
            '        android:layout_height="wrap_content"\n        android:padding="24dp"\n        app:trackCornerRadius="4dp" />',
            '        android:layout_height="68dp"\n        android:padding="24dp" />', p)
    updated[p]=content

    assets = Path(__file__).resolve().parent/'overlay'
    for rel in [
       'src/android/app/src/main/res/values/dream_glass.xml',
       'src/android/app/src/main/res/values-night/dream_glass.xml',
       'src/android/app/src/main/java/org/citron/citron_emu/ui/widgets/DreamWaveProgressBar.kt',
    ]:
        path=Path(rel)
        data=(assets/rel).read_text(encoding='utf-8')
        if (repo/path).exists() and (repo/path).read_text(encoding='utf-8') != data:
            raise RuntimeError(f'{path} already exists with different content; stopping.')
        updated[path]=data
    # All edits validated before the first write.
    for path,data in updated.items():
        target=repo/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data,encoding='utf-8')
    print('DreamSwitch patch applied to',repo)
    print('Changed/new files:',len(updated))
    print('Notice: APK not built, game not tested, Windows changes not included.')


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('citron_source',type=Path)
    args=ap.parse_args()
    run(args.citron_source.expanduser().resolve())
