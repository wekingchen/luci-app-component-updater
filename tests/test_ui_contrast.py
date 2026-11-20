"""Prevent LuCI theme collisions and unreadable buttons from shipping again."""
import re
import unittest
from pathlib import Path

CSS = (Path(__file__).resolve().parents[1] /
       "luci-app-component-updater/htdocs/luci-static/resources/component-updater/design.css").read_text()


def luminance(hex_rgb):
    values = [int(hex_rgb[i:i+2], 16) / 255 for i in (1, 3, 5)]
    values = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in values]
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def contrast(foreground, background):
    a, b = sorted([luminance(foreground), luminance(background)], reverse=True)
    return (a + .05) / (b + .05)


class VisualContrastContract(unittest.TestCase):
    def test_all_normal_text_and_disabled_buttons_have_aa_contrast(self):
        pairs = {
            "正文 / 卡片": ("#152c38", "#ffffff"),
            "次要说明 / 卡片": ("#4d626e", "#ffffff"),
            "未启用按钮": ("#526671", "#e5ebee"),
            "主要操作": ("#ffffff", "#086b64"),
            "警告状态": ("#815000", "#fff5da"),
            "正常状态": ("#0e644c", "#e6f6ed"),
            "底部链接": ("#076b62", "#f4f7f8"),
            "分组标签": ("#48616c", "#edf3f5"),
        }
        for name, (fg, bg) in pairs.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast(fg, bg), 4.5,
                    f"{name}: {contrast(fg, bg):.2f}:1 < WCAG AA 4.5:1")
                self.assertIn(fg, CSS, f"{name}: expected foreground token missing")
                self.assertIn(bg, CSS, f"{name}: expected background token missing")

    def test_luci_heading_background_is_explicitly_reset(self):
        # Production GL.iNet theme may set H2/H3 to white background and text.
        block = re.search(r"\.cu-app\s+:is\(h2,\s*h3\).*?\{([^}]+)\}", CSS, re.S)
        self.assertIsNotNone(block)
        for required in ("background: transparent !important",
                         "background-image: none !important",
                         "color: var(--cu-ink) !important",
                         "padding: 0 !important",
                         "box-shadow: none !important"):
            self.assertIn(required, block.group(1))

    def test_theme_accent_bars_are_scoped_out_without_hiding_functional_pseudo_elements(self):
        # GL.iNet adds decorative bars to headers, panels and LuCI form maps.
        # Only the updater's wrappers should be reset; do not touch global nav.
        for token in (
            ".cu-page-head::after", ".cu-settings-heading::before",
            ".cu-hero::before", ".cu-panel::after",
            ".cu-settings-form .cbi-map::before",
            ".cu-settings-form .cbi-section::after",
        ):
            self.assertIn(token, CSS)
        self.assertIn("content: none !important", CSS)
        self.assertIn(".cu-app .cu-status::before", CSS,
                      "The intentional status dot must remain visible")
        self.assertIn(".cu-app .cu-detail > summary::after", CSS,
                      "The expand/collapse indicator must remain visible")
        self.assertNotIn("body > header::after", CSS,
                         "Never alter the router's global navigation")

    def test_prominent_settings_shortcut_and_select_appearance(self):
        for token in (
            ".cu-page-title-row", ".cu-page-settings",
            ".cu-settings-form .cbi-value-description",
            ".cu-settings-form .cbi-page-actions",
            ".cu-settings-form [hidden]",
            "font-size: 16px !important",
            ".cu-setup-hint", "min-height: 44px",
        ):
            self.assertIn(token, CSS)

    def test_ready_button_does_not_animate_from_disabled_gray_to_teal(self):
        # Without this guard, white text changes immediately while background
        # transitions for 150ms, producing a low-contrast white-on-gray flash.
        self.assertIn(".cu-app button.cu-btn {", CSS)
        button_block = CSS.split(".cu-app button.cu-btn {", 1)[1].split("}", 1)[0]
        self.assertIn("transition: none !important", button_block)
        self.assertNotIn("transition: background-color", button_block)

    def test_disabled_button_preserves_full_opacity_and_readable_text(self):
        block = re.search(r"\.cu-app button\.cu-btn:disabled\s*\{([^}]+)\}", CSS, re.S)
        self.assertIsNotNone(block)
        for term in ("opacity: 1 !important", "color: #526671 !important",
                     "background: #e5ebee !important"):
            self.assertIn(term, block.group(1))

    def test_check_first_flow_and_mobile_widths_are_defined(self):
        for selector in (".cu-actions:not(.is-ready) .cu-btn-check",
                         ".cu-actions.is-ready .cu-btn-update",
                         "@media (max-width: 600px)", "@media (max-width: 360px)",
                         "white-space: nowrap", "color-scheme: light"):
            self.assertIn(selector, CSS)
        self.assertNotIn("opacity: .4", CSS)


if __name__ == "__main__":
    unittest.main()
