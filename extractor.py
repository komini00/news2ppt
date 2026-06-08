"""
뉴스 기사 URL → (제목, 본문 텍스트) 추출.
requests + BeautifulSoup. 한국 언론사 흔한 셀렉터 우선, 폴백으로 <p> 모음.
외부 의존: requests, beautifulsoup4, lxml
"""
import re
import requests
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 한국 언론사/포털에서 본문이 담기는 흔한 컨테이너들 (우선순위 순)
BODY_SELECTORS = [
    "article",
    "#dic_area",            # 네이버 뉴스
    "#articleBodyContents", # 구 네이버
    "#newsct_article",      # 네이버 모바일
    "#article-view-content-div",
    "#articleBody", ".article-body", ".article_body",
    "#newsEndContents", "#news_body_area", ".news_body",
    "#contents", ".content", ".cont_view",
    "[itemprop=articleBody]",
]

# 본문에서 걷어낼 잡음 태그
STRIP_TAGS = ["script", "style", "noscript", "iframe", "figure",
              "figcaption", "aside", "nav", "header", "footer", "form"]


class ExtractError(Exception):
    pass


def _clean(text: str) -> str:
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    # 기자 이메일/저작권 흔한 꼬리 제거
    text = re.sub(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "", text)
    return text.strip()


def fetch_html(url: str) -> str:
    if not re.match(r"^https?://", url.strip(), re.I):
        raise ExtractError("올바른 URL이 아닙니다 (http/https로 시작해야 합니다).")
    try:
        r = requests.get(url.strip(), headers={"User-Agent": UA},
                         timeout=12, allow_redirects=True)
        r.raise_for_status()
    except requests.RequestException as e:
        raise ExtractError(f"기사를 불러오지 못했습니다: {e}")
    # 인코딩 보정
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text


def extract_article(url: str) -> tuple[str, str]:
    """URL → (title, body_text). 실패 시 ExtractError."""
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # 제목: og:title > <title> > <h1>
    title = ""
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        title = og["content"].strip()
    if not title and soup.title:
        title = soup.title.get_text(strip=True)
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "제목 없음"

    # 본문: 셀렉터 우선 탐색
    body_node = None
    for sel in BODY_SELECTORS:
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            body_node = node
            break

    if body_node is not None:
        for t in body_node.find_all(STRIP_TAGS):
            t.decompose()
        body = body_node.get_text("\n", strip=True)
    else:
        # 폴백: 페이지 전체에서 긴 <p> 들을 모음
        for t in soup.find_all(STRIP_TAGS):
            t.decompose()
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        paras = [p for p in paras if len(p) > 40]
        body = "\n".join(paras)

    body = _clean(body)
    if len(body) < 200:
        raise ExtractError(
            "본문을 충분히 추출하지 못했습니다. 로그인이 필요하거나 동적 페이지일 수 있어요. "
            "아래 '본문 직접 붙여넣기'를 이용해 주세요."
        )
    # 너무 길면 자르기 (토큰 절약)
    return title, body[:8000]
