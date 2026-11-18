# 5-1- Mini Redis (CLI 기반 인메모리 Key-Value 저장소)

> 📊 **[메인 인포그래픽·애니메이션 README 보기](../README.md)** &nbsp;|&nbsp; **▶ [인터랙티브 HTML 데모 열기](https://nick19850906-debug.github.io/5-1-Mini-Redis/)**

파이썬의 내장 컬렉션(`dict`, `set`, `collections`)을 쓰지 않고 **이중 연결 리스트, 해시맵, 최소 힙**을 직접 구현해 Redis의 핵심 원리(O(1) 조회, LRU 캐시 교체, TTL 만료 관리, 메모리 제한)를 재현한 프로젝트입니다.

---

## 1. 디렉토리 구조

```text
mini_redis/
├── doubly_linked_list.py   # O(1) 삽입/삭제/이동을 지원하는 이중 연결 리스트
├── hash_map.py             # 다항식 롤링 해시 + 체이닝 기반 해시맵
├── min_heap.py             # TTL 만료 시간 관리를 위한 배열 기반 최소 힙
├── mini_redis.py           # 자료구조 통합 + 명령어/LRU/TTL/메모리 정책 코어 엔진
├── main.py                 # CLI REPL 인터페이스 및 명령어 파서
├── evaluate.py             # 동료 평가자용 자동 점검 스크립트
└── README.md               # 프로젝트 문서
```

## 2. 실행 방법

Python 3.8 이상, 외부 라이브러리 설치 불필요.

```bash
cd mini_redis
python main.py        # CLI 실행 (exit 또는 quit 으로 종료)
python evaluate.py    # 자동 점검 (약 1초 대기 포함)
```

## 3. 지원 명령어

| 구분 | 명령어 | 설명 |
| :--- | :--- | :--- |
| String | `SET key value` | 값 저장, LRU 갱신. 덮어쓰면 기존 TTL 초기화 |
| String | `GET key` | 값 조회. 성공 시에만 LRU 갱신, 만료 키는 삭제 후 `(nil)` |
| String | `DEL key` | 저장소/LRU/메모리에서 완전 삭제 (`1` 또는 `0`) |
| String | `EXISTS key` | 존재 여부 (`1` 또는 `0`) |
| String | `DBSIZE` | 유효한 전체 키 개수 |
| String | `KEYS` | 전체 키 목록 (패턴 매칭 없음) |
| 메모리 | `CONFIG SET maxmemory bytes` | 최대 메모리 설정 (0은 무제한) |
| 메모리 | `INFO memory` | `used_memory`, `maxmemory`, `evicted_keys` 출력 |
| TTL | `EXPIRE key seconds` | 만료 시간 설정 (0 이하는 즉시 만료) |
| TTL | `TTL key` | 남은 초 (`-2` 키 없음, `-1` 만료 없음) |

## 4. 동료 평가자 체크리스트

`python evaluate.py` 한 번으로 아래 항목이 자동 점검됩니다. 직접 확인하고 싶다면 오른쪽 방법을 따르세요.

| # | 평가 항목 | 직접 확인 방법 |
| :-: | :--- | :--- |
| 1 | `dict`/`set`/`collections` 미사용 | 5개 `.py` 파일에서 해당 키워드 검색 |
| 2 | 이중 연결 리스트 6개 메서드 (O(1)) | `doubly_linked_list.py` 의 `insert_front/back`, `remove_front/back/node`, `move_to_front` |
| 3 | 해시맵: 자체 해시 함수 + 체이닝 + 0.75 초과 시 2배 확장 | `hash_map.py` 의 `_hash`, `_resize`, `put` |
| 4 | 최소 힙: `push/pop/peek/size`, `_heapify_up/down` | `min_heap.py` |
| 5 | 명세서 예시 재현 (LRU 제거, `INFO memory`) | 아래 "데모 시나리오" 실행 |
| 6 | GET 시 LRU 갱신, 단일 엔트리 OOM | `maxmemory 30` 설정 후 큰 값 `SET` |
| 7 | TTL: 만료 후 `(nil)`/`-2`, 덮어쓰기 시 TTL 초기화 | `EXPIRE`, `TTL` 실행 후 대기 |
| 8 | 에러 표준 출력 4종 | `GET`(인자 없음), `HELLO`, `CONFIG SET maxmemory abc` |
| 9 | 각 자료구조가 독립 파일, docstring 작성 | 파일 구조 확인 |

### 데모 시나리오

```text
mini-redis> CONFIG SET maxmemory 30
OK
mini-redis> SET user:1 "Alice"
OK
mini-redis> SET user:2 "Bob"
OK
mini-redis> SET user:3 "Charlie"
OK
mini-redis> GET user:1
(nil)
mini-redis> INFO memory
used_memory:22
maxmemory:30
evicted_keys:1
mini-redis> KEYS
1. "user:2"
2. "user:3"
mini-redis> EXPIRE user:2 3
(integer) 1
mini-redis> TTL user:2
(integer) 3
```

> `TTL` 은 남은 시간을 올림(`ceil`)해서 반환하므로 직후에는 `3` 이 나옵니다. 명세서 예시의 `2` 는 "참고용 예시"입니다.

## 5. 핵심 원리 Q&A

**Q1. 해시 함수와 충돌 해결은?**
`hash_map.py` 의 `_hash` 는 각 문자의 `ord` 에 소수 31을 곱해 누적하고 버킷 크기로 나머지를 구하는 다항식 롤링 해시입니다. 같은 버킷에 걸리면 직접 만든 `DoublyLinkedList` 에 이어 붙이는 체이닝으로 해결합니다. `(size+1)/capacity` 가 0.75를 넘으면 버킷을 2배로 늘리고 전부 재해싱합니다(`_resize`).

**Q2. 이중 연결 리스트 + 해시맵으로 O(1) LRU가 되는 이유는?**
리스트만 쓰면 키 위치를 찾는 데 O(N)이 듭니다. 그래서 해시맵의 `Record` 가 리스트 노드(`lru_node`)를 직접 들고 있습니다. `GET`/`SET` 시 해시맵으로 노드를 O(1)에 찾고, `move_to_front` 로 앞뒤 포인터만 바꿔 맨 앞으로 옮깁니다. 퇴거 대상은 항상 `tail.prev` 이므로 O(1)입니다. 양 끝 더미(sentinel) 노드 덕에 빈 리스트나 끝 노드도 같은 코드로 처리됩니다.

**Q3. 최소 힙이 TTL에 적합한 이유는?**
루트에 가장 빨리 만료될 `(expire_at, key)` 가 있어 `peek` 한 번(O(1))으로 만료 대상 유무를 알 수 있고, `push`/`pop` 은 O(log N)입니다. `DEL` 이나 덮어쓰기로 무효가 된 항목은 힙에서 찾아 지우지 않고, 루트에서 꺼낼 때 실제 `Record.expire_at` 과 대조해 버리는 지연 삭제(lazy deletion)를 씁니다.

**Q4. 메모리 제한 시 LRU 퇴거와 `used_memory` 갱신 흐름은?**
`used_memory` 는 엔트리 추가/삭제 때마다 `len(utf8(key)) + len(utf8(value))` 만큼 증감합니다. `SET` 에서 예상 메모리가 `maxmemory` 를 넘으면 `tail.prev` 의 가장 오래된 키부터 하나씩 지우고 `evicted_keys` 를 1씩 올립니다. 단일 엔트리 자체가 `maxmemory` 보다 크면 기존 데이터를 지우지 않고 바로 OOM 에러를 반환합니다.
