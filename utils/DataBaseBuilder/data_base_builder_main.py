def display_data_base_builder_menu() -> None:
    print(
        "\n=== ShopGraph Data Base Builder ===\n"
    )

    print(
        "0. Return to Main"
    )


def run_data_base_builder_menu() -> None:
    while True:
        display_data_base_builder_menu()

        option = input(
            "\nSelect option: "
        ).strip()

        if option == "0":
            return

        else:
            print(
                "\n[ERROR] Invalid option."
            )


def main() -> None:
    run_data_base_builder_menu()


if __name__ == "__main__":
    main()
