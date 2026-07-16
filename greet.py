import sys


def greet(name: str = "World") -> str:
    return f"Hello, {name}! Welcome aboard."


def main() -> None:
    if len(sys.argv) > 1:
        print(greet(sys.argv[1]))
    else:
        print(greet())


if __name__ == "__main__":
    main()
