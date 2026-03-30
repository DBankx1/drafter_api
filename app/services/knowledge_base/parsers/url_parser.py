import httpx
from bs4 import BeautifulSoup

class UrlParser:
    async def parse(self, url: str) -> str:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
            response = await client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        return soup.get_text(separator="\n", strip=True)