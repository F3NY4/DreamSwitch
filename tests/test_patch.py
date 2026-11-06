import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import apply_dreamswitch as patch

class DreamSwitchPatchTests(unittest.TestCase):
    def test_overlay_xml(self):
        for path in (ROOT / "overlay").rglob("*.xml"):
            ET.parse(path)

    def test_patch_contains_keyboard_session_guard(self):
        text = (ROOT / "apply_dreamswitch.py").read_text(encoding="utf-8")
        self.assertIn("initialGraceMs = 8_000L", text)
        self.assertIn("inlineKeyboardSession.incrementAndGet()", text)

    def test_patch_refuses_missing_source(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "Pass the root"):
                patch.run(Path(tmp))

    def test_patch_applies_twice(self):
        with TemporaryDirectory() as tmp:
            repo = Path(tmp)
            gradlew = repo / "src/android/gradlew"
            gradlew.parent.mkdir(parents=True)
            gradlew.touch()

            def write(relative, content):
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                return path

            kb = write(patch.JAVA / "applets/keyboard/SoftwareKeyboard.kt",
                "import android.os.Looper\nimport android.view.WindowInsets\n"
                "private var inlineConfig: KeyboardConfig? = null\n"
                "        inlineConfig = config\n"
                "startKeyboardDismissPolling(overlayView, previousVisibility, previousAlpha)\n"
                + patch.KEYBOARD_OLD + "\n"
                "    fun clearInlineConfig() {\n        inlineConfig = null\n    }\n"
            )
            write(patch.JAVA / "utils/ThemeHelper.kt", "/* Theme.MaterialYou */")
            for directory, filename, margin in [
                ("layout", "card_installable.xml", "12dp"),
                ("layout", "card_installable_icon.xml", "6dp"),
                ("layout-w1000dp", "card_installable_icon.xml", "12dp"),
            ]:
                write(patch.RES / directory / filename,
                    '<root xmlns:android="http://schemas.android.com/apk/res/android" '
                    'xmlns:app="http://schemas.android.com/apk/res-auto" '
                    'android:layout_marginVertical="' + margin + '"/>'
                )
            write(patch.RES / "layout/dialog_progress_bar.xml",
                '<root xmlns:android="http://schemas.android.com/apk/res/android" '
                'xmlns:app="http://schemas.android.com/apk/res-auto">'
                '<com.google.android.material.progressindicator.LinearProgressIndicator '
                'android:layout_height="wrap_content" android:padding="24dp" '
                'app:trackCornerRadius="4dp" /></root>'
            )
            gradle = write("src/android/app/build.gradle.kts",
                'applicationId = "org.citron.citron_emu"\n'
                'resValue("string", "app_name_suffixed", "citron-neo: The switch fell off")\n'
                'resValue("string", "app_name_suffixed", "citron-neo: The switch fell off Debug")'
            )
            write(patch.RES / "values/strings.xml",
                '<resources><string name="app_name" translatable="false">'
                'citron-neo: The switch fell off</string></resources>'
            )
            patch.run(repo)
            first = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            patch.run(repo)
            second = {str(p.relative_to(repo)): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
            self.assertEqual(first, second)
            self.assertIn("WindowInsetsCompat.Type.ime()", kb.read_text())
            self.assertIn("org.dreamswitch.emulator", gradle.read_text())

if __name__ == "__main__":
    unittest.main()
