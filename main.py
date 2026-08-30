from utils.program_exit import install_global_exit_option
from utils.utils_main import run_utils_menu


def display_menu() -> None:
    print("\n=== ShopGraph ===\n")
    print("1. Utilities")
    print("0. Exit")


def main() -> None:
    install_global_exit_option()

    try:
        _run_main_loop()
    except SystemExit:
        print("\nGoodbye.")


def _run_main_loop() -> None:
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
