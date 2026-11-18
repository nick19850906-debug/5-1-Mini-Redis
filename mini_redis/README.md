# 5-1- Mini Redis (CLI 기반 인메모리 Key-Value 저장소)

> 📖 **[메인 페이지에서 실생활 비유 그림 · 애니메이션으로 쉽게 보기](../README.md)**  
> ▶ **[브라우저에서 직접 눌러보는 웹 시뮬레이터 열기 (한글 실시간 통역기 포함)](https://nick19850906-debug.github.io/5-1-Mini-Redis/)**

파이썬의 내장 컬렉션(`dict`, `set`, `collections`)을 전혀 쓰지 않고 **이중 연결 리스트(양손 기차 줄), 해시맵(아파트 우편함), 최소 힙(유통기한 피라미드)** 을 직접 구현해 Redis의 핵심 원리($O(1)$ 조회, LRU 자동 퇴거, TTL 만료 관리, 메모리 제한)를 재현한 프로젝트입니다.

---

## 1. 폴더 구조 & 파일별 역할 (모든 코드에 초보자용 한글 주석 완비!)

```text
mini_redis/
├── doubly_linked_list.py   # [양손 기차 줄] O(1) 삽입/삭제/이동을 지원하는 이중 연결 리스트
├── hash_map.py             # [아파트 우편함] 다항 롤링 해시(소수 31) + 체이닝 + 0.75 초과 2배 증축
├── min_heap.py             # [유통기한 피라미드] (expire_at, key) 중 가장 급한 키를 O(1) 확인(peek)
├── mini_redis.py           # [관제실 코어 엔진] 10개 명령어 처리 + LRU 퇴거 + TTL + 메모리 계산
├── main.py                 # [키오스크 창구] 큰따옴표 지원 입력 파서 + mini-redis> CLI REPL
├── evaluate.py             # [자동 채점기] 동료 평가자가 9가지 핵심 항목을 한 번에 점검하는 스크립트
└── README.md               # 코드 폴더 안내 문서
```

---

## 2. Windows CMD / 터미널 실행 방법 (1단계 `cd` 필수!)

Python 3.8 이상, 별도 라이브러리 설치 불필요.

```bash
# 1단계: mini_redis 폴더로 이동 (필수!)
cd mini_redis

# 2단계: 동료 평가자용 9대 요구사항 자동 점검 (약 1초 대기 포함)
python evaluate.py

# 3단계: 대화형 Mini Redis CLI 실행 (exit 또는 quit 으로 종료)
python main.py
```

---

## 3. 지원 명령어 10종 한눈에 보기

| 구분 | 명령어 | 한 줄 설명 |
| :--- | :--- | :--- |
| String | `SET key value` | 값 저장 & 기차 맨 앞(MRU) 승격 (덮어쓸 땐 **기존 TTL 초기화**) |
| String | `GET key` | 값 조회 (**성공 시에만** MRU 승격, 만료 키는 삭제 후 `(nil)`) |
| String | `DEL key` | 우편함·기차·메모리에서 완전 삭제 (`1` 또는 `0`) |
| String | `EXISTS key` | 존재 여부 (`1` 또는 `0`) |
| String | `DBSIZE` | 만료 키 정리 후 유효한 전체 키 개수 |
| String | `KEYS` | 전체 키 목록 (`1. "key"` 형식, 비어 있으면 `(empty array)`) |
| 메모리 | `CONFIG SET maxmemory bytes` | 최대 메모리 제한 (`0`은 무제한) |
| 메모리 | `INFO memory` | `used_memory`, `maxmemory`, `evicted_keys` 출력 |
| TTL | `EXPIRE key seconds` | 만료 시간(초) 설정 (`0` 이하는 즉시 만료 삭제) |
| TTL | `TTL key` | 남은 초 (`-2` 키 없음/만료됨, `-1` 만료 설정 안 됨) |

---

## 4. 동료 평가자 9대 체크리스트 (`python evaluate.py` 로 원클릭 확인!)

| # | 평가 항목 | 확인 포인트 |
| :-: | :--- | :--- |
| 1 | `dict` / `set` / `collections` 미사용 | 5개 `.py` 전체 AST 검사 통과 |
| 2 | 이중 연결 리스트 6개 메서드 $O(1)$ | [`doubly_linked_list.py`](./doubly_linked_list.py): `insert_front/back`, `remove_front/back/node`, `move_to_front` |
| 3 | 해시맵: 자체 해시 + 체이닝 + 0.75 초과 2배 확장 | [`hash_map.py`](./hash_map.py): `_hash`, `_resize`, `put` |
| 4 | 최소 힙: `push/pop/peek/size`, `_heapify_up/down` | [`min_heap.py`](./min_heap.py) |
| 5 | 명세서 공식 예시 재현 (LRU 퇴거, `INFO memory`) | `maxmemory 30` 후 `user:1` 퇴거, `used_memory:22`, `evicted_keys:1` |
| 6 | `GET` 시 LRU 갱신, 단일 엔트리 `OOM` | `GET` 성공 시에만 최신화, 단일 키+값 > `maxmemory` 시 즉시 `OOM` |
| 7 | TTL: 만료 후 `(nil)`/`-2`, 덮어쓰기 시 초기화 | `EXPIRE`, 대기 후 `GET`/`TTL`, 덮어쓰기 후 `TTL`→`-1` |
| 8 | 에러 표준 출력 4종 & 따옴표 값 파싱 | `GET`(인자 부족), `HELLO`, `CONFIG SET maxmemory abc`, `"hello world"` |
| 9 | 각 자료구조 독립 파일 & 초보자용 주석/Docstring | 5개 모듈 분리 및 `[실생활 비유]`·`[구역]` 한글 주석 완비 |

---

## 5. 과제 목표 4대 핵심 질문 — 쉬운 비유 & 코드 답변

**Q1. 해시맵의 해시 함수와 충돌 해결 방식은?**
- **비유:** 이름의 글자들을 숫자로 바꿔 소수 `31`을 곱하고 칸 수(`16`)로 나눈 나머지로 우편함 번호를 정합니다. 같은 칸에 2개 이상 오면 **이중 연결 리스트에 나란히 매달아 두고(체이닝)**, `75%` 넘게 차면 **우편함을 2배로 늘려 재정리**합니다.
- **코드:** [`hash_map.py`](./hash_map.py)의 `_hash`, `put`, `_resize`.

**Q2. 이중 연결 리스트 + 해시맵으로 $O(1)$ LRU가 되는 이유는?**
- **비유:** 기차 줄만 세우면 손님이 어느 칸에 있는지 찾는 데 $O(N)$이 걸립니다. 그래서 해시맵의 `Record`가 **기차 칸 위치(`lru_node`)를 직접 들고 있도록** 했습니다!
- **코드:** [`mini_redis.py`](./mini_redis.py)의 `Record.lru_node`와 [`doubly_linked_list.py`](./doubly_linked_list.py)의 `move_to_front`, `remove_node`, 양 끝 `head`/`tail` 더미 노드.

**Q3. 최소 힙이 TTL에 적합한 이유는?**
- **비유:** 유통기한이 가장 짧은 우유가 항상 피라미드 맨 꼭대기(`0`번 루트)에 오도록 정렬하므로, 맨 위 1개(`peek`)만 보고도 만료 대상이 있는지 $O(1)$에 확인합니다.
- **코드:** [`min_heap.py`](./min_heap.py)의 `peek/push/pop` 및 [`mini_redis.py`](./mini_redis.py)의 게으른 삭제(`_cleanup_expired_heap`).

**Q4. 메모리 제한 시 LRU 퇴거와 `used_memory` 갱신 흐름은?**
- **비유:** 냉장고 한도(`maxmemory`)를 넘으면 기차 맨 뒤(`tail.prev`)의 가장 오래 안 쓴 키부터 하나씩 지우고, 지운 바이트만큼 `used_memory`를 줄이며 `evicted_keys`를 1씩 올립니다. 단, 새 데이터 1개 자체가 한도보다 크면 기존 데이터를 지키고 즉시 `OOM`을 반환합니다.
- **코드:** [`mini_redis.py`](./mini_redis.py)의 `set` 메서드.
