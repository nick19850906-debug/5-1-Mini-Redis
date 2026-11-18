# [파일 역할] 직접 설계한 해시 함수 + 체이닝(이중 연결 리스트 재사용) 기반 해시맵.
#            내장 dict/set/collections 없이 O(1) 평균 조회/삽입/삭제를 구현한다.

from doubly_linked_list import DoublyLinkedList


class HashEntry:
    """해시맵 버킷(체이닝 리스트)에 저장되는 Key-Value 쌍 데이터 객체."""

    def __init__(self, key, value):
        self.key = key
        self.value = value


class HashMap:
    """체이닝(이중 연결 리스트 재사용)과 동적 리사이징을 지원하는 해시맵.

    내장 dict, set, collections를 사용하지 않고 고정 크기 리스트와
    직접 구현한 DoublyLinkedList만으로 O(1) 평균 조회/삽입/삭제를 구현합니다.
    """

    LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(self, initial_capacity=16):
        self._capacity = initial_capacity
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        self._size = 0

    def _hash(self, key):
        """다항식 롤링 해시(Polynomial Rolling Hash)로 문자열 키의 버킷 인덱스를 계산합니다."""
        key_str = str(key)
        hash_val = 0
        prime = 31
        for ch in key_str:
            hash_val = (hash_val * prime + ord(ch)) % self._capacity
        return hash_val

    def _resize(self):
        """로드 팩터가 0.75를 초과하면 버킷 크기를 2배 확장하고 전체 데이터를 재해싱합니다."""
        old_buckets = self._buckets
        self._capacity *= 2
        self._buckets = [DoublyLinkedList() for _ in range(self._capacity)]
        self._size = 0

        for bucket in old_buckets:
            for node in bucket:
                entry = node.data
                self.put(entry.key, entry.value)

    def put(self, key, value):
        """키-값을 저장하거나 기존 키가 존재할 경우 값을 덮어씁니다."""
        if (self._size + 1) / self._capacity > self.LOAD_FACTOR_THRESHOLD:
            self._resize()

        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                node.data.value = value
                return

        bucket.insert_back(HashEntry(key, value))
        self._size += 1

    def get(self, key):
        """키에 매핑된 값을 조회합니다. 키가 없으면 None을 반환합니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                return node.data.value
        return None

    def remove(self, key):
        """키를 찾아 삭제하고 성공 시 True, 키가 없으면 False를 반환합니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                bucket.remove_node(node)
                self._size -= 1
                return True
        return False

    def contains(self, key):
        """특정 키의 존재 여부를 불리언으로 반환합니다."""
        idx = self._hash(key)
        bucket = self._buckets[idx]

        for node in bucket:
            if node.data.key == key:
                return True
        return False

    def keys(self):
        """해시맵에 저장된 모든 키를 리스트로 수집하여 반환합니다."""
        result = []
        for bucket in self._buckets:
            for node in bucket:
                result.append(node.data.key)
        return result

    def size(self):
        """현재 저장된 총 엔트리 개수를 반환합니다."""
        return self._size
