# Avatar Media Sync

`message` 툴 첨부는 기본적으로 `~/.openclaw/media` 하위만 허용된다.

아바타 원본(`workspace/avatars/*.png`)을 첨부 가능한 경로로 복사할 때 아래 스크립트를 사용:

```bash
python3 utility/common/avatar_media_sync.py
```

기본 동작:
- 원본: `/home/user/.openclaw/workspace/avatars/taeyul.png`
- 대상: `/home/user/.openclaw/media/avatars/`
- `taeyul.png` (캐노니컬) 갱신
- 타임스탬프 스냅샷 1개 추가 생성

옵션 예시:

```bash
python3 utility/common/avatar_media_sync.py \
  --src /home/user/.openclaw/workspace/avatars/taeyul.png \
  --canonical-name taeyul.png \
  --topic taeyul_avatar
```

타임스탬프 복사 생략:

```bash
python3 utility/common/avatar_media_sync.py --no-timestamp-copy
```
