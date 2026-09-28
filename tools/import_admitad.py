import json
import sys
import xml.etree.ElementTree as ET


def text(element, path, default=None):
    node = element.find(path)
    if node is None or node.text is None:
        return default
    return node.text.strip()


def parse_offer(offer):
    offer_id = (offer.get("id") or "").strip()
    title = text(offer, "name", "").strip()
    affiliate_url = text(offer, "url")

    if not offer_id or not title or not affiliate_url:
        return None

    discount = None

    for param in offer.findall("param"):
        if param.get("name") == "discount":
            value = (param.text or "").strip().replace("%", "")
            try:
                discount = float(value)
            except ValueError:
                discount = None

    return {
        "id": offer.get("id"),
        "title_en": text(offer, "name", ""),
        "store": "AliExpress",
        "category": text(offer, "categoryId", ""),
        "country": "GLOBAL",
        "price": float(text(offer, "price", "0")),
        "currency": text(offer, "currencyId", ""),
        "discount": discount,
        "image": text(offer, "picture"),
        "description_ar": "",
        "product_url": None,
        "affiliate_url": text(offer, "url"),
        "verified_at": None,
        "status": "draft",
    }


def main():
    count = 0
    products = []

    for event, element in ET.iterparse(sys.stdin, events=("end",)):
        if element.tag == "offer":
            product = parse_offer(element)
            element.clear()

            if product is not None:
                products.append(product)
                count += 1

            if count >= 100:
                break

    print(json.dumps(products, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
