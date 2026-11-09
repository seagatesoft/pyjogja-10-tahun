import re

from web_poet import WebPage

FIELDS = (
    "kabupaten", "kecamatan", "npsn", "nama_satuan_pendidikan", "alamat",
    "kelurahan", "status", "bentuk_pendidikan", "jenjang_pendidikan",
    "kementerian_pembina", "website", "operator", "latitude", "longitude",
)


def clean(value):
    if value is None:
        return None
    value = " ".join(value.split())
    return None if value.casefold() in {"", "-", "–", "—", "n/a", "null"} else value


def cell_text(cell):
    return clean(cell.xpath("string(.)").get())


def school_status(value):
    value = (value or "").casefold()
    return value if value in {"swasta", "negeri"} else None


def coordinate(text, label, limit):
    match = re.search(rf"{label}\s*:\s*([+-]?\d+(?:[.,]\d+)?)\s*$", text, re.I | re.M)
    if match:
        number = float(match[1].replace(",", "."))
        if -limit <= number <= limit:
            return number
    return None


class SchoolPage(WebPage):
    def _section(self, title):
        return self.xpath(
            '//div[contains(concat(" ", normalize-space(@class), " "), " tabby-tab ")]'
            '[label[normalize-space(.) = $title]]',
            title=title,
        )

    def _rows(self, section):
        rows = {}
        for row in self._section(section).xpath(".//tr"):
            cells = row.xpath("./td | ./th")
            for i, cell in enumerate(cells):
                if cell_text(cell) == ":" and 0 < i < len(cells) - 1:
                    rows[cell_text(cells[i - 1])] = cells[i + 1]
                    break
        return rows

    async def to_item(self):
        identity = self._rows("Identitas Satuan Pendidikan")
        permits = self._rows("Dokumen dan Perijinan")
        contact = self._rows("Kontak")

        def value(rows, label):
            return cell_text(rows[label]) if label in rows else None

        website = contact.get("Website")
        href = website.css("a::attr(href)").get() if website is not None else None
        map_text = "\n".join(self._section("Peta").xpath(".//div//text()").getall())

        return {
            "npsn": value(identity, "NPSN"),
            "nama_satuan_pendidikan": value(identity, "Nama"),
            "alamat": value(identity, "Alamat"),
            "kelurahan": value(identity, "Desa/Kelurahan"),
            "status": school_status(value(identity, "Status Sekolah")),
            "bentuk_pendidikan": value(identity, "Bentuk Pendidikan"),
            "jenjang_pendidikan": value(identity, "Jenjang Pendidikan"),
            "kementerian_pembina": value(permits, "Kementerian Pembina"),
            "website": clean(href) or value(contact, "Website"),
            "operator": value(contact, "Operator"),
            "latitude": coordinate(map_text, "Lintang", 90),
            "longitude": coordinate(map_text, "Bujur", 180),
        }
