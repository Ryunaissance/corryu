"""
CORRYU - raw/ parquet 외부 스토리지 동기화 (Supabase Storage)

raw/*.parquet을 git에 매일 커밋하는 대신 Supabase Storage 버킷에 보관한다.
git에는 더 이상 parquet을 커밋하지 않으므로 .git 히스토리가 비대해지지 않는다.

  pull_raw()    : 스토리지 → 로컬 raw/ (항상 최신본으로 덮어씀)
  ensure_raw()  : 로컬에 없을 때만 pull (compute_all 등 재계산 진입점용)
  push_raw()    : 로컬 raw/ → 스토리지 덮어쓰기 (fetch 종료 시)

환경변수:
  SUPABASE_URL          예) https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY  service_role 키 (쓰기 권한 필요)
  RAW_STORAGE_BUCKET    기본 'raw-data'

durability: 원본 유실 방지를 위해 Supabase 버킷의 versioning/백업을 켜두는 것을 권장.
"""
import os
from pathlib import Path

from config import RAW_DIR

RAW_FILES = ['prices_close.parquet', 'meta.parquet']
BUCKET = os.environ.get('RAW_STORAGE_BUCKET', 'raw-data')


def is_configured() -> bool:
    """스토리지 자격증명(env)이 설정되어 있는지 여부"""
    return bool(os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_SERVICE_KEY'))


def _client():
    """설정돼 있으면 supabase 클라이언트, 아니면 None"""
    url = os.environ.get('SUPABASE_URL', '')
    key = os.environ.get('SUPABASE_SERVICE_KEY', '')
    if not url or not key:
        return None
    from supabase import create_client
    return create_client(url, key)


def _local_files_present() -> bool:
    raw_dir = Path(RAW_DIR)
    return all((raw_dir / name).exists() for name in RAW_FILES)


def pull_raw(required: bool = True) -> bool:
    """스토리지의 parquet을 로컬 raw/로 내려받아 덮어쓴다.

    Actions 컨테이너는 매번 새로 clone되므로 보통 로컬에 파일이 없다.
    미설정 시: 로컬 파일이 있으면 그대로 사용하고 경고, 없으면 required에 따라 에러.
    """
    client = _client()
    if client is None:
        if _local_files_present():
            print('  [storage] SUPABASE 미설정 — 로컬 raw/ 파일을 그대로 사용')
            return False
        msg = 'SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정 — raw/ 를 받을 수 없습니다.'
        if required:
            raise RuntimeError(msg)
        print(f'  [storage] {msg} (건너뜀)')
        return False

    raw_dir = Path(RAW_DIR)
    raw_dir.mkdir(parents=True, exist_ok=True)
    ok = True
    for name in RAW_FILES:
        local = raw_dir / name
        try:
            data = client.storage.from_(BUCKET).download(name)
            local.write_bytes(data)
            print(f'  [storage] pull: {name} ({len(data) / 1e6:.1f} MB)')
        except Exception as e:
            ok = False
            if local.exists():
                print(f'  [storage] pull 실패({name}): {e} — 로컬 기존 파일 사용')
            elif required:
                raise RuntimeError(f'스토리지에서 {name} 다운로드 실패: {e}')
            else:
                print(f'  [storage] pull 실패({name}): {e}')
    return ok


def ensure_raw(required: bool = True) -> bool:
    """로컬에 parquet이 모두 있으면 그대로 두고, 없으면 pull.

    daily 파이프라인에서 fetch_daily가 이미 받아둔 로컬 파일을 재사용하기 위함.
    """
    if _local_files_present():
        return True
    return pull_raw(required=required)


def push_raw(required: bool = True) -> bool:
    """로컬 raw/ parquet을 스토리지에 업로드(덮어쓰기)한다."""
    client = _client()
    if client is None:
        msg = 'SUPABASE_URL / SUPABASE_SERVICE_KEY 미설정 — 스토리지 업로드 불가'
        if required:
            raise RuntimeError(msg)
        print(f'  [storage] {msg} (생략)')
        return False

    raw_dir = Path(RAW_DIR)
    for name in RAW_FILES:
        path = raw_dir / name
        if not path.exists():
            print(f'  [storage] push 건너뜀(로컬 없음): {name}')
            continue
        data = path.read_bytes()
        client.storage.from_(BUCKET).upload(
            name, data,
            {'content-type': 'application/octet-stream', 'upsert': 'true'},
        )
        print(f'  [storage] push: {name} ({len(data) / 1e6:.1f} MB)')
    return True
