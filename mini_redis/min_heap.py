# [파일 역할] TTL 만료 시간 관리를 위한 배열 기반 최소 힙.
#            (expire_at, key) 중 만료 시각이 가장 이른 항목을 O(1)로 확인한다.


class MinHeap:
    """TTL 만료 시간 관리를 위한 배열 기반 최소 힙.

    (expire_at, key) 형태의 튜플을 저장하여 만료 시각(expire_at)이
    가장 이른 키를 O(1)에 조회(peek)하고 O(log N)에 삽입/삭제합니다.
    """

    def __init__(self):
        self._data = []

    def size(self):
        """힙에 저장된 요소의 개수를 반환합니다."""
        return len(self._data)

    def peek(self):
        """가장 빨리 만료되는 루트 요소를 제거하지 않고 반환합니다."""
        if not self._data:
            return None
        return self._data[0]

    def push(self, item):
        """새 (expire_at, key) 요소를 힙 끝에 추가하고 위로 정렬합니다."""
        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self):
        """가장 빨리 만료되는 루트 요소를 꺼내 반환하고 힙 구조를 재정렬합니다."""
        if not self._data:
            return None
        if len(self._data) == 1:
            return self._data.pop()

        root = self._data[0]
        self._data[0] = self._data.pop()
        self._heapify_down(0)
        return root

    def _heapify_up(self, index):
        """삽입된 노드를 부모 노드와 비교하며 최소 힙 조건을 만족할 때까지 위로 올립니다."""
        while index > 0:
            parent_idx = (index - 1) // 2
            if self._data[index][0] < self._data[parent_idx][0]:
                self._data[index], self._data[parent_idx] = (
                    self._data[parent_idx],
                    self._data[index],
                )
                index = parent_idx
            else:
                break

    def _heapify_down(self, index):
        """루트로 이동한 노드를 자식 노드들과 비교하며 최소 힙 조건을 만족할 때까지 아래로 내립니다."""
        n = len(self._data)
        while True:
            smallest = index
            left = 2 * index + 1
            right = 2 * index + 2

            if left < n and self._data[left][0] < self._data[smallest][0]:
                smallest = left
            if right < n and self._data[right][0] < self._data[smallest][0]:
                smallest = right

            if smallest != index:
                self._data[index], self._data[smallest] = (
                    self._data[smallest],
                    self._data[index],
                )
                index = smallest
            else:
                break
