# DingQian Zhang — Game Design Portfolio

Static GitHub Pages version of [zhangdingqian.com](https://www.zhangdingqian.com/).

The published site has a home page, AboutMe page, and six project pages. Each project is a directory with its own `index.html`, so direct links such as `/tiletale/` work on GitHub Pages. Layout and navigation styles are shared in `styles/site.css`; the page-specific grid positions are in `styles/pages/`. The mobile menu is in `scripts/site.js`.

`media/` contains web-sized WebP copies. The original `Assets/` folder remains local and is ignored by Git. PSDs and MP4s are not published.

Video areas currently show a cover image. When YouTube links are ready, replace each `.video-block` in the relevant page's `index.html` with an embedded player using the video's privacy-enhanced `youtube-nocookie.com` URL and a descriptive `title`.

To preview locally, serve the repository root with any static HTTP server (for example, `python -m http.server 8765`).

`tools/build_from_reference.py` can regenerate the pages and optimized images from the public original site and a local `Assets/` folder. It requires Python with `lxml` and `Pillow`. It overwrites generated page files, so edit those directly for small updates such as future YouTube embeds.
