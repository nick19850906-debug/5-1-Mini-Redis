# [파일 역할] CLI REPL 진입점. 입력 파싱(큰따옴표 지원) -> 명령 검증 -> MiniRedis 호출 -> 결과 출력.

from mini_redis import MiniRedis


def parse_command(line):
    """사용자 입력 문자열을 토큰으로 분리합니다 (큰따옴표 감싸기 지원)."""
    tokens = []
    current = []
    in_quotes = False
    has_token = False

    for ch in line.strip():
        if ch == '"':
            in_quotes = not in_quotes
            has_token = True
        elif ch.isspace() and not in_quotes:
            if has_token:
                tokens.append("".join(current))
                current = []
                has_token = False
        else:
            current.append(ch)
            has_token = True

    if in_quotes:
        raise ValueError("Unclosed quote")

    if has_token:
        tokens.append("".join(current))

    return tokens


def execute_command(redis, tokens):
    """파싱된 명령어 토큰을 검증하고 MiniRedis 엔진의 메서드를 호출합니다."""
    if not tokens:
        return None

    cmd = tokens[0].upper()

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


def main():
    """CLI REPL(Read-Eval-Print Loop) 환경을 시작하는 메인 진입점입니다."""
    redis = MiniRedis()

    while True:
        try:
            line = input("mini-redis> ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower() in ("exit", "quit"):
            break

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
