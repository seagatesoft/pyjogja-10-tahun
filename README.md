# Web Scraping in the Era of LLM and Agentic AI

## The Past

1. **Handcrafted extraction rules**: CSS selector, XPath, regular expression, JavaScript variables, JMESPath, XHR endpoints, etc.
2. **Wrapper induction (supervised machine learning)**: extraction rules automatically generated based on a set of labelled examples.
3. **Automatic extraction**: heuristic extraction rules, computer vision techniques, etc.

## Web Scraping with LLM

1. Define output schema
2. Extract relevant texts from HTML
3. Input = output schema + texts, prompt LLM to extract data

Useful libraries
1. [Marvin](https://askmarvin.ai/)
2. [Instructor](https://python.useinstructor.com/)

Extracting structured data from free-form text is no longer a difficult task.

## Web Scraping with Agentic AI

* Simply tell AI to develop web scraper.
* Cheaper than live-extraction using LLM.
* Will break when there are website changes, but we can setup monitoring and auto-healing.
* Make AI to discover and handle all kinds of layout variations.
* Use [web-poet's page object testing](https://web-poet.readthedocs.io/en/stable/page-objects/testing.html) so AI can verify its own work.

## Demo

### Tech Stack

* Python
* [Scrapy](https://www.scrapy.org/)
* [web-poet](https://web-poet.readthedocs.io/en/stable/)
* [Zyte Agentic Skills](https://github.com/zytedata/skills)

### Web to scrape

* [Data Referensi Pendidikan Kemendikdasmen](https://referensi.data.kemendikdasmen.go.id/)
* [Events in Yogyakarta](https://visitingjogja.jogjaprov.go.id/event-agenda-pariwisata-jogja/) for structured data extraction from free-form text.

### Running the demo

The [meetup runbook](demo/RUNBOOK.md) includes the offline event replay, live parser repair, and fallback. Install the locked environment with `uv sync --locked`.

Run the full DIY DIKDAS crawl from this directory.

```sh
uv run --locked scrapy crawl diy_schools -O diy-schools.jsonl
```

The spider visits each of the five city and regency branches and exports one UTF-8 JSONL record per NPSN. The crawl summary reports discovered, enriched, and exported schools and flags failed directory or detail pages. It also compares the province index total with the number of distinct NPSNs exposed by the listings. Schools whose detail pages could not be read still have a row with the listing fields.

A shorter live smoke test uses the Mantrijeron district.

```sh
uv run --locked scrapy crawl diy_schools -a district=046001 -O /tmp/mantrijeron.jsonl
```

Run the offline tests with `uv run --locked python -m pytest -q --web-poet-test-per-item`.
