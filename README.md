# 뉴스 → 강의 PPT 15장 자동생성

뉴스 기사 링크만 넣으면 GPT-4o가 학부생 강의용 슬라이드 **정확히 15장**을 만들어 `.pptx`로 다운로드해 주는 Streamlit 웹앱.

> 교수공개강의(6/9) 청중 실습용. 청중은 **URL 접속 → 기사 링크 붙여넣기 → [생성] → 다운로드**만 하면 됨.

## 구성

| 파일 | 역할 |
|---|---|
| `app.py` | Streamlit UI |
| `extractor.py` | 기사 URL → 제목·본문 (requests + BeautifulSoup) |
| `generator.py` | 본문 → GPT-4o → 15장 슬라이드 JSON |
| `ppt_builder.py` | JSON → `.pptx` (16:9 다크테마) |

## 로컬 실행

```bash
pip install -r requirements.txt
# 키 설정 (둘 중 하나)
#  (A) 환경변수:  set OPENAI_API_KEY=sk-...
#  (B) .streamlit/secrets.toml 에  OPENAI_API_KEY = "sk-..."
streamlit run app.py
```

## Streamlit Community Cloud 배포 (청중 실습용 · 약 5분)

1. **GitHub에 이 폴더를 새 레포로 올린다** (예: `news2ppt`).
   - app.py / extractor.py / generator.py / ppt_builder.py / requirements.txt 포함.
   - `.streamlit/secrets.toml` 은 **올리지 말 것**(키 노출). `.gitignore`에 추가.
2. **share.streamlit.io** 접속 → GitHub(komini00) 로그인 → **New app** → 레포·브랜치·`app.py` 선택.
3. **Advanced settings → Secrets** 에 입력:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. **Deploy** → 1~2분 후 공개 URL 발급 (예: `https://news2ppt.streamlit.app`).
5. 그 URL을 QR로 만들어 청중에게:
   `https://api.qrserver.com/v1/create-qr-code/?size=400x400&data=<URL>`

## 강의 당일 주의

- **무료 티어**라 10명 동시 업로드는 잠깐 느릴 수 있음 → "한 분씩 해보세요" 안내 + 강의 직전 1회 워밍업 호출.
- **비용**: gpt-4o 기준 기사 1건당 수십~수백원. 화면의 **빠른 모드(mini)** 토글을 켜면 더 저렴·빠름. 강의 끝나면 앱 내려서 비용 차단.
- 기사가 로그인/동적 페이지라 안 열리면 → 화면의 **"본문 직접 붙여넣기"** 사용.

## 강의 후 정리

- Streamlit Cloud 대시보드에서 앱 **Delete** 또는 키 회수.
