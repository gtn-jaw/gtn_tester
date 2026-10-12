import queue
import re
import subprocess
import threading
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText


class TestRunnerApp:
    TIMEOUT_SECONDS = 300

    def __init__(self, root):
        self.root = root
        self.root.title("Tester programu")
        self.root.geometry("1000x750")
        self.root.minsize(800, 550)

        self.selected_root = None
        self.exe_path = None
        self.tests_path = None
        self.tests = []

        self.is_running = False
        self.result_queue = queue.Queue()
        self.results_by_name = {}

        self.create_widgets()

    def create_widgets(self):
        # ==========================================================
        # PRZYCISKI
        # ==========================================================

        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        self.select_button = ttk.Button(
            top_frame,
            text="Wybierz folder główny",
            command=self.select_root_folder
        )
        self.select_button.pack(side=tk.LEFT)

        self.run_button = ttk.Button(
            top_frame,
            text="Uruchom testy",
            command=self.start_tests,
            state=tk.DISABLED
        )
        self.run_button.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        self.info_button = ttk.Button(
            top_frame,
            text="Info",
            command=self.show_info
        )
        self.info_button.pack(
            side=tk.LEFT,
            padx=(10, 0)
        )

        # ==========================================================
        # INFORMACJE O FOLDERACH I PROGRAMIE
        # ==========================================================

        info_frame = ttk.LabelFrame(
            self.root,
            text="Informacje",
            padding=10
        )
        info_frame.pack(
            fill=tk.X,
            padx=10,
            pady=(0, 10)
        )

        self.root_label = ttk.Label(
            info_frame,
            text="Folder główny: —"
        )
        self.root_label.pack(anchor=tk.W)

        self.exe_label = ttk.Label(
            info_frame,
            text="Program .exe: —"
        )
        self.exe_label.pack(anchor=tk.W)

        self.tests_label = ttk.Label(
            info_frame,
            text="Folder testów: —"
        )
        self.tests_label.pack(anchor=tk.W)

        # ==========================================================
        # TABELA WYNIKÓW
        # ==========================================================

        results_frame = ttk.LabelFrame(
            self.root,
            text="Wyniki testów",
            padding=10
        )
        results_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=(0, 10)
        )

        columns = ("test", "status", "info")

        self.results_table = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings"
        )

        self.results_table.heading(
            "test",
            text="Test"
        )
        self.results_table.heading(
            "status",
            text="Wynik"
        )
        self.results_table.heading(
            "info",
            text="Informacja"
        )

        self.results_table.column(
            "test",
            width=350,
            anchor=tk.W
        )
        self.results_table.column(
            "status",
            width=180,
            anchor=tk.W
        )
        self.results_table.column(
            "info",
            width=180,
            anchor=tk.CENTER
        )

        scrollbar = ttk.Scrollbar(
            results_frame,
            orient=tk.VERTICAL,
            command=self.results_table.yview
        )

        self.results_table.configure(
            yscrollcommand=scrollbar.set
        )

        self.results_table.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        scrollbar.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        self.results_table.bind(
            "<<TreeviewSelect>>",
            self.show_selected_result
        )

        self.results_table.tag_configure(
            "ok",
            foreground="green"
        )

        self.results_table.tag_configure(
            "wrong",
            foreground="red"
        )

        self.results_table.tag_configure(
            "error",
            foreground="darkorange"
        )

        self.results_table.tag_configure(
            "timeout",
            foreground="purple"
        )

        # ==========================================================
        # SZCZEGÓŁY TESTU
        # ==========================================================

        details_frame = ttk.LabelFrame(
            self.root,
            text="Szczegóły testu",
            padding=10
        )
        details_frame.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=(0, 10)
        )

        self.details_text = ScrolledText(
            details_frame,
            wrap=tk.NONE,
            height=15,
            state=tk.DISABLED
        )

        self.details_text.pack(
            fill=tk.BOTH,
            expand=True
        )

        # ==========================================================
        # PODSUMOWANIE
        # ==========================================================

        self.summary_label = ttk.Label(
            self.root,
            text="Wybierz folder główny, aby rozpocząć."
        )

        self.summary_label.pack(
            anchor=tk.W,
            padx=10,
            pady=(0, 10)
        )

    # ==============================================================
    # WYBÓR FOLDERU GŁÓWNEGO
    # ==============================================================

    def select_root_folder(self):
        folder = filedialog.askdirectory(
            title="Wybierz folder główny"
        )

        if not folder:
            return

        root_path = Path(folder)

        try:
            exe_path, tests_path, test_pairs = (
                self.validate_structure(root_path)
            )
        except ValueError as error:
            messagebox.showerror(
                "Nieprawidłowa struktura folderów",
                str(error)
            )

            self.clear_selection()
            return

        self.selected_root = root_path
        self.exe_path = exe_path
        self.tests_path = tests_path
        self.tests = test_pairs

        self.root_label.config(
            text=f"Folder główny: {root_path}"
        )

        self.exe_label.config(
            text=f"Program .exe: {exe_path}"
        )

        self.tests_label.config(
            text=f"Folder testów: {tests_path}"
        )

        self.run_button.config(
            state=tk.NORMAL
        )

        self.clear_results()

        self.summary_label.config(
            text=(
                f"Znaleziono testów: {len(self.tests)}. "
                "Gotowe do uruchomienia."
            )
        )

    def clear_selection(self):
        self.selected_root = None
        self.exe_path = None
        self.tests_path = None
        self.tests = []

        self.root_label.config(
            text="Folder główny: —"
        )

        self.exe_label.config(
            text="Program .exe: —"
        )

        self.tests_label.config(
            text="Folder testów: —"
        )

        self.run_button.config(
            state=tk.DISABLED
        )

        self.clear_results()

        self.summary_label.config(
            text="Wybierz folder główny, aby rozpocząć."
        )

    # ==============================================================
    # SPRAWDZANIE STRUKTURY
    # ==============================================================

    def validate_structure(self, root_path):
        if not root_path.exists() or not root_path.is_dir():
            raise ValueError(
                "Wybrana ścieżka nie jest poprawnym folderem."
            )

        debug_path = root_path / "x64" / "Debug"

        if not debug_path.is_dir():
            raise ValueError(
                "Nie znaleziono folderu:\n\n"
                f"{debug_path}"
            )

        exe_files = [
            path
            for path in debug_path.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".exe"
        ]

        if len(exe_files) == 0:
            raise ValueError(
                "W folderze x64/Debug nie znaleziono pliku .exe."
            )

        if len(exe_files) > 1:
            names = "\n".join(
                f"- {path.name}"
                for path in exe_files
            )

            raise ValueError(
                "W folderze x64/Debug znaleziono więcej "
                "niż jeden plik .exe:\n\n"
                f"{names}"
            )

        tests_path = root_path / "tests"
        input_path = tests_path / "in"
        output_path = tests_path / "out"

        if not tests_path.is_dir():
            raise ValueError(
                "Nie znaleziono folderu:\n\n"
                f"{tests_path}"
            )

        if not input_path.is_dir():
            raise ValueError(
                "Nie znaleziono folderu:\n\n"
                f"{input_path}"
            )

        if not output_path.is_dir():
            raise ValueError(
                "Nie znaleziono folderu:\n\n"
                f"{output_path}"
            )

        input_files = [
            path
            for path in input_path.iterdir()
            if path.is_file()
            and path.suffix.lower() == ".in"
        ]

        if not input_files:
            raise ValueError(
                "Folder tests/in nie zawiera żadnych plików .in."
            )

        test_pairs = []

        for input_file in input_files:
            test_name = input_file.stem
            output_file = output_path / f"{test_name}.out"

            test_pairs.append({
                "name": test_name,
                "input": input_file,
                "output": output_file
            })

        test_pairs.sort(
            key=lambda test: natural_sort_key(test["name"])
        )

        return exe_files[0], tests_path, test_pairs

    # ==============================================================
    # OKNO INFORMACYJNE
    # ==============================================================

    def show_info(self):
        if self.selected_root is None:
            info = (
                "OCZEKIWANA STRUKTURA FOLDERÓW I PLIKÓW\n"
                "========================================\n\n"
                "folder_główny/\n"
                "├── x64/\n"
                "│   └── Debug/\n"
                "│       └── program.exe\n"
                "└── tests/\n"
                "    ├── in/\n"
                "    │   ├── name1.in\n"
                "    │   └── name2.in\n"
                "    └── out/\n"
                "        ├── name1.out\n"
                "        └── name2.out\n\n"
                "ZASADY DZIAŁANIA\n"
                "=================\n"
                "1. Użytkownik wybiera folder główny.\n"
                "2. Program znajduje plik .exe w:\n"
                "   x64/Debug/\n"
                "3. Pliki wejściowe znajdują się w:\n"
                "   tests/in/\n"
                "4. Pliki wyników znajdują się w:\n"
                "   tests/out/\n"
                "5. Pliki muszą mieć takie same nazwy bazowe.\n"
                "   Przykład: name.in oraz name.out\n"
                "6. Wyniki są porównywane znak po znaku.\n"
                "7. Końcowe białe znaki są ignorowane.\n"
            )

            self.show_large_info_window(
                "Informacje o programie",
                info
            )
            return

        root_path = self.selected_root
        debug_path = root_path / "x64" / "Debug"
        tests_path = root_path / "tests"
        input_path = tests_path / "in"
        output_path = tests_path / "out"

        exe_files = []

        if debug_path.is_dir():
            exe_files = sorted(
                [
                    path
                    for path in debug_path.iterdir()
                    if path.is_file()
                    and path.suffix.lower() == ".exe"
                ],
                key=lambda path: path.name.lower()
            )

        input_files = []

        if input_path.is_dir():
            input_files = sorted(
                [
                    path
                    for path in input_path.iterdir()
                    if path.is_file()
                    and path.suffix.lower() == ".in"
                ],
                key=lambda path: natural_sort_key(path.stem)
            )

        output_files = []

        if output_path.is_dir():
            output_files = sorted(
                [
                    path
                    for path in output_path.iterdir()
                    if path.is_file()
                    and path.suffix.lower() == ".out"
                ],
                key=lambda path: natural_sort_key(path.stem)
            )

        info = (
            "WYBRANY FOLDER GŁÓWNY\n"
            "=====================\n"
            f"{root_path}\n\n"

            "HIERARCHIA FOLDERÓW\n"
            "===================\n"
            f"{self.path_status(root_path / 'x64')} "
            f"{root_path / 'x64'}\n"
            f"{self.path_status(debug_path)} "
            f"{debug_path}\n"
            f"{self.path_status(tests_path)} "
            f"{tests_path}\n"
            f"{self.path_status(input_path)} "
            f"{input_path}\n"
            f"{self.path_status(output_path)} "
            f"{output_path}\n\n"

            "PLIKI .EXE\n"
            "==========\n"
        )

        if exe_files:
            info += "\n".join(
                f"[OK] {path.name}"
                for path in exe_files
            )
        else:
            info += "[BRAK] Nie znaleziono pliku .exe."

        info += (
            f"\n\nPLIKI WEJŚCIOWE .IN: {len(input_files)}\n"
            "==============================\n"
        )

        if input_files:
            info += "\n".join(
                f"- {path.name}"
                for path in input_files
            )
        else:
            info += "Brak plików .in."

        info += (
            f"\n\nPLIKI WYJŚCIOWE .OUT: {len(output_files)}\n"
            "================================\n"
        )

        if output_files:
            info += "\n".join(
                f"- {path.name}"
                for path in output_files
            )
        else:
            info += "Brak plików .out."

        info += (
            f"\n\nLICZBA ZNALEZIONYCH TESTÓW: "
            f"{len(self.tests)}\n"
        )

        self.show_large_info_window(
            "Informacje o hierarchii folderów i plików",
            info
        )

    @staticmethod
    def path_status(path):
        if path.exists():
            return "[OK]"

        return "[BRAK]"

    def show_large_info_window(self, title, content):
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("850x650")
        window.minsize(600, 400)

        text = ScrolledText(
            window,
            wrap=tk.NONE
        )
        text.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=10
        )

        text.insert(
            "1.0",
            content
        )

        text.config(
            state=tk.DISABLED
        )

        close_button = ttk.Button(
            window,
            text="Zamknij",
            command=window.destroy
        )

        close_button.pack(
            pady=(0, 10)
        )

    # ==============================================================
    # URUCHAMIANIE TESTÓW
    # ==============================================================

    def start_tests(self):
        if self.is_running:
            return

        if not self.exe_path or not self.tests:
            messagebox.showwarning(
                "Brak danych",
                "Najpierw wybierz poprawny folder główny."
            )
            return

        self.is_running = True
        self.results_by_name.clear()

        self.select_button.config(
            state=tk.DISABLED
        )

        self.run_button.config(
            state=tk.DISABLED
        )

        self.clear_results()

        self.summary_label.config(
            text="Trwa wykonywanie testów..."
        )

        worker_thread = threading.Thread(
            target=self.run_all_tests,
            daemon=True
        )

        worker_thread.start()

        self.root.after(
            100,
            self.process_result_queue
        )

    def run_all_tests(self):
        results = []

        for test in self.tests:
            result = self.run_single_test(test)
            results.append(result)

            self.result_queue.put({
                "type": "result",
                "data": result
            })

        self.result_queue.put({
            "type": "finished",
            "data": results
        })

    def run_single_test(self, test):
        test_name = test["name"]
        input_file = test["input"]
        output_file = test["output"]

        # Odczyt danych wejściowych
        try:
            input_text = input_file.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError as error:
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Błąd kodowania",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_file}\n\n"
                    "Nie udało się odczytać pliku wejściowego "
                    "jako UTF-8.\n\n"
                    f"{error}"
                )
            }
        except OSError as error:
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Błąd odczytu",
                "details": (
                    "Nie udało się odczytać danych wejściowych.\n\n"
                    f"{error}"
                )
            }

        # Sprawdzenie pliku .out
        if not output_file.exists():
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Brak pliku .out",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Brak odpowiadającego pliku wyjściowego:\n"
                    f"{output_file}"
                )
            }

        # Odczyt oczekiwanego wyniku
        try:
            expected_text = output_file.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError as error:
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Błąd kodowania",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Nie udało się odczytać pliku .out "
                    "jako UTF-8.\n\n"
                    f"{error}"
                )
            }
        except OSError as error:
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Błąd odczytu",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Nie udało się odczytać pliku .out.\n\n"
                    f"{error}"
                )
            }

        # Uruchomienie programu .exe
        try:
            completed = subprocess.run(
                [str(self.exe_path)],
                input=input_text,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.TIMEOUT_SECONDS,
                cwd=str(self.exe_path.parent)
            )

        except subprocess.TimeoutExpired:
            return {
                "name": test_name,
                "status": "TIMEOUT",
                "tag": "timeout",
                "info": f">{self.TIMEOUT_SECONDS} s",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Program nie zakończył działania w czasie "
                    f"{self.TIMEOUT_SECONDS} sekund."
                )
            }

        except OSError as error:
            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": "Nie uruchomiono",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Nie udało się uruchomić programu .exe.\n\n"
                    f"{error}"
                )
            }

        received_text = completed.stdout

        # Program zakończył się kodem błędu
        if completed.returncode != 0:
            stderr_text = completed.stderr.strip()

            details = (
                "Dane wejściowe:\n"
                f"{input_text}\n\n"
                f"Program zakończył działanie z kodem: "
                f"{completed.returncode}\n"
            )

            if stderr_text:
                details += (
                    "\nKomunikat błędu programu:\n"
                    f"{stderr_text}\n"
                )

            details += (
                "\nPoprawny wynik:\n"
                f"{expected_text}\n"
                "\nOtrzymany wynik:\n"
                f"{received_text}"
            )

            return {
                "name": test_name,
                "status": "BŁĄD",
                "tag": "error",
                "info": f"Kod {completed.returncode}",
                "details": details
            }

        # Porównanie wyników.
        # rstrip() ignoruje białe znaki wyłącznie na końcu.
        expected_normalized = expected_text.rstrip()
        received_normalized = received_text.rstrip()

        if expected_normalized == received_normalized:
            return {
                "name": test_name,
                "status": "OK ✓",
                "tag": "ok",
                "info": "Poprawny",
                "details": (
                    "Dane wejściowe:\n"
                    f"{input_text}\n\n"
                    "Wynik programu:\n"
                    f"{received_text}"
                )
            }

        return {
            "name": test_name,
            "status": "NIEPOPRAWNY ✗",
            "tag": "wrong",
            "info": "Różny wynik",
            "details": (
                "Dane wejściowe:\n"
                f"{input_text}\n\n"
                "Poprawny wynik:\n"
                f"{expected_text}\n"
                "\nOtrzymany wynik:\n"
                f"{received_text}"
            )
        }

    # ==============================================================
    # ODBIERANIE WYNIKÓW Z WĄTKU
    # ==============================================================

    def process_result_queue(self):
        try:
            while True:
                message = self.result_queue.get_nowait()

                if message["type"] == "result":
                    self.display_result(message["data"])

                elif message["type"] == "finished":
                    self.finish_tests(message["data"])

        except queue.Empty:
            pass

        if self.is_running:
            self.root.after(
                100,
                self.process_result_queue
            )

    def display_result(self, result):
        test_name = result["name"]

        self.results_by_name[test_name] = result["details"]

        self.results_table.insert(
            "",
            tk.END,
            values=(
                test_name,
                result["status"],
                result["info"]
            ),
            tags=(result["tag"],)
        )

    def finish_tests(self, results):
        self.is_running = False

        self.select_button.config(
            state=tk.NORMAL
        )

        self.run_button.config(
            state=tk.NORMAL
        )

        total = len(results)

        correct = sum(
            1
            for result in results
            if result["status"] == "OK ✓"
        )

        wrong = sum(
            1
            for result in results
            if result["status"] == "NIEPOPRAWNY ✗"
        )

        errors = sum(
            1
            for result in results
            if result["status"] in ("BŁĄD", "TIMEOUT")
        )

        self.summary_label.config(
            text=(
                f"Zakończono. Wszystkich testów: {total} | "
                f"Poprawnych: {correct} | "
                f"Niepoprawnych: {wrong} | "
                f"Błędów: {errors}"
            )
        )

        if results:
            items = self.results_table.get_children()

            if items:
                last_item = items[-1]

                self.results_table.selection_set(
                    last_item
                )

                self.results_table.focus(
                    last_item
                )

                self.show_selected_result()

    # ==============================================================
    # WYŚWIETLANIE SZCZEGÓŁÓW TESTU
    # ==============================================================

    def show_selected_result(self, event=None):
        selected_items = self.results_table.selection()

        if not selected_items:
            return

        selected_item = selected_items[0]

        values = self.results_table.item(
            selected_item
        ).get("values", [])

        if not values:
            return

        test_name = values[0]
        details = self.results_by_name.get(
            test_name,
            ""
        )

        self.set_details(details)

    def set_details(self, text):
        self.details_text.config(
            state=tk.NORMAL
        )

        self.details_text.delete(
            "1.0",
            tk.END
        )

        self.details_text.insert(
            "1.0",
            text
        )

        self.details_text.config(
            state=tk.DISABLED
        )

    def clear_results(self):
        for item in self.results_table.get_children():
            self.results_table.delete(item)

        self.results_by_name.clear()
        self.set_details("")


def natural_sort_key(text):
    """
    Sortowanie naturalne:

    test1
    test2
    test10

    zamiast:

    test1
    test10
    test2
    """
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", text)
    ]


if __name__ == "__main__":
    root = tk.Tk()
    app = TestRunnerApp(root)
    root.mainloop()