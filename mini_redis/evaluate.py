# [파일 역할] 동료 평가자용 자동 점검 스크립트.
#            README의 체크리스트 항목을 실행해서 PASS/FAIL로 보여준다.
# 실행: cd mini_redis  ->  python evaluate.py

import ast
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from doubly_linked_list import DoublyLinkedList
from hash_map import HashMap
from min_heap import MinHeap
from main import parse_command, execute_command
from mini_redis import MiniRedis

FILES = ["doubly_linked_list.py", "hash_map.py", "min_heap.py", "mini_redis.py", "main.py"]


def run(redis, line):
    return execute_command(redis, parse_command(line))


def check_no_builtin_collections():
    """dict/set/collections 사용 금지 (AST 검사)."""
    for name in FILES:
        with open(os.path.join(BASE, name), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        for n in ast.walk(tree):
            assert not isinstance(n, (ast.Dict, ast.Set, ast.DictComp, ast.SetComp)), name
            if isinstance(n, ast.Import):
                assert all(a.name != "collections" for a in n.names), name
            if isinstance(n, ast.ImportFrom):
                assert n.module != "collections", name
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                assert n.func.id not in ("dict", "set"), name


def check_doubly_linked_list():
    d = DoublyLinkedList()
    a = d.insert_front("A")
    b = d.insert_back("B")
    c = d.insert_front("C")
    assert [n.data for n in d] == ["C", "A", "B"]
    d.move_to_front(b)
    assert [n.data for n in d] == ["B", "C", "A"]
    assert d.remove_node(c) == "C"
    assert d.remove_back() == "A" and d.remove_front() == "B"
    assert len(d) == 0 and a is not None


def check_hash_map():
    h = HashMap(initial_capacity=4)
    for i in range(20):
        h.put("k%d" % i, i)
    assert h.size() == 20 and h._capacity > 4
    assert all(h.get("k%d" % i) == i for i in range(20))
    h.put("k3", "new")
    assert h.get("k3") == "new" and h.size() == 20
    assert h.remove("k3") is True and h.contains("k3") is False
    assert h.remove("nope") is False and len(h.keys()) == 19


def check_min_heap():
    m = MinHeap()
    for t, k in [(30, "c"), (10, "a"), (20, "b")]:
        m.push((t, k))
    assert m.peek() == (10, "a") and m.size() == 3
    assert [m.pop(), m.pop(), m.pop()] == [(10, "a"), (20, "b"), (30, "c")]
    assert m.pop() is None


def check_official_example():
    r = MiniRedis()
    assert run(r, "CONFIG SET maxmemory 30") == "OK"
    assert run(r, 'SET user:1 "Alice"') == "OK"
    assert run(r, 'SET user:2 "Bob"') == "OK"
    assert run(r, 'SET user:3 "Charlie"') == "OK"
    assert run(r, "GET user:1") == "(nil)"
    assert run(r, "INFO memory") == "used_memory:22\nmaxmemory:30\nevicted_keys:1"
    keys = run(r, "KEYS")
    assert '"user:2"' in keys and '"user:3"' in keys
    assert run(r, "DBSIZE") == "(integer) 2"


def check_lru_order_and_oom():
    r = MiniRedis()
    run(r, "CONFIG SET maxmemory 30")
    run(r, 'SET user:1 "Alice"')
    run(r, 'SET user:2 "Bob"')
    assert run(r, "GET user:1") == '"Alice"'      # user:1 최신화 -> user:2가 LRU
    run(r, 'SET user:3 "Charlie"')
    assert run(r, "GET user:2") == "(nil)"
    assert run(r, "GET user:1") == '"Alice"'
    res = run(r, 'SET big "' + "x" * 40 + '"')
    assert res == "(error) OOM command not allowed when used_memory > 'maxmemory'"


def check_ttl():
    r = MiniRedis()
    run(r, 'SET a "1"')
    assert run(r, "TTL a") == "(integer) -1"
    assert run(r, "TTL nokey") == "(integer) -2"
    assert run(r, "EXPIRE nokey 5") == "(integer) 0"
    assert run(r, "EXPIRE a 10") == "(integer) 1"
    assert 1 <= int(run(r, "TTL a").split()[1]) <= 10
    run(r, 'SET a "2"')                            # 덮어쓰기 -> TTL 초기화
    assert run(r, "TTL a") == "(integer) -1"
    run(r, "EXPIRE a 1")
    time.sleep(1.2)
    assert run(r, "GET a") == "(nil)"
    assert run(r, "TTL a") == "(integer) -2"
    run(r, 'SET b "1"')
    assert run(r, "EXPIRE b 0") == "(integer) 1" and run(r, "EXISTS b") == "(integer) 0"


def check_del_exists():
    r = MiniRedis()
    run(r, 'SET a "1"')
    assert run(r, "EXISTS a") == "(integer) 1"
    assert run(r, "DEL a") == "(integer) 1" and run(r, "DEL a") == "(integer) 0"
    assert run(r, "KEYS") == "(empty array)"
    assert run(r, "INFO memory").startswith("used_memory:0")


def check_errors():
    r = MiniRedis()
    assert run(r, "CONFIG SET maxmemory abc") == "(error) ERR value is not an integer or out of range"
    assert run(r, "GET") == "(error) ERR wrong number of arguments for 'GET' command"
    assert run(r, "HELLO") == "(error) ERR unknown command 'HELLO'"
    assert run(r, 'SET msg "hello world"') == "OK"
    assert run(r, "GET msg") == '"hello world"'


CHECKS = [
    ("dict / set / collections 미사용", check_no_builtin_collections),
    ("이중 연결 리스트 (삽입/삭제/이동)", check_doubly_linked_list),
    ("해시맵 (체이닝 + 로드팩터 확장)", check_hash_map),
    ("최소 힙 (push/pop/peek)", check_min_heap),
    ("명세서 공식 예시 (LRU 제거 + INFO)", check_official_example),
    ("GET 시 LRU 갱신 + 단일 엔트리 OOM", check_lru_order_and_oom),
    ("TTL (EXPIRE/TTL/만료/덮어쓰기 초기화)", check_ttl),
    ("DEL / EXISTS / 메모리 차감", check_del_exists),
    ("에러 표준 출력 + 따옴표 값 파싱", check_errors),
]

if __name__ == "__main__":
    passed = 0
    for title, fn in CHECKS:
        try:
            fn()
            print("[PASS] " + title)
            passed += 1
        except AssertionError as e:
            print("[FAIL] " + title + " -> " + repr(e))
    print("\n결과: %d / %d 통과" % (passed, len(CHECKS)))
    sys.exit(0 if passed == len(CHECKS) else 1)
