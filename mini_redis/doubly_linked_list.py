# [파일 역할] O(1) 삽입/삭제/이동을 지원하는 이중 연결 리스트.
#            LRU 순서 추적과 해시맵 체이닝(충돌 해결)에 재사용된다.


class Node:
    """이중 연결 리스트의 단일 노드 클래스.

    Attributes:
        data: 노드에 저장할 실제 데이터
        prev: 이전 노드를 가리키는 포인터
        next: 다음 노드를 가리키는 포인터
    """

    def __init__(self, data=None):
        self.data = data
        self.prev = None
        self.next = None


class DoublyLinkedList:
    """모든 삽입, 삭제, 이동 연산이 O(1)에 동작하는 이중 연결 리스트.

    경계 조건(빈 리스트, 첫/마지막 노드 처리) 예외를 없애기 위해
    더미(Sentinel) 노드인 head와 tail을 양 끝에 배치합니다.
    """

    def __init__(self):
        self.head = Node()
        self.tail = Node()
        self.head.next = self.tail
        self.tail.prev = self.head
        self._size = 0

    def _add_after(self, target_node, new_node):
        """target_node 바로 뒤에 new_node를 O(1)에 연결하는 내부 헬퍼 메서드."""
        new_node.prev = target_node
        new_node.next = target_node.next
        target_node.next.prev = new_node
        target_node.next = new_node
        self._size += 1

    def insert_front(self, data):
        """리스트 맨 앞(head 바로 뒤)에 새 노드를 O(1)에 삽입하고 노드를 반환합니다."""
        new_node = Node(data)
        self._add_after(self.head, new_node)
        return new_node

    def insert_back(self, data):
        """리스트 맨 뒤(tail 바로 앞)에 새 노드를 O(1)에 삽입하고 노드를 반환합니다."""
        new_node = Node(data)
        self._add_after(self.tail.prev, new_node)
        return new_node

    def remove_node(self, node):
        """특정 노드의 앞뒤 연결고리만 재연결하여 O(1)에 제거하고 데이터를 반환합니다."""
        if node is None or node is self.head or node is self.tail:
            return None
        node.prev.next = node.next
        node.next.prev = node.prev
        node.prev = None
        node.next = None
        self._size -= 1
        return node.data

    def remove_front(self):
        """리스트의 가장 앞에 있는 노드를 O(1)에 제거하고 데이터를 반환합니다."""
        if self._size == 0:
            return None
        return self.remove_node(self.head.next)

    def remove_back(self):
        """리스트의 가장 뒤에 있는 노드를 O(1)에 제거하고 데이터를 반환합니다."""
        if self._size == 0:
            return None
        return self.remove_node(self.tail.prev)

    def move_to_front(self, node):
        """기존 노드를 리스트의 맨 앞(가장 최근 사용 위치)으로 O(1)에 이동시킵니다."""
        if node is None or node is self.head or node is self.tail:
            return
        # 1. 기존 위치에서 연결 해제
        node.prev.next = node.next
        node.next.prev = node.prev
        # 2. head 바로 뒤로 재연결
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def __len__(self):
        """저장된 실제 노드의 개수를 반환합니다."""
        return self._size

    def __iter__(self):
        """head 다음부터 tail 이전까지 노드를 순차적으로 순회합니다."""
        curr = self.head.next
        while curr is not self.tail:
            yield curr
            curr = curr.next
