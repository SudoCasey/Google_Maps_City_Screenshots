import argparse
import re
import time
from pathlib import Path
from typing import Iterable
from urllib.parse import quote_plus

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Search Google Maps for each US city in a text file and save a 500x500 "
            "screenshot for each result."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a text file with one city per line, for example: Austin, TX",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Folder where screenshots will be saved",
    )
    parser.add_argument(
        "--wait-seconds",
        type=float,
        default=3.0,
        help="Extra time to wait after each search loads before taking the screenshot",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser without opening a visible window",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Keep the browser open after processing for debugging",
    )
    return parser.parse_args()


def read_cities(path: Path) -> list[str]:
    cities = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        city = raw_line.strip()
        if city and not city.startswith("#"):
            cities.append(city)
    return cities


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value, flags=re.ASCII)
    cleaned = re.sub(r"[-\s]+", "_", cleaned.strip())
    return cleaned or "city"


def dismiss_google_dialogs(page) -> None:
    labels = [
        "Reject all",
        "No thanks",
        "Not now",
        "Accept all",
    ]
    for label in labels:
        button = page.get_by_role("button", name=label)
        try:
            button.first.wait_for(state="visible", timeout=1500)
            button.first.click()
            page.wait_for_timeout(1000)
            return
        except PlaywrightTimeoutError:
            continue


