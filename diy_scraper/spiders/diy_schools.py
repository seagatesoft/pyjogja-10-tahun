import re
from urllib.parse import urlsplit

import scrapy
from web_poet import HttpResponse

from diy_scraper.pages import FIELDS, SchoolPage, cell_text, school_status

HOST = "referensi.data.kemendikdasmen.go.id"
START = f"https://{HOST}/pendidikan/dikdas/040000/1"
DIRECTORY = r"/pendidikan/dikdas/\d{6}/"
DETAIL = r"/pendidikan/npsn/([A-Za-z0-9]{8})"
LIST_FIELDS = {
    "Nama Satuan Pendidikan": "nama_satuan_pendidikan",
    "Alamat": "alamat",
    "Kelurahan": "kelurahan",
    "Status": "status",
}


class DiySchoolsSpider(scrapy.Spider):
    name = "diy_schools"
    allowed_domains = [HOST]

    def __init__(self, district=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.district = district
        self.seen_npsns = set()

    async def start(self):
        yield scrapy.Request(START, self.parse_directory, errback=self.directory_failed)

    def _increment(self, name):
        self.crawler.stats.inc_value(f"schools/{name}")

    @staticmethod
    def _url(response, href, pattern):
        if href:
            url = response.urljoin(href)
            parts = urlsplit(url)
            if parts.scheme == "https" and parts.netloc == HOST and re.fullmatch(pattern, parts.path):
                return url

    def directory_failed(self, failure):
        self._directory_error(failure.request.url, failure.getErrorMessage())

    def _directory_error(self, url, reason):
        self._increment("failed_directory_pages")
        self.logger.error("Directory page %s: %s", url, reason)

    def parse_directory(self, response, level=1, kabupaten=None, kecamatan=None):
        table = response.css("table#table1")
        headers = [cell_text(cell) for cell in table.css("thead th")]
        key = {1: "Nama Kota/Kabupaten", 2: "Nama Kecamatan", 3: "NPSN"}[level]
        if key not in headers or (level == 3 and not LIST_FIELDS.keys() <= set(headers)):
            self._directory_error(response.url, "missing expected directory table or columns")
            return

        rows = table.css("tbody tr")
        if level < 3 and not rows:
            self._directory_error(response.url, "no region rows")
        if level == 2 and not urlsplit(response.url).query:
            self._increment("city_regency_branches")

        for row in rows:
            cells = row.xpath("./td")
            if len(cells) != len(headers):
                continue
            values = dict(zip(headers, cells))
            cell = values[key]
            label = cell_text(cell)
            pattern = DETAIL if level == 3 else DIRECTORY + str(level + 1)
            url = self._url(response, cell.css("a::attr(href)").get(), pattern)
            if level < 3:
                if label and url:
                    if level == 1 and "Total" in values:
                        total = cell_text(values["Total"])
                        if total and total.isdecimal():
                            self.crawler.stats.inc_value("schools/index_total", int(total))
                    if level == 2 and self.district and urlsplit(url).path.split("/")[-2] != self.district:
                        continue
                    yield scrapy.Request(
                        url, self.parse_directory, errback=self.directory_failed,
                        cb_kwargs={
                            "level": level + 1,
                            "kabupaten": label if level == 1 else kabupaten,
                            "kecamatan": label if level == 2 else None,
                        },
                    )
                elif label:
                    self._directory_error(response.url, f"missing region link for {label}")
                continue

            if not label or not re.fullmatch(r"[A-Za-z0-9]{8}", label):
                if label:
                    self._directory_error(response.url, f"invalid NPSN {label}")
                continue
            if label in self.seen_npsns:
                self._increment("duplicate_listings")
                continue
            self.seen_npsns.add(label)
            self._increment("discovered")
            listing = {"kabupaten": kabupaten, "kecamatan": kecamatan, "npsn": label}
            listing.update({field: cell_text(values[header]) for header, field in LIST_FIELDS.items()})
            listing["status"] = school_status(listing["status"])
            if url and urlsplit(url).path.rsplit("/", 1)[1] == label:
                yield scrapy.Request(
                    url, self.parse_school, errback=self.school_failed,
                    cb_kwargs={"listing": listing},
                )
            else:
                yield self._school_error(listing, "missing or mismatched detail link")

        # The directory currently renders all rows in HTML and paginates them in
        # DataTables. Follow server-side pagination if the branch exposes links.
        path = urlsplit(response.url).path
        for href in response.css('a[rel~="next"]::attr(href), .pagination a::attr(href)').getall():
            url = self._url(response, href, re.escape(path))
            if url and urlsplit(url).query:
                yield scrapy.Request(
                    url, self.parse_directory, errback=self.directory_failed,
                    cb_kwargs={"level": level, "kabupaten": kabupaten, "kecamatan": kecamatan},
                )

    async def parse_school(self, response, listing):
        page = SchoolPage(HttpResponse(url=response.url, body=response.body, encoding=response.encoding))
        detail = await page.to_item()
        if detail["npsn"] != listing["npsn"]:
            return self._school_error(listing, f"detail returned NPSN {detail['npsn']!r}")
        self._increment("enriched")
        return self._record(listing, detail)

    def school_failed(self, failure):
        return self._school_error(failure.request.cb_kwargs["listing"], failure.getErrorMessage())

    def _school_error(self, listing, reason):
        self._increment("failed_details")
        self.logger.warning("Detail for NPSN %s: %s", listing["npsn"], reason)
        return self._record(listing, {})

    def _record(self, listing, detail):
        self._increment("exported")
        return {field: detail.get(field) if detail.get(field) is not None else listing.get(field) for field in FIELDS}

    def closed(self, reason):
        stats = self.crawler.stats
        counts = {key: stats.get_value(f"schools/{key}", 0) for key in (
            "city_regency_branches", "index_total", "discovered", "enriched", "exported",
            "failed_directory_pages", "failed_details",
        )}
        self.logger.info("School crawl summary (%s) %s", reason, counts)
        if not self.district and counts["index_total"] and counts["index_total"] != counts["discovered"]:
            self.logger.warning(
                "The province index reports %d schools and the listings expose %d distinct NPSNs",
                counts["index_total"], counts["discovered"],
            )
        if reason != "finished" or counts["failed_directory_pages"] or counts["failed_details"] or (
            not self.district and counts["city_regency_branches"] != 5
        ) or counts["discovered"] != counts["exported"] or not counts["exported"]:
            self.logger.warning("School export is incomplete or the crawl did not finish cleanly")
