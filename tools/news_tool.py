import feedparser

FEEDS = {
    "Receita Federal — Tributação": "https://www.gov.br/receitafederal/pt-br/assuntos/noticias/tributacao-2/tributacao-coletanea/RSS",
    "Portal Gov.br — Geral": "https://www.gov.br/pt-br/rss",
}

def get_news(max_items: int = 5):
    out = []
    for nome, url in FEEDS.items():
        try:
            fp = feedparser.parse(url)
            for e in fp.entries[:max_items]:
                out.append({
                    "fonte": nome,
                    "titulo": e.get('title'),
                    "link": e.get('link')
                })
        except Exception:
            continue
    return out
