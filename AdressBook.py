from collections import UserDict
from datetime import datetime, date, timedelta
import pickle


# --- 1. Функції для серіалізації/десеріалізації ---

def save_data(book, filename="addressbook.pkl"):
    """Зберігає стан адресної книги у файл за допомогою pickle."""
    with open(filename, "wb") as f:
        pickle.dump(book, f)


def load_data(filename="addressbook.pkl"):
    """Завантажує адресну книгу з файлу або створює нову, якщо файл не знайдено."""
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return AddressBook()  # Повернення нової адресної книги, якщо файл відсутній


# --- 2. Класи даних та валідація ---

class Field:
    """Базовий клас для полів запису."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)


class Name(Field):
    """Обов'язкове поле з ім'ям контакту."""
    pass


class Phone(Field):
    """Поле телефону з перевіркою на 10 цифр."""
    def __init__(self, value):
        if not (value.isdigit() and len(value) == 10):
            raise ValueError("Phone number must contain exactly 10 digits.")
        super().__init__(value)


class Birthday(Field):
    """Поле для дня народження. Зберігає значення як рядок у форматі DD.MM.YYYY."""
    def __init__(self, value: str):
        try:
            datetime.strptime(value, "%d.%m.%Y")
            super().__init__(value)
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")

    @property
    def date_obj(self) -> date:
        """Динамічно повертає об'єкт date на основі рядка self.value."""
        return datetime.strptime(self.value, "%d.%m.%Y").date()


# --- 3. Логіка запису та адресної книги ---

class Record:
    """Запис контакту: ім'я, список телефонів та день народження."""
    def __init__(self, name):
        self.name = Name(name)
        self.phones = []
        self.birthday = None

    def add_phone(self, phone_number):
        self.phones.append(Phone(phone_number))

    def remove_phone(self, phone_number):
        phone_to_remove = self.find_phone(phone_number)
        if phone_to_remove:
            self.phones.remove(phone_to_remove)
            return True
        return False

    def edit_phone(self, old_phone, new_phone):
        phone_to_edit = self.find_phone(old_phone)
        if not phone_to_edit:
            raise ValueError(f"Phone number {old_phone} not found.")
        new_phone_obj = Phone(new_phone)
        index = self.phones.index(phone_to_edit)
        self.phones[index] = new_phone_obj

    def find_phone(self, phone_number):
        for phone in self.phones:
            if phone.value == phone_number:
                return phone
        return None

    def add_birthday(self, birthday_string):
        self.birthday = Birthday(birthday_string)

    def __str__(self):
        phones_str = '; '.join(p.value for p in self.phones) if self.phones else "No phones"
        birthday_str = f", birthday: {self.birthday.value}" if self.birthday else ""
        return f"Contact name: {self.name.value}, phones: {phones_str}{birthday_str}"


class AddressBook(UserDict):
    """Адресна книга для збереження та обробки записів."""
    def add_record(self, record):
        self.data[record.name.value] = record

    def find(self, name):
        return self.data.get(name, None)

    def delete(self, name):
        if name in self.data:
            del self.data[name]

    def get_upcoming_birthdays(self, days=7):
        """Знаходить контакти, у яких день народження припадає на наступні 7 днів."""
        upcoming_birthdays = []
        today = date.today()

        for record in self.data.values():
            if record.birthday is None:
                continue

            birthday_this_year = record.birthday.date_obj.replace(year=today.year)

            if birthday_this_year < today:
                birthday_this_year = birthday_this_year.replace(year=today.year + 1)

            delta_days = (birthday_this_year - today).days

            if 0 <= delta_days <= days:
                congratulation_date = birthday_this_year
                if congratulation_date.weekday() >= 5:
                    days_ahead = 7 - congratulation_date.weekday()
                    congratulation_date += timedelta(days=days_ahead)

                upcoming_birthdays.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%d.%m.%Y")
                })

        return upcoming_birthdays


# --- 4. Декоратор та обробники команд ---

def input_error(func):
    """Декоратор для перехоплення помилок вводу та відсутності знайденого контакту."""
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e) if str(e) else "Give me name and phone please."
        except IndexError:
            return "Enter user name or missing arguments."
        except (KeyError, AttributeError):
            return "Contact not found."
    return inner


def parse_input(user_input: str):
    """Розбирає введений рядок на команду та аргументи."""
    cmd, *args = user_input.split()
    cmd = cmd.strip().lower()
    return cmd, *args


@input_error
def add_contact(args, book: AddressBook):
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_contact(args, book: AddressBook):
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    record.edit_phone(old_phone, new_phone)
    return "Contact phone updated successfully."


@input_error
def show_phone(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if not record.phones:
        return f"No phone numbers found for {name}."
    return f"{name}'s phones: {', '.join(p.value for p in record.phones)}"


@input_error
def show_all(book: AddressBook):
    if not book.data:
        return "Address book is empty."
    return "\n".join(str(record) for record in book.data.values())


@input_error
def add_birthday(args, book: AddressBook):
    name, birthday_str, *_ = args
    record = book.find(name)
    record.add_birthday(birthday_str)
    return f"Birthday added for {name}."


@input_error
def show_birthday(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record.birthday is None:
        return f"No birthday set for {name}."
    return f"{name}'s birthday: {record.birthday.value}"


@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No upcoming birthdays for the next 7 days."
    
    result = ["Upcoming birthdays:"]
    for user in upcoming:
        result.append(f"{user['name']}: {user['congratulation_date']}")
    return "\n".join(result)


# --- 5. Головний цикл бота ---

def main():
    # Завантажуємо дані з файлу при запуску програми
    book = load_data()
    print("Welcome to the assistant bot!")
    
    while True:
        user_input = input("Enter a command: ").strip()
        if not user_input:
            continue

        command, *args = parse_input(user_input)

        if command in ["close", "exit"]:
            # Зберігаємо дані у файл перед виходом з програми
            save_data(book)
            print("Good bye!")
            break

        elif command == "hello":
            print("How can I help you?")

        elif command == "add":
            print(add_contact(args, book))

        elif command == "change":
            print(change_contact(args, book))

        elif command == "phone":
            print(show_phone(args, book))

        elif command == "all":
            print(show_all(book))

        elif command == "add-birthday":
            print(add_birthday(args, book))

        elif command == "show-birthday":
            print(show_birthday(args, book))

        elif command == "birthdays":
            print(birthdays(args, book))

        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()