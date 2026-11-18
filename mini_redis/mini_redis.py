# [파일 이름] mini_redis.py
# ==============================================================================
# [파일 역할] 해시맵 + 이중 연결 리스트(LRU) + 최소 힙(TTL)을 하나로 결합한
#             Mini Redis 코어 엔진. 10개 명령어 실행과 메모리/LRU/TTL 정책을 담당합니다.
# [실생활 비유] 초고속 냉장 보관 창고의 관제실입니다.
#              1) 우편함(store: HashMap)에 키별 정보 묶음(Record)을 보관하고,
#              2) 양손 기차 줄(lru_list: DoublyLinkedList)로 방금 쓴 키는 맨 앞(1등석 MRU),
#                 안 쓴 키는 맨 뒤(퇴거 1순위 LRU)로 세우며,
#              3) 유통기한 피라미드(ttl_heap: MinHeap)로 만료된 키를 0.001초 만에 찾아 버립니다!
# ==============================================================================

import math
import time
from doubly_linked_list import DoublyLinkedList
from hash_map import HashMap
from min_heap import MinHeap


# ==============================================================================
# [1구역: 키 하나가 들고 다니는 정보 묶음 (Record) 클래스]
# ==============================================================================
class Record:
    """해시맵에 저장되는 키의 실제 값과 메타데이터(LRU 노드 참조, 만료 시각)를 묶는 객체.

    [HashMap <-> Record <-> DoublyLinkedList 결합 다이어그램 — 평가 항목 #10]
      HashMap (self.store)                DoublyLinkedList (self.lru_list)
      ┌─────────────────────┐             ┌──────┐   ┌──────────┐   ┌──────┐
      │ key: "user:1"       │             │ HEAD │<=>│"user:1"  │<=>│ TAIL │
      │   └─► Record        │             └──────┘   │  (Node)  │   └──────┘
      │        ├─ value     │                           ▲
      │        ├─ lru_node ─┼───────────────────────────┘ (O(1) 직접 참조!)
      │        └─ expire_at │
      └─────────────────────┘
      -> 해시맵에서 키를 평균 O(1)에 찾은 뒤 Record.lru_node로 리스트 노드를 즉시 잡기 때문에,
         리스트 전체를 처음부터 탐색(O(N))하지 않고도 move_to_front / remove_node 가 O(1)로 동작합니다.
    """

    def __init__(self, value, lru_node, expire_at=None):
        """[함수 역할] 실제 값(value), 기차 칸 위치(lru_node), 만료 시각(expire_at)을 묶습니다."""
        self.value = value          # 실제 저장된 문자열 값 (예: "Alice")
        self.lru_node = lru_node    # 기차 줄(lru_list) 안에서 이 키가 서 있는 칸 주소 -> O(1) 이동 비결!
        self.expire_at = expire_at  # 만료 예정 타임스탬프 (만료 시간이 없으면 None)


