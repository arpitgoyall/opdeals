import json
import re
from random import choice

import httpx
from aiohttp import ClientSession
from aiohttp.http_exceptions import HttpProcessingError
from fake_useragent import UserAgent

from cfg import GOOGLE_WEB_CACHE_PREFIX, PORTS, PROXY, logger
from yaab.wrappers import safe_execute

from .scraper import Scraper


class AmazonScraper(Scraper):
    def __init__(self) -> None:
        super().__init__("amazon")
        self.fetched_from_google_cache = False
        self.headers["Referer"] = "https://www.amazon.in"

    def pre_build_check(self) -> bool:
        return self._soup is not None

    def fetch_product_id(self, url: str) -> str:
        # Regular expression pattern to match ASIN in Amazon URLs
        asin_pattern = r"/([A-Z0-9]{10})(?:[/?]|$)"

        match = re.search(asin_pattern, url)
        if match:
            return match.group(1)
        else:
            return None

    def verify_product_url(self, url: str) -> bool:
        if "/dp/" in url or "/gp/" in url:
            return True
        else:
            logger.debug("Url verification failed: dp not found in url %s", url)
            return False

    def fetch_image_url(self) -> str:
        try:
            if self.fetched_from_google_cache:
                # find img with id main-image and get data-a-hires attribute
                image_attr = self.soup.find(id="main-image")
                if image_attr:
                    image_url = image_attr["data-a-hires"]
                    image_data = {"hiRes": image_url}
                else:
                    html = str(self.soup)
                    pattern = r"data-a-hires=\"(.+?)\""
                    image_url = re.findall(pattern, html)[0]
                    image_data = {"hiRes": image_url}
            else:
                html = str(self.soup)
                image_data = json.loads(
                    re.findall(r"colorImages':.*'initial':\s*(\[.+?\])},\n", html)[0]
                )
                image_data = image_data[0]
            img = image_data["hiRes"]
            if img:
                return img
            return image_data["large"]
        except (IndexError, KeyError):
            return None

    def fetch_title(self) -> str:
        if self.fetched_from_google_cache:
            # Find the meta tag with property="og:title"
            og_title_tag = self.soup.find("meta", {"property": "og:title"})
            # Extract the content attribute from the meta tag
            og_title_content = og_title_tag["content"]
            # Print the extracted content
            title = og_title_content
        else:
            title = self.soup.find(id="productTitle")
            if hasattr(title, "text"):
                title = title.text.strip()
        return title

    def fetch_mrp(self) -> str:
        mrp = self.soup.select(".basisPrice .a-price .a-offscreen")
        try:
            mrp = mrp[0].text.strip()
            mrp = mrp.split(".")[0].replace("₹", "")
        except IndexError:
            mrp = None
        return mrp

    def fetch_price(self) -> str:
        if self.fetched_from_google_cache:
            price = self.soup.select("#_price .normal-price")
            if not price:
                price = self.soup.select(".priceToPay .a-offscreen")
        else:
            price = self.soup.select(".priceToPay .a-offscreen")
        try:
            price = price[0].text.strip()
            if not price:
                price = self.soup.select(".priceToPay .a-price-whole")[0].text.strip()
            price = price.split(".")[0].replace("₹", "")
        except IndexError:
            price = None
        return price

    def fetch_discount_rate(self) -> str:
        discount = self.soup.select(".savingsPercentage")
        try:
            discount = discount[0].text.strip()
            discount = discount.replace("-", "")
        except IndexError:
            discount = None
        return discount

    def fetch_description(self) -> None:
        return None

    def fetch_features(self) -> str:
        try:
            if self.fetched_from_google_cache:
                description = self.soup.select("#productDescription_fullView span")
                features = None
                if description:
                    description = description[0].text.strip()
                if not description:
                    features = self.soup.select("#productFacts_feature_div")
                if not description:
                    logger.debug("Description not found, getting from feature bullets")
                    features = self.soup.select("#feature-bullets")
                if features:
                    features = features[0].select(".a-list-item")
                    description = "".join(
                        [feature.text.strip() for feature in features]
                    )
            else:
                description = self.soup.find(id="productDescription")
                if description:
                    description = description.text.strip()
                if not description:
                    logger.debug("Description not found, getting from feature bullets")
                    description = self.soup.select("#feature-bullets")
                    features = description[0].select(".a-list-item")
                    description = "".join(
                        [feature.text.strip() for feature in features]
                    )
        except IndexError:
            description = None
        if description and len(description) < 10:
            description = None
        return description
