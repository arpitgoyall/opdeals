import httpx
from bs4 import BeautifulSoup
import logging
import re

logger = logging.getLogger(__name__)

HEADERS = {
    # More browser-like header set to reduce bot detection
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "DNT": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Referer": "https://www.amazon.in",
}

class Scraper:
    async def scrape(self, url: str):
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=12.0, http2=True, headers=HEADERS) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                final_url = str(response.url)
                soup = BeautifulSoup(response.text, 'html.parser')
                domain = self._get_domain(final_url)
                logger.info(f"Resolved {url} to {final_url} (Domain: {domain})")
                
                # Only support Amazon; ignore all other domains
                if "amazon" in domain:
                    return self._scrape_amazon(soup, final_url)

                logger.info(f"Ignoring non-Amazon domain: {domain}")
                return None
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {e}")
            return None

    def _get_domain(self, url):
        return url.split("//")[-1].split("/")[0]

    def _is_valid_amazon_product_url(self, url: str) -> bool:
        return "/dp/" in url or "/gp/" in url

    def _scrape_amazon(self, soup, url):
        # Only process valid product URLs
        if not self._is_valid_amazon_product_url(url):
            logger.info(f"Skipping non-product Amazon URL: {url}")
            return None
        # Title
        title_el = soup.select_one("#productTitle")
        title = title_el.get_text(strip=True) if title_el else None
        if not title:
            meta_title = soup.find("meta", {"property": "og:title"})
            if meta_title and meta_title.get("content"):
                title = meta_title["content"].strip()

        # Price: try multiple selectors in priority order
        price_text = None
        selectors_price = [
            ".priceToPay .a-offscreen",
            "#corePrice_desktop .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price .a-offscreen",
            ".a-price-whole",
        ]
        for sel in selectors_price:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                price_text = el.get_text(strip=True)
                break

        # MRP
        mrp_text = None
        selectors_mrp = [
            ".basisPrice .a-price .a-offscreen",
            "#price .a-text-price .a-offscreen",
            ".a-text-price .a-offscreen",
        ]
        for sel in selectors_mrp:
            el = soup.select_one(sel)
            if el and el.get_text(strip=True):
                mrp_text = el.get_text(strip=True)
                break

        # Image: prefer landingImage, else parse colorImages JSON
        image_url = ""
        landing = soup.select_one("#landingImage")
        if landing and landing.has_attr("src"):
            image_url = landing["src"]
        else:
            html = str(soup)
            try:
                images_json = re.findall(r"colorImages':.*'initial':\s*(\[.+?\])},\n", html)
                if images_json:
                    import json as _json
                    data = _json.loads(images_json[0])
                    first = data[0] if isinstance(data, list) and data else {}
                    image_url = first.get("hiRes") or first.get("large") or ""
            except Exception:
                image_url = ""

        def _normalize_amount(txt):
            if not txt:
                return "0"
            # Extract the first numeric token with optional commas and decimal part
            m = re.search(r"(\d[\d,]*\.?\d*)", txt)
            if not m:
                return "0"
            num = m.group(1).replace(",", "")
            try:
                val = float(num)
                # Return int if .00, else trimmed float string
                if val.is_integer():
                    return str(int(val))
                # Trim trailing zeros and dot
                s = f"{val}"
                s = s.rstrip('0').rstrip('.')
                return s
            except Exception:
                return "0"

        price_val = _normalize_amount(price_text)
        mrp_val = _normalize_amount(mrp_text)

        deal = {
            "title": title or "No Title",
            "price": price_val,
            "mrp": mrp_val,
            "image": image_url,
            "source": "Amazon",
            "url": url,
        }

        # Validate completeness: require title, price>0, mrp>0, image present, url present
        try:
            price_ok = int(deal["price"]) > 0
        except Exception:
            price_ok = False
        try:
            mrp_ok = int(deal["mrp"]) > 0
        except Exception:
            mrp_ok = False
        title_ok = bool(deal["title"] and deal["title"].strip() and deal["title"] != "No Title")
        image_ok = bool(deal["image"])
        url_ok = bool(deal["url"])

        if not (title_ok and price_ok and mrp_ok and image_ok and url_ok):
            # Log a small snippet of body for diagnostics (avoid huge logs)
            body_snippet = str(soup)[:500].replace("\n", " ")
            logger.info(
                "Skipping incomplete deal (title_ok=%s, price_ok=%s, mrp_ok=%s, image_ok=%s, url_ok=%s). Body snippet: %s",
                title_ok, price_ok, mrp_ok, image_ok, url_ok, body_snippet
            )
            return None

        return deal

    def _scrape_flipkart(self, soup, url):
        # Ignored in current configuration; kept for future use.
        return None

scraper_service = Scraper()
