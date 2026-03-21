# PRD: Auth & FE Rendering Refactor

## Problem Statement

현재 CORRYU 프론트엔드는 **10개 이상의 HTML 파일**에 동일한 코드가 복사-붙여넣기(Copy-Paste) 되어 있습니다.  
이로 인해 한 곳에서 버그를 수정해도 다른 페이지에 반영되지 않아 **지속적인 QA 실패**가 발생합니다.

### 중복된 코드 블록 (페이지당 ~60줄씩 × 10페이지 = ~600줄 중복)

| 코드 블록 | 중복 파일 수 |
|---|---|
| `renderAuth()` — 네비바 로그인/닉네임 표시 | 10개 |
| `doLogout()` — 로그아웃 처리 | 10개 |
| `onAuthChange()` — 세션 변경 감지 | 10개 |
| `mobLoginBtn.style.display` — 모바일 로그인 버튼 숨김 | 9개 |
| Navbar HTML (고정 내비게이션) | 10개 |
| Mobile Drawer HTML + JS | 10개 |
| Hamburger Menu event binding | 10개 |

## Goals

1. **Create `nav.js`** — 공유 모듈로 navbar 인증 렌더링, 로그아웃, 모바일 메뉴 전체를 중앙관리
2. **Fix the persistent empty dashboard bug** — `initTrending` null reference 현재도 미해결
3. **Make future AI coding easier** — 단일 파일 수정으로 모든 페이지에 반영

## Success Criteria

- 인증/로그아웃 관련 JS 코드가 **`nav.js` 한 곳에만** 존재
- 각 HTML 파일에서 중복 코드 100% 제거
- 로그인/로그아웃 후 모든 페이지에서 정상 동작 확인
- 대시보드 테이블이 로그인 여부와 관계없이 정상 렌더링
