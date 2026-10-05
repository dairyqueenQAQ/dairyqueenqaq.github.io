"""Build the static portfolio from a saved copy of the owner's old site.

The source snapshots are read from the system temporary directory. Original
files in Assets are never modified or copied into the published site.
"""

from __future__ import annotations

import html as html_std
import re
import tempfile
from pathlib import Path
from urllib.parse import unquote_plus, urlparse
from urllib.request import Request, urlopen

from lxml import html
from PIL import Image, ImageOps, UnidentifiedImageError


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOTS = Path(tempfile.gettempdir()) / "dq-portfolio-reference"
YOUTUBE_VIDEOS = {
    "trigramdeduction": "AYaf3UySAeo",
    "theedgeofabyss": "69mHDICAFfw",
    "tiletale": "ua7cJMYrTsc",
    "bouncespace": "_1f-Tdm-DdA",
}

PAGES = {
    "home": "HomePage",
    "aboutme": "AboutMe",
    "fox": "Fox",
    "trigramdeduction": "TrigramDeduction",
    "tiletale": "Tiletale",
    "bouncespace": "BounceSpace",
    "theedgeofabyss": "TheEdgeOfAbyss",
    "chinesebaguavfx": "ChineseBaguaVFX",
}
BACKGROUND_IMAGES = {
    "trigramdeduction": "TrigramBackground1.png",
    "tiletale": "TileTaleBackground.png",
    "bouncespace": "BSBackground.png",
    "theedgeofabyss": "AbyssBG.png",
    "chinesebaguavfx": "baguaTA.png",
}
TITLES = {
    "home": "DingQian Zhang — Game Design Portfolio",
    "aboutme": "AboutMe! — DingQian Zhang",
    "fox": "XinYueHu — DingQian Zhang",
    "trigramdeduction": "TrigramDeduction — DingQian Zhang",
    "tiletale": "TileTale — DingQian Zhang",
    "bouncespace": "BounceSpace — DingQian Zhang",
    "theedgeofabyss": "The Edge of Abyss — DingQian Zhang",
    "chinesebaguavfx": "Chinese Bagua VFX — DingQian Zhang",
}

ASSETS = [path for path in (ROOT / "Assets").rglob("*") if path.is_file()]
ASSET_BY_NAME = {}
for path in ASSETS:
    ASSET_BY_NAME.setdefault(path.name.casefold(), []).append(path)

OUTPUT_CACHE: dict[tuple[str, str], str] = {}
UNRESOLVED: list[str] = []


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def source_image(url: str, page: str) -> Path | None:
    filename = unquote_plus(urlparse(url).path.rsplit("/", 1)[-1])
    matches = ASSET_BY_NAME.get(filename.casefold(), [])
    if matches:
        preferred = ROOT / "Assets" / PAGES[page]
        return next((p for p in matches if preferred in p.parents), matches[0])
    missing = SNAPSHOTS / "missing" / filename
    if not missing.exists() and url.startswith("https://"):
        try:
            download(url + "?format=1500w", missing)
        except OSError:
            pass
    if missing.exists():
        return missing
    UNRESOLVED.append(f"{page}: {filename}")
    return None


def web_image(url: str, page: str) -> str:
    source = source_image(url, page)
    if source is None:
        return ""
    cache_key = (page, str(source))
    if cache_key in OUTPUT_CACHE:
        return OUTPUT_CACHE[cache_key]

    output_dir = ROOT / "media" / page
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{len([key for key in OUTPUT_CACHE if key[0] == page]) + 1:03d}.webp"
    if not output.exists() or output.stat().st_mtime < source.stat().st_mtime:
        try:
            with Image.open(source) as original:
                image = ImageOps.exif_transpose(original)
                image.thumbnail((2200, 2200), Image.Resampling.LANCZOS)
                if image.mode not in {"RGB", "RGBA"}:
                    has_alpha = "A" in image.getbands() or "transparency" in image.info
                    image = image.convert("RGBA" if has_alpha else "RGB")
                image.save(output, "WEBP", quality=86, method=4)
        except (UnidentifiedImageError, OSError, ValueError) as error:
            UNRESOLVED.append(f"{page}: {source} ({error})")
            return ""
    relative = "/" + output.relative_to(ROOT).as_posix()
    OUTPUT_CACHE[cache_key] = relative
    return relative


