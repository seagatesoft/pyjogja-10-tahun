import asyncio
from pathlib import Path

from scrapy.crawler import Crawler
from scrapy.http import HtmlResponse
from scrapy.statscollectors import MemoryStatsCollector

from diy_scraper.pages import FIELDS
from diy_scraper.spiders.diy_schools import DiySchoolsSpider, HOST, START

DATA = Path(__file__).parent / "data"
SCHOOL = Path("fixtures/diy_scraper.pages.SchoolPage/gedongkiwo/inputs/HttpResponse-body.html")


def test_directory_and_school():
    crawler = Crawler(DiySchoolsSpider)
    crawler.stats = MemoryStatsCollector(crawler)
    spider = DiySchoolsSpider.from_crawler(crawler)
    index = HtmlResponse(START, body=(DATA / "diy-index.html").read_bytes(), encoding="utf-8")
    branches = list(spider.parse_directory(index))
    assert {request.cb_kwargs["kabupaten"] for request in branches} == {
        "Kab. Bantul", "Kab. Sleman", "Kab. Gunungkidul", "Kab. Kulon Progo", "Kota Yogyakarta",
    }
    assert crawler.stats.get_value("schools/index_total") == 2668

    district_url = f"https://{HOST}/pendidikan/dikdas/046001/3"
    district = HtmlResponse(district_url, body=(DATA / "mantrijeron.html").read_bytes(), encoding="utf-8")
    region = {"level": 3, "kabupaten": "Kota Yogyakarta", "kecamatan": "Mantrijeron"}
    requests = list(spider.parse_directory(district, **region))
    request = next(request for request in requests if request.url.endswith("/20403484"))
    assert list(spider.parse_directory(district, **region)) == []

    detail = HtmlResponse(request.url, body=SCHOOL.read_bytes(), encoding="utf-8")
    record = asyncio.run(request.callback(detail, **request.cb_kwargs))
    assert tuple(record) == FIELDS
    assert (record["kabupaten"], record["kecamatan"], record["npsn"]) == (
        "Kota Yogyakarta", "Mantrijeron", "20403484",
    )
    assert (record["status"], record["latitude"], record["longitude"]) == ("negeri", -7.819, 110.3535)

    wrong_body = SCHOOL.read_bytes().replace(b">20403484<", b">20403485<")
    mismatch = HtmlResponse(request.url, body=wrong_body, encoding="utf-8")
    fallback = asyncio.run(request.callback(mismatch, **request.cb_kwargs))
    assert fallback["npsn"] == record["npsn"]
    assert fallback["nama_satuan_pendidikan"] == record["nama_satuan_pendidikan"]
    assert fallback["bentuk_pendidikan"] is None
    assert fallback["website"] is None
    assert crawler.stats.get_value("schools/failed_details") == 1
