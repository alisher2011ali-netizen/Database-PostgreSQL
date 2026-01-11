import sqlite3

DB_NAME = "sqlite_db.db"

exercise = input("Какое упражнение? Пример: пресидания (повтор) ")
exercises = []
qty = int(input("Сколько подходов? "))

for i in range(1, qty + 1):
    exercises.append(int(input(f"Кол-во поторений (времени) в {i} подходе? ")))

with sqlite3.connect(DB_NAME) as sqlite_conn:
    sql_insert = "INSERT INTO Workouts (exercise, reps_or_time) VALUES (?, ?);"
    for reps in exercises:
        sqlite_conn.execute(sql_insert, (exercise, reps))
    print("Данные успешно сохранены в базу!")