def clean_text(element) -> str:
    # Squarespace adds presentation attributes and editor-only markers. Keep
    # the author's actual headings, paragraphs, emphasis, lists and links.
    clone = html.fromstring(html.tostring(element, encoding="unicode"))
    for node in clone.iter():
        if node.get("data-rte-preserve-empty") and not node.text_content().strip():
            node.text = "\u00a0"
        for attr in list(node.attrib):
            if attr not in {"href", "class", "style", "target", "rel"}:
                del node.attrib[attr]
        if node.tag == "a":
            href = node.get("href", "")
            if href.startswith("https://www.zhangdingqian.com"):
                href = urlparse(href).path
            if href == "/home":
                href = "/"
            if href.startswith("/") and href.strip("/") in PAGES:
                href = "/" if href.strip("/") == "home" else href.rstrip("/") + "/"
            node.set("href", href)
            if href.startswith("http"):
                node.set("rel", "noopener noreferrer")
    return "".join(html.tostring(child, encoding="unicode") for child in clone)


def block_markup(block, page: str, video_poster: str) -> str:
    block_class = block.get("class", "")
    content = block.xpath("./div[contains(@class, 'sqs-block')]")
    if not content:
        return ""
    kind = content[0].get("class", "")
    body = ""
    if "html-block" in kind:
        text_nodes = block.xpath(".//div[contains(@class, 'sqs-html-content')]")
        if text_nodes:
            body = f'<div class="sqs-block"><div class="sqs-html-content">{clean_text(text_nodes[0])}</div></div>'
    elif "image-block" in kind:
        images = block.xpath(".//img")
        if images:
            image = images[0]
            src = web_image(image.get("data-src") or image.get("src") or "", page)
            if src:
                anchors = block.xpath(".//a[@href]")
                href = anchors[0].get("href") if anchors else ""
                if href == "/home":
                    href = "/"
                if href and href.strip("/") in PAGES:
                    href = "/" if href.strip("/") == "home" else href.rstrip("/") + "/"
                alt = image.get("alt") or ""
                if href and not alt:
                    alt = f"View {TITLES[href.strip('/')].split(' — ')[0]}" if href.strip("/") in TITLES else "View project"
                with Image.open(ROOT / src.lstrip("/")) as optimized:
                    width, height = optimized.size
                original_css = "\n".join(block.xpath('.//style/text()'))
                fit = "cover" if "--image-component-object-fit: cover" in original_css else "contain"
                wrapper = block.xpath('.//*[contains(@class, "image-block-outer-wrapper")]')
                alignment = "center"
                if wrapper:
                    for candidate in ("left", "right", "center"):
                        if f"image-position-{candidate}" in wrapper[0].get("class", ""):
                            alignment = candidate
                radius = re.search(r"(?<![-\w])border-radius:\s*([^;]+)", original_css)
                focal = re.search(r"--image-component-focal-point:\s*([^;]+)", original_css)
                native_ratio = re.search(r"--image-component-native-aspect-ratio:\s*(\d+)\s*/\s*(\d+)", original_css)
                ratio = int(native_ratio.group(1)) / int(native_ratio.group(2)) if native_ratio else width / height
                image_style = f"--image-ratio:{ratio};"
                corners = []
                for corner in ("top-left", "top-right", "bottom-right", "bottom-left"):
                    value = re.search(rf"border-{corner}-radius:\s*([^;]+)", original_css)
                    corners.append(value.group(1) if value else "0px")
                if any(value != "0px" for value in corners):
                    image_style += "--image-radius:" + " ".join(corners) + ";"
                if radius:
                    image_style += f"--image-radius:{radius.group(1)};"
                if focal:
                    image_style += f"--image-position:{focal.group(1)};"
                img = f'<img src="{html_std.escape(src)}" width="{width}" height="{height}" alt="{html_std.escape(alt)}" loading="lazy" decoding="async">'
                if href:
                    img = f'<a class="image-link image-frame" href="{html_std.escape(href)}">{img}</a>'
                else:
                    img = f'<div class="image-frame">{img}</div>'
                body = f'<div class="sqs-block image-block fit-{fit} image-align-{alignment}" style="{html_std.escape(image_style)}">{img}</div>'

    elif "horizontalrule-block" in kind:
        body = '<div class="sqs-block"><hr aria-hidden="true"></div>'
    elif "video-block" in kind:
        video_id = YOUTUBE_VIDEOS.get(page)
        if video_id:
            title = html_std.escape(TITLES[page].split(" — ")[0] + " — Project video")
            body = (f'<div class="sqs-block video-block">'
                    f'<iframe src="https://www.youtube-nocookie.com/embed/{video_id}" '
                    f'title="{title}" loading="lazy" '
                    'referrerpolicy="strict-origin-when-cross-origin" '
                    'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
                    'allowfullscreen></iframe></div>')
        else:
            body = f'<div class="sqs-block video-block"><img src="{video_poster}" alt="Project video cover" loading="lazy"></div>'
    if not body:
        return ""
    return f'<div class="{html_std.escape(block_class)}">{body}</div>'


