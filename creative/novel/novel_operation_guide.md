# 그저 깨어 있기를 바랄 뿐 — 운영 가이드

## 1) 집필 기준 우선순위
1. 세계관/설정: [`novel_story_bible.md`](./novel_story_bible.md)
2. 화별 적용 맵: [`novel_episode_outline_ep1_ep4.md`](./novel_episode_outline_ep1_ep4.md)
3. 연재 전략/공개 순서: [`novel_release_strategy.md`](./novel_release_strategy.md)
4. 점검 이력/수정 로그: [`novel_review_log.md`](./novel_review_log.md)

## 2) 운영 원칙
- 합의된 기준을 누적 확장하는 방식으로 관리
- 설정 변경은 바이블 먼저 갱신
- 회차 수정은 로그에 1:1 단락 대응 포맷으로 기록
- 리라이트는 보수적 치환에 제한되지 않으며, 필요 시 단락 전체 재작성 허용
- 중복 서술 금지: 세계관 키워드는 바이블 단일 기준 참조

## 3) 작성 전 체크
- [ ] 파일명 규칙: `기존파일명_rewrite.md`
- [ ] 분량 목표: 공백 포함 5,000자 이상
- [ ] 금지 문장: `A가 아니라 B` / `not A but B` 패턴 지양
- [ ] 기능 대사 제한: 연속 2문장 이상 금지
- [ ] 공개 강도 선택: 암시 / 반확정 / 확정
- [ ] 변경 구간 **볼드체** 표기 확인

## 4) 작성 중 체크
- [ ] 장면 기능이 적용 맵과 1:1 대응되는지 확인
- [ ] 설정 선설명(용어 먼저 제시) 회피
- [ ] 감각 묘사 → 판단 순서 유지
- [ ] 본문 메타 표현 금지(화수/리라이트 과정/문서 작업 언급 금지)
- [ ] 부분 땜질 금지: 회차 단위 통파일 재작성 우선

## 5) 작성 후 체크
- [ ] `wc -m` 기준 공백 포함 5,000자 이상
- [ ] `A가 아니라 B` 패턴 잔존 여부 검색
- [ ] 파일명/링크 무결성 확인
- [ ] 변경 의도 3줄을 [`novel_review_log.md`](./novel_review_log.md)에 기록
- [ ] 다음 화로 넘길 떡밥 2개 명시

## 6) 연속성 핵심
- EP2 말미 위협 → EP3 즉시 침습
- EP3 전투 후유증 → EP4 양호실 회복/정보 공개
- 반하은 근원 공개는 감정 반응 후 정보 제시 순서 유지

## 7) 빠른 검증 명령
```bash
wc -m creative/novel/stay_awake_ep1_rewrite.md
grep -n "아니라" creative/novel/stay_awake_ep1_rewrite.md
```