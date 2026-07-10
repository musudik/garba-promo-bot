"""
Generates per-city caption files from the templates in content/captions/templates/.

Run this whenever you add a new caption template or change the city list.
Usage:
    python scripts/generate_captions.py
"""
import os
import sys

sys.path.append(os.path.dirname(__file__))
from utils import TARGET_CITIES  # noqa: E402

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "captions", "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "content", "captions", "generated")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.isdir(TEMPLATE_DIR):
        print(f"No templates directory found at {TEMPLATE_DIR}")
        return

    templates = [f for f in os.listdir(TEMPLATE_DIR) if f.endswith(".txt")]
    if not templates:
        print("No .txt templates found to process.")
        return

    for template_name in templates:
        base_name = os.path.splitext(template_name)[0]
        with open(os.path.join(TEMPLATE_DIR, template_name), encoding="utf-8") as f:
            template_text = f.read()

        for city in TARGET_CITIES:
            out_name = f"{base_name}_{city.lower()}.txt"
            out_path = os.path.join(OUTPUT_DIR, out_name)
            # Note: {days_left} is left as a literal placeholder here and
            # resolved at POST TIME by post_scheduler.py, so the countdown
            # is always accurate on the day it's actually published.
            rendered = template_text.replace("{city}", city)
            with open(out_path, "w", encoding="utf-8") as out_f:
                out_f.write(rendered)
            print(f"Generated {out_path}")


if __name__ == "__main__":
    main()