def page_body(document, page: str) -> tuple[str, str]:
    sections = document.xpath('//article//section[@data-test="page-section"]')
    markup = []
    grid_css = []
    poster = next((url for (name, source), url in OUTPUT_CACHE.items() if name == page), "")
    background = ""
    if page in BACKGROUND_IMAGES:
        background = web_image(f"https://example.invalid/{BACKGROUND_IMAGES[page]}", page)
    for section in sections:
        engines = section.xpath('.//div[contains(concat(" ", normalize-space(@class), " "), " fluid-engine ")]')
        for engine in engines:
            style_nodes = engine.xpath('./preceding-sibling::style')
            if style_nodes:
                grid_css.append(style_nodes[-1].text or "")
            blocks = engine.xpath('./div[contains(concat(" ", normalize-space(@class), " "), " fe-block ")]')
            if not poster:
                for block in blocks:
                    image = block.xpath('.//img')
                    if image:
                        poster = web_image(image[0].get("data-src") or image[0].get("src") or "", page)
                        if poster:
                            break
            rendered = "\n".join(block_markup(block, page, poster) for block in blocks)
            bg_style = f' style="background-image:url(\'{background}\')"' if background else ""
            markup.append(f'<section class="portfolio-section {"dark" if section.get("data-section-theme") == "black" else "light"}"{bg_style}><div class="{html_std.escape(engine.get("class", ""))}">{rendered}</div></section>')
    return "\n".join(markup), "\n".join(grid_css)


def customize_home(body: str, grid_css: str) -> tuple[str, str]:
    """Move Bagua below Fox; retain an empty project slot at the old location."""
    from copy import deepcopy
    document = html.fragment_fromstring(body, create_parent="div")
    ids = ["de96d8f366034dfbdbd1", "342358eb2d278163c7de", "4aa92232216c58966446"]
    anchor = document.xpath('.//div[contains(@class,"fe-block-62fe5af491bbdc6fb8f9")]')[0]
    for suffix, name in zip(ids, ("image", "date", "link")):
        block = document.xpath(f'.//div[contains(@class,"fe-block-{suffix}")]')[0]
        moved = deepcopy(block)
        moved.set("class", f"fe-block fe-block-home-bagua-{name}")
        anchor.addnext(moved)
        anchor = moved
        if name == "image":
            for child in list(block):
                block.remove(child)
            block.append(html.fromstring('<div class="sqs-block" aria-hidden="true"></div>'))
        else:
            content = block.xpath('.//div[@class="sqs-html-content"]')[0]
            for child in list(content):
                content.remove(child)
            content.append(html.fromstring('<h4>XXX</h4>'))

    def shift_area(match):
        r1, c1, r2, c2 = map(int, match.groups())
        if r1 >= 53:
            r1 += 12
        if r2 > 53:
            r2 += 12
        return f"grid-area: {r1}/{c1}/{r2}/{c2};"

    grid_css = re.sub(r"grid-area:\s*(\d+)/(\d+)/(\d+)/(\d+);", shift_area, grid_css)
    grid_css = grid_css.replace("repeat(106,", "repeat(118,").replace("repeat(60,", "repeat(72,")
    grid_css += """
/* Homepage project relocation; space is reserved in both responsive grids. */
.fe-block-home-bagua-image { grid-area: 53/2/59/10; z-index: 2; }
.fe-block-home-bagua-date { grid-area: 59/2/61/10; z-index: 2; }
.fe-block-home-bagua-link { grid-area: 61/2/63/10; z-index: 2; }
.fe-block-home-bagua-image .sqs-block { justify-content: center; }
.fe-block-home-bagua-date .sqs-block,
.fe-block-home-bagua-link .sqs-block { justify-content: flex-start; }
@media (min-width: 768px) {
  .fe-block-home-bagua-image { grid-area: 53/3/60/10; }
  .fe-block-home-bagua-date { grid-area: 60/3/61/10; }
  .fe-block-home-bagua-link { grid-area: 61/3/62/12; }
}
"""
    return "".join(html.tostring(child, encoding="unicode") for child in document), grid_css


