# ==============================================================================
# [파일 이름] main.py
# [파일 역할] CLI REPL(대화형 창구) 진입점.
#             사용자 입력 파싱(큰따옴표 지원) -> 명령 검증 -> MiniRedis 실행 -> 결과 출력.
# [실생활 비유] 식당 키오스크 주문 창구입니다.
#              손님이 'exit' 또는 'quit'으로 나갈 때까지
#              주문 읽기(Read) -> 주방 실행(Eval) -> 결과 출력(Print)을 무한 반복(Loop)합니다.
# ==============================================================================

from mini_redis import MiniRedis


# ==============================================================================
# [1구역: 한 줄 명령어 단어 쪼개기 파서 (parse_command)]
# ==============================================================================
def parse_command(line):
    """[함수 역할] 사용자 입력 한 줄을 단어(토큰) 리스트로 쪼갭니다 (큰따옴표 "..." 내부 공백 유지)."""
    tokens = []        # 최종 잘라낸 단어 목록 (예: ['SET', 'user:1', 'Alice'])
    current = []       # 지금 조립 중인 단어의 글자들
    in_quotes = False  # 지금 큰따옴표(") 안쪽에 들어가 있는지 여부
    has_token = False  # 빈 문자열 "" 입력도 유효한 인자로 인정하기 위한 표시

    for ch in line.strip():
        if ch == '"':
            # 큰따옴표를 만나면 안/밖 상태를 뒤집음
            in_quotes = not in_quotes
            has_token = True
        elif ch.isspace() and not in_quotes:
            # 따옴표 바깥에서 띄어쓰기를 만나면 지금까지 모은 글자를 하나의 단어로 확정
            if has_token:
                tokens.append("".join(current))
                current = []
                has_token = False
        else:
            current.append(ch)
            has_token = True

    if in_quotes:
        raise ValueError("Unclosed quote")  # 따옴표를 열고 안 닫은 경우 에러 발생

    if has_token:
        tokens.append("".join(current))

    return tokens


# ==============================================================================
# [2구역: 명령어 종류 판별 및 인자 개수 검증 실행기 (execute_command)]
# ==============================================================================
def execute_command(redis, tokens):
    """[함수 역할] 쪼갠 명령어 토큰을 검사해 알맞은 MiniRedis 메서드를 부르고, 틀리면 표준 에러를 냅니다."""
    if not tokens:
        return None

    cmd = tokens[0].upper()  # 대소문자 구분 없이 실행되도록 대문자로 통일 (set -> SET)

    if cmd == "SET":
        if len(tokens) != 3:
            return "(error) ERR wrong number of arguments for 'SET' command"
        return redis.set(tokens[1], tokens[2])

    elif cmd == "GET":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'GET' command"
        return redis.get(tokens[1])

    elif cmd == "DEL":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'DEL' command"
        return redis.delete(tokens[1])

    elif cmd == "EXISTS":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'EXISTS' command"
        return redis.exists(tokens[1])

    elif cmd == "DBSIZE":
        if len(tokens) != 1:
            return "(error) ERR wrong number of arguments for 'DBSIZE' command"
        return redis.dbsize()

    elif cmd == "KEYS":
        if len(tokens) != 1:
            return "(error) ERR wrong number of arguments for 'KEYS' command"
        return redis.keys()

    elif cmd == "CONFIG":
        if (
            len(tokens) != 4
            or tokens[1].upper() != "SET"
            or tokens[2].lower() != "maxmemory"
        ):
            return "(error) ERR wrong number of arguments for 'CONFIG' command"
        return redis.config_set_maxmemory(tokens[3])

    elif cmd == "INFO":
        if len(tokens) != 2 or tokens[1].lower() != "memory":
            return "(error) ERR wrong number of arguments for 'INFO' command"
        return redis.info_memory()

    elif cmd == "EXPIRE":
        if len(tokens) != 3:
            return "(error) ERR wrong number of arguments for 'EXPIRE' command"
        return redis.expire(tokens[1], tokens[2])

    elif cmd == "TTL":
        if len(tokens) != 2:
            return "(error) ERR wrong number of arguments for 'TTL' command"
        return redis.ttl(tokens[1])

    else:
        return f"(error) ERR unknown command '{tokens[0]}'"


# ==============================================================================
# [3구역: 대화형 CLI 프롬프트 메인 루프 (main)]
# ==============================================================================
def main():
    """[함수 역할] 'mini-redis> ' 프롬프트를 띄워 명령어를 입력받고 결과를 즉시 출력합니다."""
    redis = MiniRedis()  # Mini Redis 엔진 1대 켜기

    while True:
        try:
            line = input("mini-redis> ")  # 사용자 입력 기다리기
        except (EOFError, KeyboardInterrupt):
            print()
            break  # Ctrl+C 등 중단 신호가 오면 깔끔하게 종료

        stripped = line.strip()
        if not stripped:
            continue  # 빈 엔터는 무시

        if stripped.lower() in ("exit", "quit"):
            break  # exit 또는 quit 입력 시 프로그램 종료

        try:
            tokens = parse_command(stripped)
        except ValueError:
            print("(error) ERR unbalanced quotes in request")
            continue

        result = execute_command(redis, tokens)
        if result is not None:
            print(result)


if __name__ == "__main__":
    main()
