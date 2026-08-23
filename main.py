from utils.main import run_utils_menu


def display_menu() -> None:
    print("\n=== ShopGraph ===\n")
    print("1. Utilities")
    print("0. Exit")


def main() -> None:
    while True:
        display_menu()

        option = input("\nSelect option: ").strip()

        if option == "1":
            run_utils_menu()

        elif option == "0":
            print("\nGoodbye.")
            break

        else:
            print("\n[ERROR] Invalid option.")


if __name__ == "__main__":
    main()