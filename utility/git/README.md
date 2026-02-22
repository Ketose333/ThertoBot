# Git Initial Reset Utility

운영 기준: [`AGENTS.md`](../../AGENTS.md)

이니셜 커밋 강제 정리 표준 절차:
1) 현재 변경사항을 패치로 임시 보관
2) [`memory/git-history-archive.md`](../../memory/git-history-archive.md) 갱신
3) orphan 이니셜 커밋 생성 + 원격 강제 푸시
4) 보관한 최신 변경사항을 후속 커밋으로 push

## 실행

```bash
bash /home/user/.openclaw/workspace/utility/git/initial_reset_with_latest.sh
```

옵션:
- `--no-latest` : 후속 커밋 단계 생략(이니셜만 반영)

## 대시보드 기본 실행

- 기본 경로는 대시보드(`studio/dashboard/webui.py`)의 `이니셜 커밋으로 밀기` 액션을 사용한다.
- 대시보드에서는 큐 등록이 아닌 즉시 실행으로 동작한다.

## Gitignore 위생 런타임

```bash
# 런타임 시작(상시)
python3 utility/taeyul/taeyul_cli.py gitignore-hygiene-runtime --poll-sec 10

# 작업 큐 등록(.gitignore에 맞춰 tracked ignored 파일 추적해제)
python3 utility/taeyul/taeyul_cli.py gitignore-hygiene-enqueue --reason "periodic hygiene"
```

파일:
- queue: `memory/runtime/gitignore_hygiene_queue.jsonl`
- runs: `memory/runtime/gitignore_hygiene_runs.jsonl`

## .gitignore 작업 표준(필수)

앞으로 파일 무시 관련 작업은 아래를 한 번에 수행:
1) `.gitignore` 규칙 갱신
2) 이미 추적 중인 대상은 `git rm --cached ...`로 **추적 해제**
3) 커밋/푸시해서 원격에서도 비노출 상태 반영

예시:
```bash
git rm --cached MEMORY.md USER.md memory/*.md memory/channels/*.md
git add .gitignore
git commit -m "chore(gitignore): update ignore rules and untrack sensitive files"
git push
```
