from colorama import Fore, Style, init

init(autoreset=True)


def check_winner(board, symbol):
    """
    Проверка победителя

    :param board: Нынешнее игровое поле
    :param symbol: Символ, который проверяется на победителя (только 'x' или 'o')
    """
    # Проверка строк
    for row in board:
        if all(cell == symbol for cell in row[1:]):
            return True
    # Проверка столбцов
    for col in range(1, 4):
        if all(board[row][col] == symbol for row in range(3)):
            return True
    # Проверка диагоналей
    if board[0][1] == board[1][2] == board[2][3] == symbol:
        return True
    if board[0][3] == board[1][2] == board[2][1] == symbol:
        return True
    return False


def print_matrix(matrix):
    for row in matrix:
        print(*row)


choosed_squares = []
# Изначальная доска
matrix = [[" ", "1", "2", "3"], [" ", "4", "5", "6"], [" ", "7", "8", "9"]]

print_matrix(matrix)

while True:
    # --- ХОД КРЕСТИКОВ ---
    try:
        a = int(input(Fore.RED + "Ходят крестики (1-9): " + Fore.RESET))
        if a < 1 or a > 9 or a in choosed_squares:
            print("Некорректный ввод или клетка занята!")
            continue
    except ValueError:
        print("Введите число!")
        continue

    choosed_squares.append(a)

    r, c = (a - 1) // 3, (a - 1) % 3 + 1
    matrix[r][c] = Fore.RED + "x" + Fore.RESET

    print_matrix(matrix)

    if check_winner(matrix, Fore.RED + "x" + Fore.RESET):
        print(Fore.RED + "Крестики победили!")
        break

    if len(choosed_squares) == 9:
        print(Fore.YELLOW + "Ничья!")
        break

    # --- ХОД НОЛИКОВ ---
    try:
        b = int(input(Fore.CYAN + "Ходят нолики (1-9): " + Fore.RESET))
        if b < 1 or b > 9 or b in choosed_squares:
            print("Некорректный ввод или клетка занята!")
            continue
    except ValueError:
        print("Введите число!")
        continue

    choosed_squares.append(b)
    r_b, c_b = (b - 1) // 3, (b - 1) % 3 + 1
    matrix[r_b][c_b] = Fore.CYAN + "o" + Fore.RESET

    print_matrix(matrix)

    if check_winner(matrix, Fore.CYAN + "o" + Fore.RESET):
        print(Fore.CYAN + "Нолики победили!")
        break