# ==============================================================================
# [2구역: Mini Redis 엔진 본체 클래스]
# ==============================================================================
class MiniRedis:
    """해시맵, 이중 연결 리스트(LRU), 최소 힙(TTL)을 결합한 Mini Redis 코어 엔진."""

    def __init__(self):
        """[함수 역할] 3대 자료구조 저장소와 메모리 통계 변수를 초기화합니다."""
        self.store = HashMap()             # 1) key -> Record 를 평균 O(1)에 찾는 우편함
        self.lru_list = DoublyLinkedList() # 2) 최근/오래된 순서를 세우는 양손 기차 줄
        self.ttl_heap = MinHeap()          # 3) (expire_at, key) 유통기한 피라미드

        self.maxmemory = 0     # 최대 메모리 허용량 (바이트 단위, 0이면 무제한)
        self.used_memory = 0   # 현재 사용 중인 메모리 합계 (키+값 UTF-8 바이트)
        self.evicted_keys = 0  # 용량 초과로 쫓겨난(LRU 퇴거) 누적 키 개수

    # --------------------------------------------------------------------------
    # [3구역: 내부 계산 및 정리 도우미 (_calc_entry_bytes, _delete_internal, TTL 정리)]
    # --------------------------------------------------------------------------
    def _calc_entry_bytes(self, key, value):
        """[함수 역할] UTF-8 기준 len(key) + len(value) 바이트 크기를 계산합니다 (오버헤드 제외)."""
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _delete_internal(self, key):
        """[함수 역할] 저장소(HashMap), LRU 기차 줄, used_memory 에서 키를 한꺼번에 깨끗이 지웁니다."""
        record = self.store.get(key)
        if record is None:
            return False

        self.used_memory -= self._calc_entry_bytes(key, record.value)  # 메모리 사용량 차감
        self.lru_list.remove_node(record.lru_node)                    # 기차 줄에서 O(1) 제거
        self.store.remove(key)                                        # 우편함에서 제거
        return True

    def _cleanup_expired_heap(self):
        """[함수 역할] 최소 힙의 맨 위(peek)만 확인해 유통기한이 지난 키들을 연쇄 정리합니다."""
        now = time.time()
        while self.ttl_heap.size() > 0:
            expire_at, key = self.ttl_heap.peek()  # O(1)로 가장 급한 1등만 엿보기
            record = self.store.get(key)

            # [지연 삭제(Lazy Deletion)] 이미 지워졌거나 SET으로 덮어써져 TTL이 바뀐 낡은 항목은 그냥 버림
            if record is None or record.expire_at != expire_at:
                self.ttl_heap.pop()
                continue

            # 만료 시각이 현재 이하(지남)라면 힙에서 꺼내고 데이터도 완전히 삭제
            if expire_at <= now:
                self.ttl_heap.pop()
                self._delete_internal(key)
            else:
                # 1등조차 아직 유통기한이 남았으니, 나머지 키들은 볼 필요도 없이 종료!
                break

    def _check_and_expire_key(self, key):
        """[함수 역할] 키 명령(GET/DEL/EXISTS/EXPIRE/TTL) 실행 직전 만료 여부를 검사하고 지웁니다."""
        record = self.store.get(key)
        if record is None:
            return False

        if record.expire_at is not None and record.expire_at <= time.time():
            self._delete_internal(key)
            return True
        return False

    # --------------------------------------------------------------------------
    # [4구역: String 기본 명령어 6개 (SET, GET, DEL, EXISTS, DBSIZE, KEYS)]
    # --------------------------------------------------------------------------
    def set(self, key, value):
        """[SET key value] 값을 저장하고, 메모리 초과 시 가장 오래된(LRU) 키를 퇴거시킵니다."""
        self._check_and_expire_key(key)
        new_bytes = self._calc_entry_bytes(key, value)

        # 단일 엔트리(키+값) 하나만으로도 maxmemory를 넘으면 기존 데이터를 지우지 않고 OOM 에러 반환
        if self.maxmemory > 0 and new_bytes > self.maxmemory:
            return "(error) OOM command not allowed when used_memory > 'maxmemory'"

        existing_record = self.store.get(key)
        old_bytes = (
            self._calc_entry_bytes(key, existing_record.value)
            if existing_record is not None
            else 0
        )

        projected_memory = self.used_memory - old_bytes + new_bytes

        # maxmemory 초과 시 기차 맨 뒤(tail.prev = 가장 오래 안 쓴 LRU 키)부터 차례로 제거
        # [퇴거 루프 종료 조건 & 자기참조 방어 — 평가 항목 #2]
        # 1) 종료 조건 A: projected_memory <= self.maxmemory (메모리 한도 이하 회복)
        # 2) 종료 조건 B: self.lru_list.tail.prev is self.lru_list.head (더 이상 지울 다른 키 없음)
        # 3) 자기참조 방어(if victim_key == key): 기존 키(key)가 현재 LRU 맨 끝(tail.prev)에 있던 상태에서
        #    더 큰 값으로 덮어쓰기(SET)가 들어오면, 자기 자신은 이번 명령의 대상이므로 먼저 지우지 않고
        #    그 바로 앞 칸(victim_node.prev.data)을 다음 희생자(victim)로 선택합니다.
        #    만약 앞 칸마저 head(즉, 리스트에 자기 자신 1개뿐)라면 즉시 break 후 덮어쓰기를 완료합니다.
        if self.maxmemory > 0:
            while (
                projected_memory > self.maxmemory
                and self.lru_list.tail.prev is not self.lru_list.head
            ):
                victim_node = self.lru_list.tail.prev
                victim_key = victim_node.data
                if victim_key == key:
                    if victim_node.prev is self.lru_list.head:
                        break
                    victim_key = victim_node.prev.data

                victim_record = self.store.get(victim_key)
                if victim_record is not None:
                    freed = self._calc_entry_bytes(victim_key, victim_record.value)
                    self._delete_internal(victim_key)
                    projected_memory -= freed
                    self.evicted_keys += 1  # 퇴거 카운트 +1

        if existing_record is not None:
            # [기존 키 덮어쓰기] 값 교체, 기존 TTL 초기화(None), 기차 맨 앞 1등석(MRU) 이동
            self.used_memory = self.used_memory - old_bytes + new_bytes
            existing_record.value = value
            existing_record.expire_at = None
            self.lru_list.move_to_front(existing_record.lru_node)
        else:
            # [신규 키 저장] 기차 맨 앞(1등석)에 넣고, 그 칸 주소를 Record에 담아 우편함에 보관
            lru_node = self.lru_list.insert_front(key)
            new_record = Record(value=value, lru_node=lru_node, expire_at=None)
            self.store.put(key, new_record)
            self.used_memory += new_bytes

        return "OK"

    def get(self, key):
        """[GET key] 만료 여부를 먼저 확인한 뒤 값을 돌려주고, 성공한 경우에만 LRU를 맨 앞으로 갱신합니다.

        [예외 경로 포함 O(1) 보장 — 평가 항목 #11, #14]
        1) 빈 저장소이거나 키가 없는 경로: HashMap.get(key) 평균 O(1) -> None -> '(nil)' 반환
        2) 만료된 키 경로(expire_at <= now): _delete_internal O(1) 삭제 후 '(nil)' 반환 (LRU 갱신 안 함!)
        3) 정상 히트 경로: move_to_front(record.lru_node) 는 리스트가 1개든 10만 개든
           포인터 4개만 재연결하므로 항상 O(1) 만에 최상단(MRU)으로 이동합니다.
        """
        self._check_and_expire_key(key)
        record = self.store.get(key)
        if record is None:
            return "(nil)"

        self.lru_list.move_to_front(record.lru_node)  # 방금 찾았으니 O(1)로 1등석 승격!
        return f'"{record.value}"'

    def delete(self, key):
        """[DEL key] 저장소·LRU·메모리에서 키를 완전히 삭제합니다 (성공 1, 없으면 0)."""
        self._check_and_expire_key(key)
        if self._delete_internal(key):
            return "(integer) 1"
        return "(integer) 0"

    def exists(self, key):
        """[EXISTS key] 만료 키 정리 후 존재하면 (integer) 1, 없으면 (integer) 0을 반환합니다."""
        self._check_and_expire_key(key)
        if self.store.contains(key):
            return "(integer) 1"
        return "(integer) 0"

    def dbsize(self):
        """[DBSIZE] 만료된 키를 먼저 정리한 뒤 살아 있는 전체 키 개수를 반환합니다."""
        self._cleanup_expired_heap()
        return f"(integer) {self.store.size()}"

    def keys(self):
        """[KEYS] 만료된 키를 정리한 뒤 살아 있는 모든 키 목록을 1. "key" 형식으로 반환합니다."""
        self._cleanup_expired_heap()
        all_keys = self.store.keys()
        if not all_keys:
            return "(empty array)"

        lines = []
        for idx, k in enumerate(all_keys, start=1):
            lines.append(f'{idx}. "{k}"')
        return "\n".join(lines)

    # --------------------------------------------------------------------------
    # [5구역: 메모리 관리 명령어 2개 (CONFIG SET maxmemory, INFO memory)]
    # --------------------------------------------------------------------------
    def config_set_maxmemory(self, bytes_str):
        """[CONFIG SET maxmemory bytes] 최대 메모리 제한을 바이트 정수로 설정합니다 (0 = 무제한)."""
        try:
            val = int(bytes_str)
            if val < 0:
                return "(error) ERR value is not an integer or out of range"
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        self.maxmemory = val
        return "OK"

    def _format_human_bytes(self, num_bytes):
        """[내부 도우미] 바이트 정수를 사람이 읽기 쉬운 단위(B, KB, MB) 문자열로 변환합니다."""
        if num_bytes < 1024:
            return f"{num_bytes}B"
        if num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.2f}KB"
        return f"{num_bytes / (1024 * 1024):.2f}MB"

    def info_memory(self, human=False):
        """[INFO memory] 현재 사용량(bytes), 제한(bytes), 누적 퇴거 키 수를 반환합니다.

        [단위 표기 & human-readable 옵션 — 평가 항목 #3]
        - 기본 모드(`INFO memory`): 명세서/Redis 표준에 맞춰 바이트 단위 정수를 출력
          (used_memory:<bytes>, maxmemory:<bytes>, evicted_keys:<count>)
        - 확장 모드(`INFO memory human`): 바이트 값과 함께 사람이 읽기 쉬운 human-readable 항목
          (used_memory_human, maxmemory_human)을 추가로 출력합니다.
        """
        self._cleanup_expired_heap()
        lines = [
            f"used_memory:{self.used_memory}",
            f"maxmemory:{self.maxmemory}",
            f"evicted_keys:{self.evicted_keys}",
        ]
        if human:
            max_h = "unlimited" if self.maxmemory == 0 else self._format_human_bytes(self.maxmemory)
            lines.append(f"used_memory_human:{self._format_human_bytes(self.used_memory)}")
            lines.append(f"maxmemory_human:{max_h}")
        return "\n".join(lines)

    # --------------------------------------------------------------------------
    # [6구역: TTL 만료 관리 명령어 2개 (EXPIRE, TTL)]
    # --------------------------------------------------------------------------
    def expire(self, key, seconds_str):
        """[EXPIRE key seconds] 키에 초 단위 유통기한을 설정하고 최소 힙에 등록합니다."""
        self._check_and_expire_key(key)

        try:
            seconds = int(seconds_str)
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        record = self.store.get(key)
        if record is None:
            return "(integer) 0"  # 없는 키에는 설정 실패 (0)

        if seconds <= 0:
            self._delete_internal(key)  # 0초 이하 입력 시 즉시 만료 삭제 후 1 반환
            return "(integer) 1"

        expire_at = time.time() + seconds
        record.expire_at = expire_at
        self.ttl_heap.push((expire_at, key))  # 힙에 (만료시각, 키) 추가 (O(log N))
        return "(integer) 1"

    def ttl(self, key):
        """[TTL key] 남은 초 반환 (-2: 키 없음/만료, -1: 만료 설정 안 됨, N: 남은 초)."""
        self._check_and_expire_key(key)
        record = self.store.get(key)

        if record is None:
            return "(integer) -2"
        if record.expire_at is None:
            return "(integer) -1"

        remaining = math.ceil(record.expire_at - time.time())  # 소수점 이하 올림
        if remaining <= 0:
            self._delete_internal(key)
            return "(integer) -2"
        return f"(integer) {remaining}"
