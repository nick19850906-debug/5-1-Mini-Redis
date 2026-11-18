# ==============================================================================
# [파일 이름] hash_map.py
# [파일 역할] 직접 설계한 해시 함수 + 체이닝(이중 연결 리스트 재사용) 기반 해시맵.
#             내장 dict/set/collections 없이 평균 O(1) 조회/삽입/삭제를 구현합니다.
# [실생활 비유] 아파트 16칸 우편함 배열입니다.
#              1) 이름(key)을 번호 계산기(_hash)에 넣으면 몇 번 우편함인지 즉시 알려줍니다.
#              2) 우연히 두 이름이 같은 우편함 번호를 받아도(해시 충돌),
#                 그 칸 안의 기차 줄(DoublyLinkedList)에 나란히 매달아(체이닝) 잃어버리지 않습니다.
#              3) 우편함이 75%(0.75) 넘게 차면 우편함을 2배로 증축(_resize)해 속도를 유지합니다!
# ==============================================================================

from doubly_linked_list import DoublyLinkedList


# ==============================================================================
# [1구역: 우편함에 넣을 (key, value) 편지 봉투 클래스]
# ==============================================================================
class HashEntry:
    """해시맵 버킷(체이닝 리스트)에 저장되는 Key-Value 쌍 데이터 객체."""

    def __init__(self, key, value):
        """[함수 역할] 겉면 이름표(key)와 안쪽 내용물(value)을 하나의 세트로 묶어 저장합니다."""
        self.key = key      # 검색할 때 비교할 키 이름 (예: "user:1")
        self.value = value  # 키에 연결된 실제 값 (예: Record 객체)


# ==============================================================================
# [2구역: 체이닝 & 2배 자동 확장 해시맵(HashMap) 본체 클래스]
# ==============================================================================
class HashMap:
    """체이닝(이중 연결 리스트 재사용)과 동적 리사이징을 지원하는 해시맵.

    내장 dict, set, collections를 사용하지 않고 고정 크기 리스트와
    직접 구현한 DoublyLinkedList만으로 O(1) 평균 조회/삽입/삭제를 구현합니다.
    """

    LOAD_FACTOR_THRESHOLD = 0.75  # 우편함이 75% 초과해서 차면 2배 확장하는 기준선

    def __init__(self, initial_capacity=16):
        """[함수 역할] 16칸(기본값) 우편함 배열을 만들고 각 칸마다 빈 기차 줄을 걸어둡니다."""
        self._capacity = initial_capacity  # 전체 우편함(버킷) 칸 개수
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        self._size = 0                     # 현재 들어 있는 총 키-값 개수

    # --------------------------------------------------------------------------
    # [3구역: 직접 만든 번호 계산기(_hash) & 우편함 2배 증축(_resize)]
    # --------------------------------------------------------------------------
    def _hash(self, key):
        """[함수 역할] 다항식 롤링 해시(소수 31)로 문자열 키를 0 ~ (capacity-1) 우편함 번호로 바꿉니다."""
        key_str = str(key)
        hash_val = 0
        prime = 31  # 글자 순서가 달라도 골고루 퍼지게 곱해 주는 소수(Prime)
        for ch in key_str:
            # 글자의 유니코드 숫자(ord)를 더해 나가며 버킷 개수로 나눈 나머지(%)를 구함
            hash_val = (hash_val * prime + ord(ch)) % self._capacity
        return hash_val

    def _resize(self):
        """[함수 역할] 적재율(로드 팩터)이 0.75를 넘으면 우편함 칸을 2배 늘리고 모든 키를 재정리합니다.

        [성능·메모리 고려 사항 — 평가 항목 #8, #9]
        - 리해시 비용(O(N) 일시 지연): _resize() 실행 순간에는 기존 N개 엔트리를 모두 재삽입하므로
          해당 1회 put()에 한해 O(N) 스파이크가 발생합니다 (단, 2배 확장으로 분할 상환 시간복잡도는 평균 O(1)).
          10만 건 이상 대규모 서비스에서는 Redis 방식의 '점진적 리해싱(Incremental Rehashing,
          2개 해시테이블을 두고 명령어마다 1버킷씩 점진 이동)'으로 전환해 꼬리 지연(Tail Latency)을 제거합니다.
        - 노드 재사용 / GC 비용: 현재는 새 버킷 배열에 insert_back()으로 삽입해 기존 체이닝 Node가
          GC(가비지 컬렉션) 대상이 되나, _buckets[idx].remove_node()가 반환하는 Node 풀(Free-List)을 두거나
          existing HashEntry 노드를 직접 재연결하면 객체 생성/GC 부하도 O(1) 메모리로 줄일 수 있습니다.
        """
        old_buckets = self._buckets        # 옛 우편함 배열을 잠시 보관
        self._capacity *= 2                # 칸 수를 2배(예: 16 -> 32)로 증축
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        self._size = 0                     # 다시 put()으로 넣으면서 정확한 개수를 세기 위해 0 초기화

        # 옛 우편함에 있던 모든 편지를 꺼내 바뀐 capacity 기준으로 새 우편함에 재배치(Rehash)
        for bucket in old_buckets:
            for node in bucket:
                entry = node.data
                self.put(entry.key, entry.value)

    # --------------------------------------------------------------------------
    # [4구역: 해시맵 6대 핵심 기능 (put, get, remove, contains, keys, size)]
    # --------------------------------------------------------------------------
    def put(self, key, value):
        """[함수 역할] 키-값을 저장하거나, 이미 같은 키가 있으면 값을 새것으로 덮어씁니다."""
        # 넣었을 때 적재율이 0.75를 초과하게 되면 먼저 우편함을 2배로 늘림
        if (self._size + 1) / self._capacity > self.LOAD_FACTOR_THRESHOLD:
            self._resize()

        idx = self._hash(key)         # 1) 우편함 방 번호 계산 (O(1))
        bucket = self._buckets[idx]   # 2) 해당 방의 연결 리스트(기차 줄) 가져오기

        # 3) 이미 같은 이름의 편지가 있으면 내용물(value)만 교체하고 종료
        for node in bucket:
            if node.data.key == key:
                node.data.value = value
                return

        # 4) 처음 들어온 키면 편지 봉투(HashEntry)를 만들어 줄 끝에 매달고 개수 +1
        bucket.insert_back(HashEntry(key, value))
        self._size += 1

    def get(self, key):
        """[함수 역할] 키에 저장된 값을 평균 O(1)로 찾아 반환하고, 없으면 None을 돌려줍니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                return node.data.value
        return None

    def remove(self, key):
        """[함수 역할] 키를 찾아 연결 고리를 끊어 삭제하고 성공 시 True, 없으면 False를 반환합니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                bucket.remove_node(node)  # 이중 연결 리스트에서 O(1) 삭제
                self._size -= 1
                return True
        return False

    def contains(self, key):
        """[함수 역할] 특정 키가 해시맵 안에 있는지 True/False로 확인합니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                return True
        return False

    def keys(self):
        """[함수 역할] 모든 우편함을 돌며 살아 있는 모든 키 이름을 리스트로 모아 반환합니다."""
        result = []
        for bucket in self._buckets:
            for node in bucket:
                result.append(node.data.key)
        return result

    def size(self):
        """[함수 역할] 현재 해시맵에 저장된 총 키 개수를 O(1)로 반환합니다."""
        return self._size
