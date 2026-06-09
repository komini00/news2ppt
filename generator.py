"""
기사 (제목, 본문) → GPT-4o → 10장 강의 슬라이드 JSON.
각 슬라이드: title + points[{head, desc}]  (핵심포인트 + 부연설명)
대상 학과·학년, 교수 강조점(이론/메시지) 반영.
"""
import json
from openai import OpenAI

N_SLIDES = 10

SYSTEM = f"""당신은 대학 교수의 수업 자료를 만드는 전문 교안 디자이너입니다.
주어진 뉴스 기사를 학부생 강의용 슬라이드 정확히 {N_SLIDES}장으로 재구성합니다.

[출력 형식] JSON 객체 하나:
{{"slides":[{{"title":"슬라이드 제목(명사구, 22자 이내)",
            "points":[{{"head":"핵심 한 줄(굵게 표시될 명사구·주장, 28자 이내)",
                       "subs":["세부 불렛(15~38자)","세부 불렛","세부 불렛"]}}]}}, ... 정확히 {N_SLIDES}개]}}

[내용 규칙]
- 본문 슬라이드(2~10번)는 points를 **반드시 2~3개**(1개 금지) 넣는다. 각 point는 head(핵심 주장) + **subs(세부 불렛 2~3개)**.
- 8번(교수 강조)도 반드시 head 2~3개로 구성한다(강조 이론/메시지를 여러 각도로 전개).
- subs는 head를 뒷받침하는 구체 내용(기사의 사실·수치·발언 + 그 전공 관점의 해석)을 담는다. 한 단어 금지, 완결된 짧은 문장/구.
- 기사에 없는 사실(수치·고유명사)을 지어내지 말 것. 단, 전공 이론으로의 '해석·연결'은 "관점"으로서 허용한다.
- 한국어. 학년 수준에 맞는 난이도.

[10장 구조 — 순서 고정] (본문은 head 2~3개 × subs 2~3개)
1. 표지        : title=기사 핵심 제목. points 1개(head=한 줄 요지, subs=[]).
2. 핵심 요약    : 기사 전체를 head 2~3개로 요약.
3. 배경·맥락    : 왜 이 일이 나왔나(배경·이전 흐름).
4. 핵심 내용①   : 기사의 주요 사실(누가·무엇을·어떻게).
5. 핵심 내용②   : 이어지는 세부·발언·구체 내용.
6. 핵심 데이터·쟁점 : 수치·통계와 논란/쟁점.
7. 전공으로 보기 : **대상 학과의 이론·개념으로 기사 해석**. head=개념/이론명, subs=기사와의 연결.
8. 교수 강조 포인트 : **교수 강조점(아래 입력) 중심**. 이론이면 그 이론으로 기사 설명, 메시지면 전개. 없으면 전공 심화.
9. 수업 토론 질문 : **반드시 질문 3개**(각각 별도 point). head=학생에게 던지는 열린 질문(전공·강조점 연결, '?'로 끝). subs=답을 이끄는 보조 힌트 1개.
10. 정리·시사점  : **반드시 head 2~3개**. head=핵심 takeaway, subs=짧은 설명 1~2개.

반드시 정확히 {N_SLIDES}개의 슬라이드."""


def generate_slides(title: str, body: str, model: str = "gpt-4o",
                    api_key: str | None = None,
                    dept: str = "", grade: str = "", emphasis: str = "") -> list[dict]:
    client = OpenAI(api_key=api_key, max_retries=5, timeout=90) if api_key else OpenAI(max_retries=5, timeout=90)
    audience = " ".join(x for x in [dept.strip(), grade.strip()] if x) or "일반 학부생"
    emph = emphasis.strip()

    user = (f"[수업 대상] {audience}\n"
            f"[교수자가 강조하고 싶은 부분] {emph or '(지정 없음 — 전공 심화·시사점으로 대체)'}\n\n"
            f"[기사 제목]\n{title}\n\n[기사 본문]\n{body}\n\n"
            f"위 기사를 '{audience}' 대상 강의 슬라이드 {N_SLIDES}장으로 만들어 JSON으로 출력하세요. "
            f"7번(전공으로 보기)은 '{audience}'의 전공 이론·개념으로 기사를 해석하고, "
            f"8번(교수 강조 포인트)과 9번(토론 질문)에는 강조점을 명시적으로 반영하세요. "
            f"각 point는 head(핵심)와 subs(세부 불렛 2~3개)를 채우세요.")

    last_err = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": user},
                ],
                temperature=0.5,
                max_tokens=3500,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            # 연결·타임아웃·rate limit 등 — 재시도
            last_err = e
            continue
        raw = resp.choices[0].message.content.strip()
        try:
            data = json.loads(raw)
            slides = data.get("slides", [])
        except json.JSONDecodeError as e:
            last_err = e
            continue

        slides = [s for s in slides if isinstance(s, dict) and s.get("title")]
        if len(slides) > N_SLIDES:
            slides = slides[:N_SLIDES]
        elif len(slides) < N_SLIDES:
            if attempt < 2:
                user += f"\n\n(직전 응답이 {len(slides)}장이었습니다. 반드시 정확히 {N_SLIDES}장으로 다시 출력하세요.)"
                continue
            while len(slides) < N_SLIDES:
                slides.append({"title": "추가 내용", "points": [{"head": "내용 보강 필요", "desc": ""}]})

        # points 정리 → {head, subs:[...]}
        for s in slides:
            pts = s.get("points") or []
            norm = []
            for p in pts:
                if isinstance(p, str):
                    norm.append({"head": p.strip(), "subs": []})
                    continue
                if not isinstance(p, dict):
                    continue
                h = str(p.get("head", "")).strip()
                subs = p.get("subs")
                if subs is None:
                    # 구버전 desc 호환
                    d = str(p.get("desc", "")).strip()
                    subs = [d] if d else []
                if isinstance(subs, str):
                    subs = [subs]
                subs = [str(x).strip() for x in subs if str(x).strip()][:3]
                if h or subs:
                    norm.append({"head": h or subs[0], "subs": subs if h else subs[1:]})
            s["points"] = norm[:3] or [{"head": "(내용 없음)", "subs": []}]
            s.pop("bullets", None)
        return slides

    raise RuntimeError(f"슬라이드 생성 실패: {last_err}")