def save_city_screenshots(
    cities: Iterable[str], output_dir: Path, wait_seconds: float, headless: bool, debug: bool
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    if debug:
        playwright = sync_playwright()
        p = playwright.__enter__()
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": 1000, "height": 1000},
            device_scale_factor=1,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        for index, city in enumerate(cities, start=1):
            search = quote_plus(f"{city}, USA")
            url = f"https://www.google.com/maps/search/{search}"
            filename = output_dir / f"{index:03d}_{slugify(city)}.png"

            print(f"[{index}] Loading {city} -> {filename.name}")
            try:
                page.goto(url, wait_until="load", timeout=60000)
                # dismiss_google_dialogs(page)

                # Try to collapse the side panel
                try:
                    collapse_button = page.locator("button[aria-label='Collapse side panel']")
                    collapse_button.wait_for(state="visible", timeout=2000)
                    collapse_button.click()
                    page.wait_for_timeout(500)
                except:
                    pass

                # Hide the side panel div with width: 480px
                page.evaluate("const div = document.querySelector('div[style*=\"width: 480px\"]'); if (div) div.style.display = 'none';")

                # Zoom out slightly to show more of the city area
                page.keyboard.press("-")
                page.wait_for_timeout(500)

                time.sleep(max(wait_seconds, 0))

                # Hide UI elements for clean screenshot
                page.add_style_tag(content="""
                    .searchbox, .widget-zoom, .app-viewcard-strip, 
                    .widget-directions, .widget-places, .widget-reviews,
                    .gm-style-cc, .gm-bundled-control, .gm-svpc,
                    .gm-fullscreen-control, .gm-control-active,
                    .widget-pane, .widget-layers, .widget-street-view,
                    .widget-compass, .widget-scale, .widget-pegman,
                    .widget-zoom-in, .widget-zoom-out, .widget-home,
                    .widget-mylocation, .widget-directions-searchbox,
                    .widget-places-searchbox, .widget-reviews-header,
                    .app-header, .app-footer, .gm-style-mtc,
                    .gm-style .gm-style-iw, .gm-style .gm-style-iw-t,
                    .gm-style .gm-style-iw-b, .gm-style .gm-style-iw-l,
                    .gm-style .gm-style-iw-r, .pane, .sidebar,
                    .left-panel, .info-panel, .place-card, .details-panel,
                    .widget-pane-content, .pane-content, .place-details,
                    .place-info, .gm2-body-1, .gm2-body-2, .gm2-body-3,
                    .gm2-body-4, .gm2-body-5, .gm2-body-6, .gm2-body-7,
                    .gm2-body-8, .gm2-body-9, .gm2-body-10,
                    [aria-roledescription], #gb, button, [role="search"], [aria-label="This area"] {
                        display: none !important;
                    }
                    .widget-scene {
                        position: absolute !important;
                        top: 0 !important;
                        left: 0 !important;
                        width: 100% !important;
                        height: 100% !important;
                    }
                """)

                # Try to close the side panel if open
                try:
                    close_button = page.locator("[aria-label='Close'], .widget-pane-close, .close-button").first
                    close_button.wait_for(state="visible", timeout=2000)
                    close_button.click()
                    page.wait_for_timeout(500)
                except:
                    pass

                time.sleep(1)  # Wait for CSS to apply
                page.screenshot(path=str(filename), clip={"x": 250, "y": 250, "width": 500, "height": 500})
                print(f"    Saved {filename.name}")
            except Exception as e:
                print(f"    Error processing {city}: {e}")
                continue

        print("Browser left open for debugging. Press Enter to close...")
        input()
        browser.close()
        playwright.__exit__(None, None, None)
    else:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=headless)
            page = browser.new_page(
                viewport={"width": 1000, "height": 1000},
                device_scale_factor=1,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            for index, city in enumerate(cities, start=1):
                search = quote_plus(f"{city}, USA")
                url = f"https://www.google.com/maps/search/{search}"
                filename = output_dir / f"{index:03d}_{slugify(city)}.png"

                print(f"[{index}] Loading {city} -> {filename.name}")
                try:
                    page.goto(url, wait_until="load", timeout=60000)
                    # dismiss_google_dialogs(page)

                    # Try to collapse the side panel
                    try:
                        collapse_button = page.locator("button[aria-label='Collapse side panel']")
                        collapse_button.wait_for(state="visible", timeout=2000)
                        collapse_button.click()
                        page.wait_for_timeout(500)
                    except:
                        pass

                    # Hide the side panel div with width: 480px
                    page.evaluate("const div = document.querySelector('div[style*=\"width: 480px\"]'); if (div) div.style.display = 'none';")

                    # Zoom out slightly to show more of the city area
                    page.keyboard.press("-")
                    page.wait_for_timeout(500)

                    time.sleep(max(wait_seconds, 0))

                    # Hide UI elements for clean screenshot
                    page.add_style_tag(content="""
                        .searchbox, .widget-zoom, .app-viewcard-strip, 
                        .widget-directions, .widget-places, .widget-reviews,
                        .gm-style-cc, .gm-bundled-control, .gm-svpc,
                        .gm-fullscreen-control, .gm-control-active,
                        .widget-pane, .widget-layers, .widget-street-view,
                        .widget-compass, .widget-scale, .widget-pegman,
                        .widget-zoom-in, .widget-zoom-out, .widget-home,
                        .widget-mylocation, .widget-directions-searchbox,
                        .widget-places-searchbox, .widget-reviews-header,
                        .app-header, .app-footer, .gm-style-mtc,
                        .gm-style .gm-style-iw, .gm-style .gm-style-iw-t,
                        .gm-style .gm-style-iw-b, .gm-style .gm-style-iw-l,
                        .gm-style .gm-style-iw-r, .pane, .sidebar,
                        .left-panel, .info-panel, .place-card, .details-panel,
                        .widget-pane-content, .pane-content, .place-details,
                        .place-info, .gm2-body-1, .gm2-body-2, .gm2-body-3,
                        .gm2-body-4, .gm2-body-5, .gm2-body-6, .gm2-body-7,
                        .gm2-body-8, .gm2-body-9, .gm2-body-10,
                        [aria-roledescription], #gb, button, [role="search"], [aria-label="This area"] {
                            display: none !important;
                        }
                        .widget-scene {
                            position: absolute !important;
                            top: 0 !important;
                            left: 0 !important;
                            width: 100% !important;
                            height: 100% !important;
                        }
                    """)

                    # Try to close the side panel if open
                    try:
                        close_button = page.locator("[aria-label='Close'], .widget-pane-close, .close-button").first
                        close_button.wait_for(state="visible", timeout=2000)
                        close_button.click()
                        page.wait_for_timeout(500)
                    except:
                        pass

                    time.sleep(1)  # Wait for CSS to apply
                    page.screenshot(path=str(filename), clip={"x": 250, "y": 250, "width": 500, "height": 500})
                    print(f"    Saved {filename.name}")
                except Exception as e:
                    print(f"    Error processing {city}: {e}")
                    continue

            browser.close()


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    cities = read_cities(input_path)
    if not cities:
        raise ValueError("No cities found in the input file.")

    save_city_screenshots(
        cities=cities,
        output_dir=output_dir,
        wait_seconds=args.wait_seconds,
        headless=args.headless,
        debug=args.debug,
    )
    print(f"Saved {len(cities)} screenshot(s) to {output_dir}")


if __name__ == "__main__":
    main()
