# ==============================================================================
# [파일 이름] min_heap.py
# [파일 역할] TTL 만료 시간 관리를 위한 배열 기반 최소 힙.
#             (expire_at, key) 중 만료 시각이 가장 이른 항목을 O(1)로 확인(peek)합니다.
# [실생활 비유] 편의점의 '유통기한 피라미드 진열대'입니다.
#              유통기한이 가장 짧은(임박한) 우유가 항상 맨 꼭대기(0번 인덱스, 루트)에 오도록
#              자리 바꿈을 유지하므로, 직원은 진열대 전체를 뒤지지 않고 맨 앞 1개(peek)만 보고도
#              지금 상한 물건이 있는지 0.001초(O(1)) 만에 판단할 수 있습니다!
# ==============================================================================


# ==============================================================================
# [1구역: 배열로 완전 이진 트리를 표현한 최소 힙(MinHeap) 클래스]
# ==============================================================================
class MinHeap:
    """TTL 만료 시간 관리를 위한 배열 기반 최소 힙.

    (expire_at, key) 형태의 튜플을 저장하여 만료 시각(expire_at)이
    가장 이른 키를 O(1)에 조회(peek)하고 O(log N)에 삽입/삭제합니다.
    """

    def __init__(self):
        """[함수 역할] 빈 피라미드 진열대(1차원 배열 self._data)를 만듭니다."""
        self._data = []  # 0번 = 맨 꼭대기 루트 / 부모 = (i-1)//2 / 자식 = 2*i+1, 2*i+2

    # --------------------------------------------------------------------------
    # [2구역: 주요 공개 기능 4종 (size, peek, push, pop)]
    # --------------------------------------------------------------------------
    def size(self):
        """[함수 역할] 현재 힙에 들어 있는 (expire_at, key) 항목 개수를 반환합니다."""
        return len(self._data)

    def peek(self):
        """[함수 역할] 가장 빨리 만료될 루트(0번 자리)를 꺼내지 않고 O(1)로 살짝 엿봅니다."""
        if not self._data:
            return None
        return self._data[0]

    def push(self, item):
        """[함수 역할] 새 (expire_at, key)를 맨 끝에 넣고, 위로 올려보내(_heapify_up) 제자리를 찾습니다."""
        self._data.append(item)               # 1) 일단 피라미드 맨 마지막 칸에 추가
        self._heapify_up(len(self._data) - 1)  # 2) 방금 넣은 칸부터 부모와 비교하며 위로 승진(O(log N))

    def pop(self):
        """[함수 역할] 가장 빨리 만료될 0번 루트를 꺼내고, 맨 끝 노드를 올려 아래로 정렬(_heapify_down)합니다."""
        if not self._data:
            return None
        if len(self._data) == 1:
            return self._data.pop()

        root = self._data[0]              # 1) 맨 꼭대기 1등(최솟값) 따로 챙겨두기
        self._data[0] = self._data.pop()  # 2) 맨 마지막 칸 요소를 뽑아 임시로 0번 자리에 올림
        self._heapify_down(0)             # 3) 자식들과 비교하며 내려보내 피라미드 규칙 복구(O(log N))
        return root                       # 4) 챙겨둔 1등 반환

    # --------------------------------------------------------------------------
    # [3구역: 피라미드 서열 유지 핵심 정렬 (_heapify_up, _heapify_down)]
    # --------------------------------------------------------------------------
    def _heapify_up(self, index):
        """[함수 역할] 새 노드의 만료 시각(index[0])이 부모보다 작으면 부모와 자리를 바꾸며 위로 올라갑니다."""
        while index > 0:
            parent_idx = (index - 1) // 2  # 내 직속 부모(윗칸) 번호 공식
            # item[0]은 expire_at(만료 시각 타임스탬프)
            if self._data[index][0] < self._data[parent_idx][0]:
                self._data[index], self._data[parent_idx] = (
                    self._data[parent_idx],
                    self._data[index],
                )
                index = parent_idx
            else:
                break

    def _heapify_down(self, index):
        """[함수 역할] 루트(0번)로 올라온 노드를 왼쪽·오른쪽 자식 중 더 급한 쪽과 바꾸며 아래로 내립니다."""
        n = len(self._data)
        while True:
            smallest = index           # 일단 나 자신을 최솟값 후보로 둠
            left = 2 * index + 1       # 왼쪽 자식 번호 공식
            right = 2 * index + 2      # 오른쪽 자식 번호 공식

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
