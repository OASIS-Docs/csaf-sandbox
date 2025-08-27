"""
Utilities for converting Markdown files to HTML.

The module provides :class:`MarkdownToHtmlConverter`, a helper that formats and
converts Markdown sources to HTML while downloading remote images and injecting
metadata. It is used by CI workflows and is considered an entrypoint script.
"""

from __future__ import annotations

import argparse
import logging
import os
import re
import subprocess
from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


# -------------------- small helpers --------------------

def sanitize_file_path(file_path: str) -> str:
    """Return a normalized, newline-free path."""
    sanitized = os.path.normpath(file_path.strip().replace("\n", ""))
    logger.debug("Sanitized file path: Original='%s' | Sanitized='%s'", file_path, sanitized)
    return sanitized


def _mkdirp(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def _is_tag(n) -> bool:
    return isinstance(n, Tag)


# -------------------- converter --------------------

class MarkdownToHtmlConverter:
    """Convert Markdown files to HTML with post-processing utilities."""

    # canonical host for public artifacts
    base_url = "https://docs.oasis-open.org"

    # default remote stylesheet used when a local one is not available
    css_file_name = "styles/markdown-styles-v1.7.3.css"   # remote path under base_url

    # Canonical public logo URL (authoritative)
    logo_canonical_remote = "https://docs.oasis-open.org/templates/OASISLogo-v3.0.png"
    logo_ok_src_regex = re.compile(r".*/OASISLogo-v3\.0\.png$", re.IGNORECASE)

    # repo-relative output subdirs
    images_subdir = "images"    # for localized images next to the output HTML
    styles_subdir = "styles"    # for localized CSS next to the output HTML

    def __init__(
        self,
        md_file: str,
        output_file: str,
        git_repo_basedir: Optional[str] = None,
        md_dir: Optional[str] = None,
    ) -> None:
        self.md_file = sanitize_file_path(md_file)
        self.output_file = sanitize_file_path(output_file)
        self.git_repo_basedir = sanitize_file_path(git_repo_basedir) if git_repo_basedir else None
        self.md_dir = sanitize_file_path(md_dir) if md_dir else None

        logger.info("Initialized MarkdownToHtmlConverter with:")
        logger.info("  Markdown File: %s", self.md_file)
        logger.info("  Output File: %s", self.output_file)
        logger.info("  Git Repo Base Dir: %s", self.git_repo_basedir)
        logger.info("  Markdown Directory: %s", self.md_dir)

        self.meta_description = self._extract_meta_description(step=1)
        self.html_title = self._extract_html_title(step=2)

        out_dir = os.path.dirname(self.output_file)
        self.styles_dir = os.path.join(out_dir, self.styles_subdir)
        self.images_dir = os.path.join(out_dir, self.images_subdir)
        _mkdirp(self.images_dir)

        local_styles_css = os.path.join(self.styles_dir, "styles.css")
        if os.path.exists(local_styles_css):
            self.css_ref_for_pandoc = os.path.join(self.styles_subdir, "styles.css")
        else:
            self.css_ref_for_pandoc = os.path.join(self.base_url, self.css_file_name)

        self.base_href_remote = self._construct_abs_doc_url(self.git_repo_basedir, self.md_dir)
        self._abs_doc_parsed = urlparse(self.base_href_remote)
        self._abs_doc_dir = (self._abs_doc_parsed.path.rsplit("/", 1)[0] + "/") if self._abs_doc_parsed.path else "/"

    def _extract_meta_description(self, step: int) -> str:
        logger.info("Step %s: Extracting meta description from: %s", step, self.md_file)
        try:
            with open(self.md_file, "r", encoding="utf-8") as f:
                for line in f:
                    # Look for meta description in markdown comments or front matter
                    if line.strip().startswith("<!--") and "description:" in line.lower():
                        # Extract description from HTML comment
                        desc_start = line.lower().find("description:") + len("description:")
                        desc_end = line.find("-->")
                        if desc_end > desc_start:
                            return line[desc_start:desc_end].strip()
                    elif line.strip().startswith("description:"):
                        # Extract from YAML front matter style
                        return line.split(":", 1)[1].strip().strip('"\'')
            logger.warning("Step %s: No meta description found.", step)
            return "-"
        except Exception:
            logger.error("Step %s: Error extracting meta description", step, exc_info=True)
            return "-"

    def _extract_html_title(self, step: int) -> str:
        logger.info("Step %s: Extracting HTML title from: %s", step, self.md_file)
        try:
            with open(self.md_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("# "):  # first H1
                        return line.strip("# ").strip()
            logger.warning("Step %s: No HTML title found.", step)
            return "-"
        except Exception:
            logger.error("Step %s: Error extracting HTML title", step, exc_info=True)
            return "-"

    def _read_file(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            logger.error("Failed to read %s", file_path, exc_info=True)
            raise

    def _write_file(self, file_path: str, content: str) -> None:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            logger.error("Failed to write %s", file_path, exc_info=True)
            raise

    def _construct_abs_doc_url(self, git_repo_basedir: Optional[str], md_dir: Optional[str]) -> str:
        if not git_repo_basedir or not md_dir:
            logger.warning("Git base or md_dir not provided; falling back to %s", self.base_url)
            return self.base_url
        relative_md_dir = os.path.relpath(md_dir, git_repo_basedir)
        if relative_md_dir == ".":
            relative_md_dir = ""
        if relative_md_dir:
            return f"{self.base_url}/{relative_md_dir}/{os.path.basename(self.output_file)}"
        return f"{self.base_url}/{os.path.basename(self.output_file)}"

    def _run_pandoc(self, step: int) -> None:
        logger.info("Step %s: Running pandoc.", step)
        cmd = [
            "pandoc",
            self.md_file,
            "-f", "markdown+autolink_bare_uris+hard_line_breaks",
            "-c", self.css_ref_for_pandoc,
            "-s",
            "-o", "temp_output.html",
            "--metadata", f"title={self.html_title}",
            "--toc"  # ### FIX ###: Explicitly tell Pandoc to create the Table of Contents
        ]
        logger.debug("Pandoc command: %s", " ".join(cmd))
        try:
            subprocess.run(cmd, check=True)
            logger.info("Step %s: pandoc OK.", step)
        except subprocess.CalledProcessError:
            logger.error("Step %s: pandoc failed", step, exc_info=True)
            raise

    def _convert_plain_urls_to_links(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        url_re = re.compile(r"(https?://[^\s<]+)")
        for p in soup.find_all("p"):
            if p.find(True):
                continue  # already has tags
            text = p.get_text()
            if "http" not in text:
                continue
            new_html = url_re.sub(lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', text)
            p.clear()
            p.append(BeautifulSoup(new_html, "html.parser"))
        return str(soup)

    def _normalize_same_doc_anchors_for_web(self, soup: BeautifulSoup, output_basename: str) -> None:
        """
        ### FIX ###: This function is now the primary method for fixing TOC and internal links.
        It robustly finds any link pointing to the same document and rewrites it
        to be a simple fragment-only link (e.g., "#section-1").
        """
        for a in soup.find_all("a", href=True):
            href = (a["href"] or "").strip()
            if not href:
                continue
            # If it's already a clean fragment link, we're good.
            if href.startswith("#"):
                a.attrs.pop("target", None)
                continue

            p = urlparse(href)
            # We only care about links that have a fragment identifier.
            if not p.fragment:
                continue

            same_doc = False
            # Case 1: Relative link like "my-doc.html#section" or just "#section"
            if not p.scheme and not p.netloc:
                if (p.path == "") or (os.path.basename(p.path) == output_basename):
                    same_doc = True
            # Case 2: Absolute link back to this exact same document
            else:
                if os.path.basename(p.path) == output_basename:
                    same_doc = True
            
            # If it's a same-document link, rewrite href to be just the fragment.
            if same_doc:
                new_href = f"#{p.fragment}"
                logger.debug(f"Normalizing same-document anchor: '{href}' -> '{new_href}'")
                a["href"] = new_href
                a.attrs.pop("target", None)

    def _is_same_site_same_scope(self, url: str) -> Optional[str]:
        try:
            p = urlparse(url)
        except Exception:
            return None
        if not p.scheme or not p.netloc:
            return None
        if (p.scheme, p.netloc) != (self._abs_doc_parsed.scheme, self._abs_doc_parsed.netloc):
            return None
        if not p.path.startswith(self._abs_doc_dir):
            return None
        return p.path[len(self._abs_doc_dir):]

    def _relativize_same_scope_links(self, soup: BeautifulSoup) -> None:
        # This function remains as it was in the original script.
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#"):
                continue
            tail = self._is_same_site_same_scope(href)
            if not tail:
                continue
            from urllib.parse import urlparse as _p
            pp = _p(href)
            if os.path.basename(pp.path) == os.path.basename(self.output_file):
                if pp.fragment:
                    a["href"] = f"#{pp.fragment}"
                else:
                    a["href"] = os.path.basename(pp.path)
                a.attrs.pop("target", None)
            else:
                a["href"] = tail.lstrip("/")
        # ... (rest of the original function is preserved)
        for link in soup.find_all("link", href=True):
            tail = self._is_same_site_same_scope(link["href"].strip())
            if tail:
                link["href"] = tail.lstrip("/")
        for s in soup.find_all("script", src=True):
            tail = self._is_same_site_same_scope(s["src"].strip())
            if tail:
                s["src"] = tail.lstrip("/")
        for img in soup.find_all("img", src=True):
            tail = self._is_same_site_same_scope(img["src"].strip())
            if tail:
                img["src"] = tail.lstrip("/")


    def _first_tag_child(self, parent: Tag) -> Tag | None:
        for c in parent.children:
            if isinstance(c, Tag):
                return c
        return None

    def _looks_like_logo_src(self, src: str) -> bool:
        if not src:
            return False
        return ("OASISLogo-v3.0.png" in src or src == self.logo_canonical_remote or bool(self.logo_ok_src_regex.match(src)))

    def _is_canonical_logo_img(self, img: Tag, body: Tag) -> bool:
        if img.name != "img": return False
        src = (img.get("src") or "").strip()
        alt = (img.get("alt") or "").strip()
        if not (self._looks_like_logo_src(src) and alt == "OASIS Logo"): return False
        parent = img.parent
        if not (parent and parent.name == "p" and parent.parent is body): return False
        return parent is self._first_tag_child(body)

    def _enforce_single_oasis_logo(self, soup: BeautifulSoup) -> None:
        # This function is preserved from your original script.
        body = soup.body or soup
        for img in list(soup.find_all("img")):
            src = (img.get("src") or "")
            alt = (img.get("alt") or "")
            if ("OASISLogo" in src) or (alt.strip() == "OASIS Logo"):
                if not self._is_canonical_logo_img(img, body):
                    p = img.parent
                    if p and p.name == "p" and all((isinstance(x, Tag) and x.name == "img") or str(x).strip() == "" for x in p.contents):
                        p.decompose()
                    else:
                        img.decompose()
        first_el = self._first_tag_child(body)
        current_good = None
        if first_el and first_el.name == "p":
            maybe_img = first_el.find("img", recursive=False) or first_el.find("img")
            if maybe_img and self._is_canonical_logo_img(maybe_img, body):
                current_good = first_el
        if not current_good:
            existing_good_img = None
            for img in soup.find_all("img"):
                src = (img.get("src") or "")
                alt = (img.get("alt") or "")
                if self._looks_like_logo_src(src) and alt == "OASIS Logo":
                    existing_good_img = img
                    break
            if existing_good_img:
                container = existing_good_img.parent if (existing_good_img.parent and existing_good_img.parent.name == "p") else None
                if not container:
                    container = soup.new_tag("p")
                    existing_good_img.replace_with(container)
                    container.append(existing_good_img)
                first_tag = self._first_tag_child(body)
                if first_tag:
                    first_tag.insert_before(container)
                else:
                    body.insert(0, container)
            else:
                p = soup.new_tag("p")
                img = soup.new_tag("img", src=self.logo_canonical_remote, alt="OASIS Logo")
                p.append(img)
                first_tag = self._first_tag_child(body)
                if first_tag:
                    first_tag.insert_before(p)
                else:
                    body.insert(0, p)
        for img in list(soup.find_all("img")):
            src = (img.get("src") or "")
            alt = (img.get("alt") or "")
            if ("OASISLogo" in src) or (alt.strip() == "OASIS Logo"):
                if not self._is_canonical_logo_img(img, body):
                    p = img.parent
                    if p and p.name == "p" and all((isinstance(x, Tag) and x.name == "img") or str(x).strip() == "" for x in p.contents):
                        p.decompose()
                    else:
                        img.decompose()

    def _fix_top_banner_block(self, soup: BeautifulSoup) -> None:
        # This function is preserved from your original script.
        body = soup.body or soup
        logo_p = None
        for p_tag in body.find_all("p", recursive=False):
            img = p_tag.find("img", recursive=False)
            if img and self._is_canonical_logo_img(img, body):
                logo_p = p_tag
                break
        if not logo_p:
            logger.warning("Could not find the canonical OASIS logo paragraph. Skipping banner fix.")
            return
        first_heading = None
        for sibling in logo_p.find_next_siblings():
            if _is_tag(sibling) and sibling.name in ("h1", "h1big", "h2", "h3", "h4", "h5", "h6"):
                first_heading = sibling
                break
        if not first_heading:
            logger.warning("Could not find a heading after the OASIS logo. Skipping banner fix.")
            return
        node = logo_p.next_sibling
        while node and node != first_heading:
            if _is_tag(node) and node.name == "hr":
                next_node = node.next_sibling
                logger.debug("Removing extraneous <hr> tag between logo and title.")
                node.decompose()
                node = next_node
            else:
                node = node.next_sibling
        next_elem = logo_p.next_sibling
        while next_elem and not _is_tag(next_elem):
            next_elem = next_elem.next_sibling
        if not (next_elem and next_elem.name == "hr" and "page-break-before: avoid" in next_elem.get("style", "")):
             if next_elem != first_heading:
                styled_hr = soup.new_tag("hr")
                styled_hr["style"] = "page-break-before: avoid"
                logo_p.insert_after(styled_hr)
        if first_heading.name == "h1":
            logger.debug("Upgrading first <h1> to <h1big> to prevent premature page break.")
            first_heading.name = "h1big"

    def _remove_duplicate_heading_anchors(self, soup: BeautifulSoup) -> None:
        """
        ### FIX ###: Remove duplicate anchor tags inside headings that have the same ID.
        This fixes the internal linking issue where TOC links don't work due to duplicate IDs.
        """
        for heading in soup.find_all(["h1", "h1big", "h2", "h3", "h4", "h5", "h6"]):
            heading_id = heading.get("id")
            if heading_id:
                # Find any anchor tags inside this heading with the same ID
                duplicate_anchors = heading.find_all("a", id=heading_id)
                for anchor in duplicate_anchors:
                    logger.debug(f"Removing duplicate anchor with id='{heading_id}' from heading")
                    # Remove the anchor tag but keep its text content
                    if anchor.string:
                        anchor.replace_with(anchor.string)
                    else:
                        anchor.decompose()

    def _post_process_html(self, html: str, step: int) -> str:
        logger.info("Step %s: Post-processing HTML.", step)
        soup = BeautifulSoup(html, "html.parser")

        if soup.header:
            soup.header.decompose()

        meta_tag = soup.new_tag("meta", attrs={"name": "description", "content": self.meta_description})
        soup.head.insert(0, meta_tag)
        
        # ### FIX ###: Remove or fix base href to prevent TOC fragment links from breaking.
        # The base href causes fragment-only links (#section) to resolve incorrectly.
        base_tag = soup.find("base")
        if base_tag:
            # Remove the base tag entirely to fix fragment link navigation
            base_tag.decompose()
            logger.debug("Removed base tag to fix internal fragment links")

        for fig in list(soup.find_all("figure")):
            img = fig.find("img")
            if img and self._looks_like_logo_src(img.get("src", "")):
                fig.decompose()

        # Kill stray TOC <nav> blocks; our own TOC logic is handled differently.
        if soup.nav:
            soup.nav.decompose()

        self._enforce_single_oasis_logo(soup)
        self._fix_top_banner_block(soup)
        self._remove_duplicate_heading_anchors(soup)  # ### FIX ###: Remove duplicate anchor IDs
        self._normalize_same_doc_anchors_for_web(soup, output_basename=os.path.basename(self.output_file))
        
        soup_str = self._convert_plain_urls_to_links(str(soup))
        soup = BeautifulSoup(soup_str, "html.parser")

        if os.getenv("HTML_LOCALIZE_CSS", "").lower() in {"1", "true", "yes"}:
            _mkdirp(self.styles_dir)
            for link in list(soup.find_all("link", rel=True, href=True)):
                if (link.get("rel") or [""])[0].lower() != "stylesheet": continue
                href = link["href"].strip()
                pr = urlparse(href)
                if pr.scheme in {"http", "https"}:
                    css_name = os.path.basename(pr.path) or "style.css"
                    local_css = os.path.join(self.styles_dir, css_name)
                    if not os.path.exists(local_css):
                        try:
                            logger.info("Downloading CSS %s -> %s", href, local_css)
                            r = requests.get(href, timeout=10)
                            r.raise_for_status()
                            with open(local_css, "wb") as f: f.write(r.content)
                        except RequestException:
                            logger.error("Failed to download CSS: %s", href, exc_info=True)
                            continue
                    link["href"] = os.path.join(self.styles_subdir, css_name)
        
        for img in list(soup.find_all("img", src=True)):
            src = img["src"].strip()
            pr = urlparse(src)
            if pr.scheme in {"http", "https"}:
                image_filename = os.path.basename(pr.path) or "image"
                local_image_path = os.path.join(self.images_dir, image_filename)
                if not os.path.exists(local_image_path):
                    try:
                        logger.info("Downloading image %s -> %s", src, local_image_path)
                        r = requests.get(src, timeout=10)
                        r.raise_for_status()
                        with open(local_image_path, "wb") as f: f.write(r.content)
                    except RequestException:
                        logger.error("Failed to download image %s", src, exc_info=True)
                        img.decompose()
                        continue
                img["src"] = os.path.join(self.images_subdir, image_filename)
                if img.has_attr("srcset"):
                    del img["srcset"]

        self._relativize_same_scope_links(soup)
        
        final = str(soup)
        logger.info("Step %s: Post-processing complete.", step)
        return final

    def run_prettier(self) -> None:
        logger.info("Running Prettier on Markdown.")
        try:
            subprocess.run(["prettier", "--write", self.md_file.strip()], check=True)
        except subprocess.CalledProcessError:
            logger.error("Prettier failed", exc_info=True)
            raise

    def ensure_toc_title(self) -> None:
        logger.info("Ensuring TOC title exists.")
        try:
            with open(self.md_file, "r", encoding="utf-8") as f: content = f.read()
            toc_found = re.search(r"(- \[.*\]\(.*\))", content)
            toc_title_present = re.search(r"^\s*#+\s*Table of Contents\s*$", content, re.IGNORECASE | re.MULTILINE)
            if toc_found and not toc_title_present:
                lines = content.split("\n")
                toc_indices = [i for i, line in enumerate(lines) if re.match(r"- \[.*\]\(.*\)", line)]
                if toc_indices:
                    lines.insert(toc_indices[0], "\n# Table of Contents")
                    with open(self.md_file, "w", encoding="utf-8") as f2: f2.write("\n".join(lines))
                    logger.info("Inserted TOC title.")
        except Exception:
            logger.error("Error ensuring TOC title", exc_info=True)

    def convert(self) -> None:
        temp_output = "temp_output.html"
        try:
            step = 3
            logger.info("Step %s: Begin conversion.", step)
            self.ensure_toc_title(); step += 1
            self._run_pandoc(step=step); step += 1
            html_content = self._read_file(temp_output)
            final_html = self._post_process_html(html_content, step=step); step += 1
            self._write_file(self.output_file, final_html)
            logger.info("Step %s: Conversion done.", step)
        except Exception:
            logger.error("Conversion error", exc_info=True)
            raise
        finally:
            if os.path.exists(temp_output):
                os.remove(temp_output)
                logger.debug("Removed %s", temp_output)


# -------------------- CLI --------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Markdown to HTML Converter")
    parser.add_argument("md_file", type=str, help="Path to the markdown file")
    parser.add_argument("git_repo_basedir", type=str, help="Base directory of git repository")
    parser.add_argument("md_dir", type=str, help="Directory containing markdown file")
    parser.add_argument("--test", action="store_true", help="Run in test mode")
    parser.add_argument("--md-format", action="store_true", help="Run Prettier to format the markdown file")
    parser.add_argument("--md-to-html", action="store_true", help="Convert markdown file to HTML")
    args = parser.parse_args()

    if args.test:
        git_repo_basedir = "/github/workspace"
        md_dir = git_repo_basedir
        md_file = os.path.join(md_dir, "example.md")
        output_file = os.path.join(md_dir, "example.html")
    else:
        git_repo_basedir = sanitize_file_path(args.git_repo_basedir)
        md_dir = sanitize_file_path(args.md_dir)
        md_file = sanitize_file_path(args.md_file)
        output_file = os.path.join(md_dir, os.path.basename(md_file).replace(".md", ".html"))

    converter = MarkdownToHtmlConverter(md_file, output_file, git_repo_basedir, md_dir)

    if args.md_format:
        converter.run_prettier()
        logger.info("Markdown formatting completed.")

    if args.md_to_html:
        converter.convert()
        logger.info("Markdown to HTML conversion completed.")


if __name__ == "__main__":
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler("markdown_conversion.log"), logging.StreamHandler()],
    )
    main()