def render_page(page: str) -> None:
    document = html.fromstring((SNAPSHOTS / f"{page}.html").read_text(encoding="utf-8"))
    body, grid_css = page_body(document, page)
    if page == "home":
        body, grid_css = customize_home(body, grid_css)
    body = body.replace('loading="lazy"', 'loading="eager"', 8)
    if page == "home":
        bg_source = ROOT / "Assets" / "HomePage" / "BACKGROUND.png"
        if bg_source.exists():
            bg_url = web_image("https://example.invalid/BACKGROUND.png", page)
            body = f'<div class="home-background" style="background-image:url(\'{bg_url}\')">{body}</div>'
    css_dir = ROOT / "styles" / "pages"
    css_dir.mkdir(parents=True, exist_ok=True)
    grid_css = "\n".join(line.rstrip() for line in grid_css.splitlines()).strip("\n") + "\n"
    (css_dir / f"{page}.css").write_text(grid_css, encoding="utf-8")

    nav_class = ' class="current" aria-current="page"' if page == "aboutme" else ""
    html_page = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="DingQian Zhang's game design portfolio and projects.">
  <title>{html_std.escape(TITLES[page])}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Raleway:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/styles/site.css">
  <link rel="stylesheet" href="/styles/pages/{page}.css">
  <script src="/scripts/site.js" defer></script>
</head>
<body class="page-{page}">
  <a class="skip-link" href="#main">Skip to Content</a>
  <header class="site-header">
    <a class="site-title" href="/">DingQian Zhang — Game Design Portfolio</a>
    <nav class="desktop-nav" aria-label="Main navigation"><a href="/aboutme/"{nav_class}>AboutMe!</a></nav>
    <button class="menu-toggle" type="button" aria-label="Open Menu" aria-controls="mobile-menu" aria-expanded="false"><span></span><span></span></button>
    <nav class="mobile-nav" id="mobile-menu" aria-label="Mobile navigation" hidden><a href="/aboutme/"{nav_class}>AboutMe!</a></nav>
  </header>
  <main id="main">{'' if page in {'home', 'fox'} else f'<h1 class="visually-hidden">{html_std.escape(TITLES[page].split(' — ')[0])}</h1>'}{body}</main>
  <footer class="site-footer">©2026 Dingqian Zhang</footer>
</body>
</html>
'''
    target = ROOT / ("index.html" if page == "home" else f"{page}/index.html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html_page, encoding="utf-8")
    print(f"{page}: {len(body):,} HTML bytes, {len(grid_css):,} grid CSS bytes")


def main() -> None:
    for page in PAGES:
        snapshot = SNAPSHOTS / f"{page}.html"
        if not snapshot.exists():
            download(f"https://www.zhangdingqian.com/{page}", snapshot)
    for page in PAGES:
        render_page(page)
    if UNRESOLVED:
        print("UNRESOLVED IMAGES:\n" + "\n".join(UNRESOLVED))
    total = sum(path.stat().st_size for path in (ROOT / "media").rglob("*.webp"))
    print(f"media: {len(OUTPUT_CACHE)} files, {total / 1024 / 1024:.1f} MiB")


if __name__ == "__main__":
    main()
