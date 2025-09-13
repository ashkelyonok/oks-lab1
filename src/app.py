from src.ports_core import PortsCore, PortException
from tkinter import scrolledtext, ttk
import tkinter as tk

class App:
    def __init__(self):
        self.__ports_core = PortsCore()
        self.device_number = 1
        self.__root = tk.Tk()
        self.__root.geometry("1000x700")
        self.__root.resizable(False, False)
        self.__root.title("COM Port Terminal")
        self.__root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.tx_port = None  # For status
        self.rx_port = None
        self.portion_bytes = 0  # For RX portion (reset on pause)
        self.receiving_text_widget = None
        self.receiving_device = None
        self.ports_open = False

        # Auto-start integrated GUI (no menu)
        self.render_integrated_gui()
        # Auto-start RX for demo (modify for device)
        self.__ports_core.emit_received = self.emit_received_wrapper
        self.__root.after(100, self.check_portion_end)

    def render_integrated_gui(self):
        main_container = tk.Frame(self.__root)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Top: Port selection (restored Combobox original logic)
        control_frame = tk.LabelFrame(main_container, text="Port Selection & Control", font=('Arial', 12, 'bold'))
        control_frame.pack(fill='x', pady=5)
        # Available ports (original)
        available_ports = self.__ports_core.get_available_ports()
        # TX Combobox (original style, not spin)
        tx_frame = tk.Frame(control_frame)
        tx_frame.pack(side='left', padx=10)
        tk.Label(tx_frame, text="TX Port (Sender):").pack(side='left')
        self.tx_var = tk.StringVar()
        self.tx_combo = ttk.Combobox(tx_frame, textvariable=self.tx_var, values=available_ports, state="readonly", width=15)
        self.tx_combo.pack(side='left')
        # Dynamic RX Combobox (read-only, auto from TX)
        rx_frame = tk.Frame(control_frame)
        rx_frame.pack(side='left', padx=10)
        tk.Label(rx_frame, text="RX Port (Receiver, auto):").pack(side='left')
        self.rx_var = tk.StringVar(value="Select TX for auto RX")
        self.rx_combo = ttk.Combobox(rx_frame, textvariable=self.rx_var, values=available_ports, state="readonly", width=15)  # Read-only
        self.rx_combo.pack(side='left')
        # ### NEW: Hardcode mapping TX to RX (7→10, 8→9)
        tx_to_rx = {'7': '10', '8': '9'}  # Dict for krest
        def on_tx_change(*args):
            tx_selected = self.tx_var.get()
            if tx_selected and tx_selected.startswith('COM'):
                try:
                    tx_num = tx_selected.replace('COM', '')
                    if tx_num in tx_to_rx:
                        rx_num = tx_to_rx[tx_num]
                        rx_selected = f"COM{rx_num}"
                        if rx_selected in available_ports:
                            self.rx_var.set(rx_selected)
                            self.control_error.config(text=f"Auto RX set to {rx_selected}", fg="green")
                        else:
                            self.rx_var.set("RX not available")
                            self.control_error.config(text=f"Warning: RX {rx_selected} not in VSPE", fg="orange")
                    else:
                        self.rx_var.set("No auto for this TX")
                        self.control_error.config(text="Only COM7/COM8 auto-pair", fg="orange")
                except ValueError:
                    self.control_error.config(text="Invalid TX", fg="red")
            else:
                self.rx_var.set("Select TX first")
        self.tx_var.trace('w', on_tx_change)
        # Baud (custom input: state="normal" for edit)
        baud_frame = tk.Frame(control_frame)
        baud_frame.pack(side='left', padx=10)
        tk.Label(baud_frame, text="Baudrate:").pack(side='left')
        self.baud_var = tk.StringVar(value=str(self.__ports_core.baudrate))
        self.baud_combo = ttk.Combobox(baud_frame, textvariable=self.baud_var, values=["9600", "19200", "38400", "57600", "115200"], state="normal", width=10)  # ### FIX4: state="normal" for custom input
        self.baud_combo.pack(side='left')
        # Timeout
        timeout_frame = tk.Frame(control_frame)
        timeout_frame.pack(side='left', padx=10)
        tk.Label(timeout_frame, text="Timeout (s):").pack(side='left')
        self.timeout_var = tk.StringVar(value=str(self.__ports_core.timeout))
        self.timeout_combo = ttk.Combobox(timeout_frame, textvariable=self.timeout_var, values=["0.1", "0.2", "0.3", "0.4", "0.5", "1.0"], state="normal", width=10)  # Allow custom
        self.timeout_combo.pack(side='left')
        # Toggle button (Open/Close)
        self.open_btn = tk.Button(control_frame, text="Open Ports", command=self.toggle_ports)
        self.open_btn.pack(side='right', padx=10)
        self.control_error = tk.Label(control_frame, text="Select TX for auto RX", fg="blue")
        self.control_error.pack(side='right', padx=5)

        # Status (right, as before)
        status_frame = tk.LabelFrame(main_container, text="Status", font=('Arial', 12, 'bold'), width=200)
        status_frame.pack(side='right', fill='y', padx=10, pady=5)
        status_frame.pack_propagate(False)
        self.status_label = tk.Label(status_frame, text="TX Port: N/A\nRX Port: N/A", fg="blue", justify='left')
        self.status_label.pack(pady=10)

        # Input (TX)
        input_frame = tk.LabelFrame(main_container, text="Input (TX)", font=('Arial', 12, 'bold'))
        input_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        self.input_text = tk.Text(input_frame, height=10, width=40)
        self.input_text.pack(pady=10, fill="both", expand=True)
        self.input_status = tk.Label(input_frame, text="", fg="green")
        self.input_status.pack(pady=5)

        def send_message():
            if not self.ports_open:
                self.input_status.config(text="Open ports first!", fg="red")
                return
            message = self.input_text.get("1.0", tk.END).strip()
            if not message:
                self.input_status.config(text="Message is empty!", fg="red")
                return
            try:
                msg_bytes = message.encode('ascii', errors='ignore')
                sent_count = self.__ports_core.send_message(self.device_number, msg_bytes)
                self.input_status.config(text="")  # Очищаем перед обновлением
                self.input_status.config(text=f"Sent {sent_count} bytes (portion)!", fg="green")
                self.input_text.delete("1.0", tk.END)
                self.input_text.focus()
                self.output_text.insert(tk.END, "\n")
                self.output_text.insert(tk.END, message)
                self.debug_text.insert(tk.END, f"Sent {sent_count} bytes: {message}\n")
                self.debug_text.see(tk.END)
            except Exception as e:
                self.input_status.config(text=f"Error: {str(e)}", fg="red")
                self.debug_text.insert(tk.END, f"Send error: {e}\n")

        def on_enter_key(event):
            send_message()
            return "break"

        self.input_text.bind("<Return>", on_enter_key)
        self.input_text.bind("<Control-Return>", lambda e: None)
        send_btn = tk.Button(input_frame, text="Send", command=send_message)
        send_btn.pack(pady=5)

        # Output (RX, initial "Not receiving")
        output_frame = tk.LabelFrame(main_container, text="Output (RX)", font=('Arial', 12, 'bold'))
        output_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10, width=40)
        self.output_text.pack(pady=10, fill="both", expand=True)
        self.output_status = tk.Label(output_frame, text="Not receiving", fg="gray")  ### FIX3: Initial not receiving
        self.output_status.pack(pady=5)

        # Debug
        debug_frame = tk.LabelFrame(self.__root, text="Debug Log", font=('Arial', 12, 'bold'))
        debug_frame.pack(fill='x', padx=10, pady=5)
        self.debug_text = scrolledtext.ScrolledText(debug_frame, height=5, width=100, state='normal')
        self.debug_text.pack(pady=5, fill='x')
        self.debug_text.insert(tk.END, "Debug started. Select TX for auto RX, then Open Ports.\n")

        self.update_status()

    def toggle_ports(self):
        """Toggle open/close (### FIX3: Open starts RX)"""
        if not self.ports_open:
            # Open
            tx_selected = self.tx_var.get()
            rx_selected = self.rx_var.get()
            if not tx_selected or rx_selected == "Select TX first" or not rx_selected.startswith('COM'):
                self.control_error.config(text="Select valid TX/RX pair!", fg="red")
                return
            try:
                baud = int(self.baud_var.get())
                timeout = float(self.timeout_var.get())
                # Create/set TX (slot 1)
                tx_port = self.__ports_core.create_port(tx_selected)
                self.__ports_core.set_port(tx_port, 1)
                # Create/set RX (slot 2)
                rx_port = self.__ports_core.create_port(rx_selected)
                self.__ports_core.set_port(rx_port, 2)
                # Set params
                self.__ports_core.set_ports_params(baudrate=baud, timeout=timeout)
                self.tx_port = tx_selected
                self.rx_port = rx_selected
                self.ports_open = True
                self.open_btn.config(text="Close Ports")
                self.control_error.config(text=f"Ports opened: TX {tx_selected}, RX {rx_selected}", fg="green")
                self.debug_text.insert(tk.END, f"Ports opened TX {tx_selected} RX {rx_selected} baud {baud} timeout {timeout}\n")
                self.update_status()
                # ### FIX3/FIX4: Start RX after open
                self.start_receiving(self.device_number)
                self.output_status.config(text="Receiving...", fg="blue")
            except PortException as e:
                self.control_error.config(text=f"Error: {e.message}", fg="red")
                self.debug_text.insert(tk.END, f"Open error: {e.message}\n")
        else:
            # Close
            try:
                self.__ports_core.end_receiving()
                self.__ports_core.close_active_ports()
                self.ports_open = False
                self.open_btn.config(text="Open Ports")
                self.tx_port = None
                self.rx_port = None
                self.portion_bytes = 0
                self.output_text.delete("1.0", tk.END)
                self.output_status.config(text="Not receiving", fg="gray")  # Информируем о закрытии
                self.input_status.config(text="Ports closed - ready to open")  # Информируем о состоянии отправки
                self.current_portion = b""  # Сбрасываем буфер
                self.control_error.config(text="Ports closed - no sending/receiving", fg="orange")
                self.debug_text.insert(tk.END, "Ports closed, RX stopped.\n")
                self.update_status()  # Обновляем статусное окно
            except Exception as e:
                self.control_error.config(text=f"Close error: {str(e)}", fg="red")

    def update_status(self):
        tx_str = self.tx_port if self.tx_port else "N/A"
        rx_str = self.rx_port if self.rx_port else "N/A"
        self.status_label.config(text=f"TX Port: {tx_str}\nRX Port: {rx_str}")

    def start_receiving(self, device_number):
        try:
            self.__ports_core.start_receiving(device_number)
            self.output_status.config(text="Receiving...", fg="blue")
            self.debug_text.insert(tk.END, f"RX started for device {device_number}\n")
        except Exception as e:
            self.output_status.config(text=f"Error: {str(e)}", fg="red")
            self.debug_text.insert(tk.END, f"RX start error: {e}\n")

    def check_portion_end(self):
        if hasattr(self, 'current_portion') and self.current_portion and self.ports_open:
            # Если данные накопились, но новых не поступает (условно после паузы)
            self.output_text.insert(tk.END, "\n")  # Новая строка
            self.output_text.insert(tk.END, self.current_portion.decode(errors='ignore'))
            self.output_status.config(text=f"Received {self.portion_bytes} bytes in portion", fg="green")
            self.update_status()
            self.current_portion = b""
            self.portion_bytes = 0
            self.__root.after(2000, lambda: self.output_status.config(text="Receiving...", fg="blue") if self.ports_open else None)
            
        if self.ports_open:
            self.__root.after(100, self.check_portion_end)

    def emit_received_wrapper(self, message: bytes, bytes_count: int):
        """### FIX4: Debug emit, incremental for sync"""
        def update_output():
            if not hasattr(self, 'current_portion'):
                self.current_portion = b""  # Инициализируем буфер, если его нет
            self.debug_text.insert(tk.END, f"Emit called with {len(message)} bytes (portion {bytes_count})\n")

            if bytes_count > 0:  # Накопление байтов
                self.current_portion += message  # Добавляем текущий байт
                self.portion_bytes += bytes_count  # Увеличиваем счетчик для текущей порции
            else:  # Предполагаем конец порции (например, после паузы, но без явного сигнала)
                if self.current_portion:  # Если есть накопленные данные
                    self.output_text.insert(tk.END, "\n")  # Новая строка перед порцией
                    self.output_text.insert(tk.END, self.current_portion.decode(errors='ignore'))  # Отображаем всю порцию
                    self.output_status.config(text=f"Received {self.portion_bytes} bytes in portion", fg="green")
                    self.update_status()
                    self.current_portion = b""  # Сбрасываем буфер
                    self.portion_bytes = 0  # Сбрасываем счетчик
                    self.__root.after(2000, lambda: self.output_status.config(text="Receiving...", fg="blue") if self.ports_open else None)
                

            self.output_text.see(tk.END)
            self.debug_text.see(tk.END)

        self.__root.after(10, update_output)

    def on_closing(self):
        try:
            if self.ports_open:
                self.toggle_ports()  # Close on exit
            self.__root.destroy()
        except Exception as e:
            pass

    def start(self):
        self.__root.mainloop()