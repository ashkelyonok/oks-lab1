from src.ports_core import PortsCore, PortException
from tkinter import ttk
import tkinter as tk

class App:
    def __init__(self):
        self.__ports_core = PortsCore()
        self.__root = tk.Tk()
        self.__root.geometry("300x400")
        self.__root.resizable(False, False)
        self.__root.title("COM-sender")
        self.__root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.current_frame = None
        self.receiving_text_widget = None
        self.receiving_device = None

        self.main_frame = tk.Frame(self.__root)
        self.main_frame.pack(fill="both", expand=True)

    def start(self):
        self.render_main_menu()
        self.__root.mainloop()

    def clear_frame(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = tk.Frame(self.main_frame)
        self.current_frame.pack(fill="both", expand=True, padx=10, pady=10)

    def create_back_button(self):
        back_button = tk.Button(self.current_frame, text="Back",
                                command=self.render_main_menu)
        back_button.pack(anchor="nw", pady=5)

    def render_main_menu(self):
        self.clear_frame()

        title_label = tk.Label(
            self.current_frame,
            text="COM-Sender",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=20)

        buttons_info = [
            ("Choose ports", self.render_select_ports_window),
            ("Write in port 1_1", lambda: self.render_send_window(1)),
            ("Write in port 2_2", lambda: self.render_send_window(2)),
            ("Read from port 1_2", lambda: self.render_receive_window(1)),
            ("Read from port 2_1", lambda: self.render_receive_window(2)),
            ("Change ports params", self.render_params_window),
            ("Ports info", self.render_info_window)
        ]

        for text, command in buttons_info:
            button = tk.Button(
                self.current_frame,
                text=text,
                command=command,
                width=20,
                height=2
            )
            button.pack(pady=1)

    def render_select_ports_window(self, device_number: int = None):
        self.clear_frame()
        self.create_back_button()

        title_label = tk.Label(
            self.current_frame,
            text="Choose active ports",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        available_ports: list[str] = self.__ports_core.get_available_ports()

        port_vars: dict = {}
        port_combos: dict = {}

        port_configs = [
            ("Port 1_1", 1),
            ("Port 1_2", 2),
            ("Port 2_1", 3),
            ("Port 2_2", 4)
        ]

        for port_name, port_num in port_configs:
            frame = tk.Frame(self.current_frame)
            frame.pack(fill="x", pady=5)

            label = tk.Label(frame, text=port_name, width=10)
            label.pack(side="left")

            var = tk.StringVar()
            combo = ttk.Combobox(frame, textvariable=var, values=available_ports, state="readonly")
            combo.pack(side="left", fill="x", expand=True, padx=5)

            port_vars[port_num] = var
            port_combos[port_num] = combo

        error_label = tk.Label(self.current_frame, text="", fg="red")
        error_label.pack(pady=5)

        def apply_selection():
            selected_ports = {}
            error_messages = []

            for port_num, var in port_vars.items():
                port_name = var.get()
                if port_name:
                    if port_name in selected_ports.values():
                        error_messages.append(f"Port {port_name} selected multiple times")
                    selected_ports[port_num] = port_name

            if error_messages:
                error_label.config(text="\n".join(error_messages))
                return

            for port_num, port_name in selected_ports.items():
                try:
                    port = self.__ports_core.create_port(port_name)
                    self.__ports_core.set_port(port, port_num)
                except PortException as e:
                    error_messages.append(f"Error with {port_name}: {e.message}")

            if error_messages:
                error_label.config(text="\n".join(error_messages))
            else:
                error_label.config(text="Ports configured successfully!", fg="green")

        apply_button = tk.Button(self.current_frame, text="Select", command=apply_selection)
        apply_button.pack(pady=10)

    def render_send_window(self, device_number: int):
        self.clear_frame()
        self.create_back_button()

        title_text = f"Write to port {1 if device_number == 1 else 2}_{1 if device_number == 1 else 2}"
        title_label = tk.Label(
            self.current_frame,
            text=title_text,
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        text_widget = tk.Text(self.current_frame, height=10, width=60)
        text_widget.pack(pady=10, fill="both", expand=True)

        status_label = tk.Label(self.current_frame, text="", fg="green")
        status_label.pack(pady=5)

        def send_message():
            message = text_widget.get("1.0", tk.END).strip()
            if not message:
                status_label.config(text="Message is empty!", fg="red")
                return

            try:
                sent_count = self.__ports_core.send_message(device_number, message.encode())
                status_label.config(text=f"Sent {sent_count} characters successfully!", fg="green")
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", fg="red")

        send_button = tk.Button(
            self.current_frame,
            text="Send",
            command=send_message, width=20
        )
        send_button.pack(pady=10)

    def render_receive_window(self, device_number: int):
        self.clear_frame()
        self.create_back_button()

        title_text = f"Read from port {1 if device_number == 1 else 2}_{2 if device_number == 1 else 1}"
        title_label = tk.Label(
            self.current_frame,
            text=title_text,
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        text_widget = tk.Text(self.current_frame, height=10, width=60)
        text_widget.pack(pady=10, fill="both", expand=True)
        self.receiving_text_widget = text_widget
        self.receiving_device = device_number

        status_label = tk.Label(self.current_frame, text="Not receiving", fg="gray")
        status_label.pack(pady=5)

        def emit_received_wrapper(message: bytes, bytes_count: int):
            def update_text():
                text_widget.delete("1.0", tk.END)
                text_widget.insert("1.0", message.decode(errors='ignore'))
                status_label.config(text=f"Received {bytes_count} bytes", fg="green")

            self.__root.after(500, update_text)

        self.__ports_core.emit_received = emit_received_wrapper

        def start_receiving():
            try:
                self.__ports_core.start_receiving(device_number)
                status_label.config(text="Receiving...", fg="blue")
                start_button.config(state="disabled")
                stop_button.config(state="normal")
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", fg="red")

        def stop_receiving():
            try:
                self.__ports_core.end_receiving()
                status_label.config(text="Stopped receiving", fg="gray")
                start_button.config(state="normal")
                stop_button.config(state="disabled")
            except Exception as e:
                status_label.config(text=f"Error: {str(e)}", fg="red")

        button_frame = tk.Frame(self.current_frame)
        button_frame.pack(pady=10)

        start_button = tk.Button(
            button_frame,
            text="Start Receiving",
            command=start_receiving
        )
        start_button.pack(side="left", padx=5)

        stop_button = tk.Button(
            button_frame,
            text="Stop Receiving",
            command=stop_receiving,
            state="disabled"
        )
        stop_button.pack(side="left", padx=5)

    def render_info_window(self):
        """Окно информации о портах"""
        self.clear_frame()
        self.create_back_button()

        title_label = tk.Label(
            self.current_frame,
            text="Ports Information",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        # Текстовое поле для информации
        info_text = tk.Text(self.current_frame, height=15, width=60)
        info_text.pack(pady=10, fill="both", expand=True)

        def update_info():
            """Обновляет информацию о портах"""
            try:
                info = self.__ports_core.print_ports_info()
                info_text.delete("1.0", tk.END)
                info_text.insert("1.0", info)
            except Exception as e:
                info_text.delete("1.0", tk.END)
                info_text.insert("1.0", f"Error getting port info: {str(e)}")

        update_info()

        refresh_button = tk.Button(
            self.current_frame,
            text="Refresh",
            command=update_info
        )
        refresh_button.pack(pady=5)

    def render_params_window(self):
        """Окно изменения параметров портов"""
        self.clear_frame()
        self.create_back_button()

        title_label = tk.Label(
            self.current_frame,
            text="Change Port Parameters",
            font=("Arial", 14, "bold")
        )
        title_label.pack(pady=10)

        # Baudrate selection
        baud_frame = tk.Frame(self.current_frame)
        baud_frame.pack(fill="x", pady=5)

        baud_label = tk.Label(baud_frame, text="Choose baudrate:", width=15)
        baud_label.pack(side="left")

        baud_var = tk.StringVar(value=str(self.__ports_core.baudrate))
        baud_combo = ttk.Combobox(
            baud_frame,
            textvariable=baud_var,
            values=["1000", "2000", "3000", "4000", "5000"],
            state="readonly", width=10)
        baud_combo.pack(side="left", padx=5)

        def apply_baudrate():
            """Применяет выбранный baudrate"""
            try:
                baudrate = int(baud_var.get())
                self.__ports_core.set_ports_params(baudrate=baudrate)
                baud_status.config(text="Baudrate applied successfully!", fg="green")
            except Exception as e:
                baud_status.config(text=f"Error: {str(e)}", fg="red")

        baud_button = tk.Button(baud_frame, text="Apply", command=apply_baudrate)
        baud_button.pack(side="left", padx=5)

        baud_status = tk.Label(self.current_frame, text="", fg="green")
        baud_status.pack(pady=2)

        # Timeout selection
        timeout_frame = tk.Frame(self.current_frame)
        timeout_frame.pack(fill="x", pady=5)

        timeout_label = tk.Label(timeout_frame, text="Choose timeout:", width=15)
        timeout_label.pack(side="left")

        timeout_var = tk.StringVar(value=str(self.__ports_core.timeout))
        timeout_combo = ttk.Combobox(
            timeout_frame, textvariable=timeout_var,
            values=["0.1", "0.2", "0.3", "0.4", "0.5"],
            state="readonly",
            width=10
        )
        timeout_combo.pack(side="left", padx=5)

        def apply_timeout():
            """Применяет выбранный timeout"""
            try:
                timeout = float(timeout_var.get())
                self.__ports_core.set_ports_params(timeout=timeout)
                timeout_status.config(text="Timeout applied successfully!", fg="green")
            except Exception as e:
                timeout_status.config(text=f"Error: {str(e)}", fg="red")

        timeout_button = tk.Button(timeout_frame, text="Apply", command=apply_timeout)
        timeout_button.pack(side="left", padx=5)

        timeout_status = tk.Label(self.current_frame, text="", fg="green")
        timeout_status.pack(pady=2)

    def on_closing(self):
        """Обработчик закрытия приложения"""
        try:
            # Останавливаем прием, если он активен
            if hasattr(self.__ports_core, 'is_receiving') and self.__ports_core.is_receiving:
                self.__ports_core.end_receiving()

            # Закрываем все порты
            self.__ports_core.close_active_ports()
        except:
            pass

        self.__root.destroy()
