import os
import sys


def prompt_selection(options, title, multi=False):
    """
    Generic interactive selection menu.
    options: list of (label, value) tuples.
    title: string to display.
    multi: boolean, if true allows multiple selection.
    returns: selected value (or list of values if multi).
    """
    if not options:
        return [] if multi else None

    def fallback_prompt():
        print(f"\n{title}:")
        for i, (text, _) in enumerate(options, 1):
            print(f"  {i}. {text}")
        if multi:
            print("  (Ingresa números separados por coma, ej: 1,3,4 o 'all' para todos)")
        while True:
            try:
                choice = input("\nSelección: ").strip().lower()
                if not choice:
                    if multi: return []
                    continue
                if multi and choice == 'all':
                    return [val for _, val in options]
                if multi:
                    indices = [int(x.strip()) for x in choice.replace(',', ' ').split() if x.strip()]
                    selected = []
                    for idx in indices:
                        if 1 <= idx <= len(options):
                            selected.append(options[idx-1][1])
                    return selected
                else:
                    idx = int(choice)
                    if 1 <= idx <= len(options):
                        return options[idx-1][1]
                print("Selección inválida.")
            except ValueError:
                print("Por favor ingresa un valor válido.")
            except (KeyboardInterrupt, EOFError):
                print("\nOperación cancelada.")
                sys.exit(0)

    if not sys.stdin.isatty():
        return fallback_prompt()

    try:
        import tty
        import termios
    except ImportError:
        return fallback_prompt()

    def getch():
        fd = sys.stdin.fileno()
        try:
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return sys.stdin.read(1)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch += sys.stdin.read(2)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    current_idx = 0
    selected_indices = set()
    input_buffer = ""

    # Grid settings
    try:
        term_width = os.get_terminal_size().columns
    except Exception:
        term_width = 80

    max_text_len = max(len(text) for text, _ in options)
    item_width = max_text_len + 10
    num_cols = max(1, term_width // item_width)
    num_rows = (len(options) + num_cols - 1) // num_cols
    lines_to_clear = num_rows + 1

    print(f"\n{title}:")

    def render_menu():
        sys.stdout.write("\r")
        for row in range(num_rows):
            line_content = ""
            for col in range(num_cols):
                idx = row + col * num_rows
                if idx < len(options):
                    text, _ = options[idx]
                    num = f"{idx+1:2d}. "
                    prefix = "❯ " if idx == current_idx else "  "
                    if multi:
                        mark = "[x] " if idx in selected_indices else "[ ] "
                        prefix += mark

                    item = f"{prefix}{num}{text}"
                    padding = " " * (item_width - len(item))

                    if idx == current_idx:
                        line_content += f"\033[92m{item}\033[0m{padding}"
                    else:
                        line_content += f"{item}{padding}"

            sys.stdout.write(f"{line_content}\033[K\n")

        if multi:
            sys.stdout.write(f"\033[90m(Espacio: sel, Enter: ok, A: todos, N: ninguno)\033[0m\033[K")
        else:
            sys.stdout.write(f"Opción (Número o flechas) [ {input_buffer} ]: \033[K")
        sys.stdout.flush()

    sys.stdout.write("\033[?25l")
    try:
        render_menu()
        while True:
            ch = getch()
            if ch == '\x03':
                raise KeyboardInterrupt
            elif ch in ('\r', '\n'):
                sys.stdout.write("\n")
                break
            elif ch == ' ':
                if multi:
                    if current_idx in selected_indices:
                        selected_indices.remove(current_idx)
                    else:
                        selected_indices.add(current_idx)
            elif ch in ('a', 'A'):
                if multi:
                    selected_indices = set(range(len(options)))
            elif ch in ('n', 'N'):
                if multi:
                    selected_indices.clear()
            elif ch == '\x1b[A':
                current_idx = (current_idx - 1) % len(options)
                input_buffer = ""
            elif ch == '\x1b[B':
                current_idx = (current_idx + 1) % len(options)
                input_buffer = ""
            elif ch == '\x1b[C':
                current_idx = (current_idx + num_rows) % len(options)
                input_buffer = ""
            elif ch == '\x1b[D':
                current_idx = (current_idx - num_rows) % len(options)
                input_buffer = ""
            elif ch in ('\x7f', '\b'):
                input_buffer = input_buffer[:-1]
                if input_buffer:
                    try:
                        num_val = int(input_buffer)
                        if 1 <= num_val <= len(options):
                            current_idx = num_val - 1
                    except ValueError:
                        pass
            elif len(ch) == 1 and ch.isdigit():
                new_buffer = input_buffer + ch
                try:
                    num_val = int(new_buffer)
                    if 1 <= num_val <= len(options):
                        input_buffer = new_buffer
                        current_idx = num_val - 1
                    else:
                        num_val = int(ch)
                        if 1 <= num_val <= len(options):
                            input_buffer = ch
                            current_idx = num_val - 1
                except ValueError:
                    pass

            sys.stdout.write(f"\033[{lines_to_clear}F")
            render_menu()

        sys.stdout.write(f"\033[{lines_to_clear}A")
        for _ in range(lines_to_clear + 1):
            sys.stdout.write("\033[K\n")
        sys.stdout.write(f"\033[{lines_to_clear + 1}F")

    except (Exception, KeyboardInterrupt):
        sys.stdout.write("\n\033[?25hOperación cancelada.\n")
        sys.exit(0)
    finally:
        sys.stdout.write("\033[?25h")

    if multi:
        return [options[i][1] for i in sorted(list(selected_indices))]
    return options[current_idx][1]
