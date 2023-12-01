import argparse
from bot import QuiplashBot


parser = argparse.ArgumentParser(description="Quiplash bot")
parser.add_argument(
    "roomcode", type=str, default="",
)


def main():
    try:
        args = parser.parse_args()
        roomcode = args.roomcode

        username = "chatgpt"
        model = "gpt-3.5-turbo"
        qb = QuiplashBot(model=model)
        qb.join_game(roomcode, username)
        qb.play()

    except KeyboardInterrupt:
        qb.driver.quit()
        exit()

if __name__ == "__main__":
    main()
