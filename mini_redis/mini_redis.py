# [파일 역할] 해시맵 + 이중 연결 리스트(LRU) + 최소 힙(TTL)을 결합한
#            Mini Redis 코어 엔진. 명령어 10개와 메모리/LRU/TTL 정책을 담당한다.

import math
import time
from doubly_linked_list import DoublyLinkedList
from hash_map import HashMap
from min_heap import MinHeap


class Record:
    """해시맵에 저장되는 키의 실제 값과 메타데이터(LRU 노드 참조, 만료 시각)를 묶는 객체."""

    def __init__(self, value, lru_node, expire_at=None):
        self.value = value
        self.lru_node = lru_node
        self.expire_at = expire_at


class MiniRedis:
    """해시맵, 이중 연결 리스트(LRU), 최소 힙(TTL)을 결합한 Mini Redis 코어 엔진."""

    def __init__(self):
        self.store = HashMap()
        self.lru_list = DoublyLinkedList()
        self.ttl_heap = MinHeap()

        self.maxmemory = 0  # 0은 무제한을 의미
        self.used_memory = 0
        self.evicted_keys = 0

    def _calc_entry_bytes(self, key, value):
        """UTF-8 인코딩 기준 키와 값의 바이트 합을 계산합니다."""
        return len(key.encode("utf-8")) + len(value.encode("utf-8"))

    def _delete_internal(self, key):
        """저장소, LRU 리스트, 메모리 사용량에서 키를 완전히 제거합니다."""
        record = self.store.get(key)
        if record is None:
            return False

        self.used_memory -= self._calc_entry_bytes(key, record.value)
        self.lru_list.remove_node(record.lru_node)
        self.store.remove(key)
        return True

    def _cleanup_expired_heap(self):
        """최소 힙의 루트부터 확인하여 만료되었거나 무효화된(Stale) 항목을 정리합니다."""
        now = time.time()
        while self.ttl_heap.size() > 0:
            expire_at, key = self.ttl_heap.peek()
            record = self.store.get(key)

            # 이미 삭제되었거나 TTL이 갱신/초기화된 낡은(Stale) 항목 제거
            if record is None or record.expire_at != expire_at:
                self.ttl_heap.pop()
                continue

            # 만료 시각이 경과한 항목 제거
            if expire_at <= now:
                self.ttl_heap.pop()
                self._delete_internal(key)
            else:
                break

    def _check_and_expire_key(self, key):
        """단일 키 명령 실행 전 만료 여부를 확인하고 만료 시 즉시 삭제합니다."""
        record = self.store.get(key)
        if record is None:
            return False

        if record.expire_at is not None and record.expire_at <= time.time():
            self._delete_internal(key)
            return True
        return False

    def set(self, key, value):
        """SET key value: 값을 저장하고 필요 시 LRU 퇴거를 수행합니다."""
        self._check_and_expire_key(key)
        new_bytes = self._calc_entry_bytes(key, value)

        # 단일 엔트리가 maxmemory를 초과하면 저장하지 않고 OOM 에러 반환
        if self.maxmemory > 0 and new_bytes > self.maxmemory:
            return "(error) OOM command not allowed when used_memory > 'maxmemory'"

        existing_record = self.store.get(key)
        old_bytes = (
            self._calc_entry_bytes(key, existing_record.value)
            if existing_record is not None
            else 0
        )

        projected_memory = self.used_memory - old_bytes + new_bytes

        # maxmemory 초과 시 가장 오래된(LRU tail 쪽) 키부터 순차 제거
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
                    self.evicted_keys += 1

        if existing_record is not None:
            # 기존 키 덮어쓰기: 값 갱신, 기존 TTL 초기화, LRU 최상단 이동
            self.used_memory = self.used_memory - old_bytes + new_bytes
            existing_record.value = value
            existing_record.expire_at = None
            self.lru_list.move_to_front(existing_record.lru_node)
        else:
            # 신규 키 삽입
            lru_node = self.lru_list.insert_front(key)
            new_record = Record(value=value, lru_node=lru_node, expire_at=None)
            self.store.put(key, new_record)
            self.used_memory += new_bytes

        return "OK"

    def get(self, key):
        """GET key: 만료 확인 후 값을 반환하고, 성공 시에만 LRU를 갱신합니다."""
        self._check_and_expire_key(key)
        record = self.store.get(key)
        if record is None:
            return "(nil)"

        self.lru_list.move_to_front(record.lru_node)
        return f'"{record.value}"'

    def delete(self, key):
        """DEL key: 키를 삭제하고 성공 시 1, 없으면 0을 반환합니다."""
        self._check_and_expire_key(key)
        if self._delete_internal(key):
            return "(integer) 1"
        return "(integer) 0"

    def exists(self, key):
        """EXISTS key: 키가 존재하면 1, 없으면 0을 반환합니다."""
        self._check_and_expire_key(key)
        if self.store.contains(key):
            return "(integer) 1"
        return "(integer) 0"

    def dbsize(self):
        """DBSIZE: 만료 키 정리 후 현재 유효한 전체 키 개수를 반환합니다."""
        self._cleanup_expired_heap()
        return f"(integer) {self.store.size()}"

    def keys(self):
        """KEYS: 만료 키 정리 후 전체 키 목록을 Redis 출력 형식으로 반환합니다."""
        self._cleanup_expired_heap()
        all_keys = self.store.keys()
        if not all_keys:
            return "(empty array)"

        lines = []
        for idx, k in enumerate(all_keys, start=1):
            lines.append(f'{idx}. "{k}"')
        return "\n".join(lines)

    def config_set_maxmemory(self, bytes_str):
        """CONFIG SET maxmemory <bytes>: 최대 메모리 제한을 설정합니다."""
        try:
            val = int(bytes_str)
            if val < 0:
                return "(error) ERR value is not an integer or out of range"
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        self.maxmemory = val
        return "OK"

    def info_memory(self):
        """INFO memory: 현재 메모리 사용량, 제한, 누적 퇴거 키 수를 반환합니다."""
        self._cleanup_expired_heap()
        return (
            f"used_memory:{self.used_memory}\n"
            f"maxmemory:{self.maxmemory}\n"
            f"evicted_keys:{self.evicted_keys}"
        )

    def expire(self, key, seconds_str):
        """EXPIRE key seconds: 키의 만료 시간을 초 단위로 설정합니다."""
        self._check_and_expire_key(key)

        try:
            seconds = int(seconds_str)
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        record = self.store.get(key)
        if record is None:
            return "(integer) 0"

        if seconds <= 0:
            self._delete_internal(key)
            return "(integer) 1"

        expire_at = time.time() + seconds
        record.expire_at = expire_at
        self.ttl_heap.push((expire_at, key))
        return "(integer) 1"

    def ttl(self, key):
        """TTL key: 키의 남은 만료 시간을 반환합니다 (-2: 없음, -1: 만료 없음)."""
        self._check_and_expire_key(key)
        record = self.store.get(key)

        if record is None:
            return "(integer) -2"
        if record.expire_at is None:
            return "(integer) -1"

        remaining = math.ceil(record.expire_at - time.time())
        if remaining <= 0:
            self._delete_internal(key)
            return "(integer) -2"
        return f"(integer) {remaining}"
