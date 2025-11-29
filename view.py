import webview
import tkinter as tk

# --- Obtener resolución de pantalla ---
root = tk.Tk()
root.withdraw()

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()-80

# --- Ratio original: 1080x1920 ---
ratio = 1080 / 1920  # 0.5625

# --- Ajustar a la altura de la pantalla ---
target_height = screen_height
target_width = int(target_height * ratio)

# Si excede ancho de pantalla, ajustamos al ancho
if target_width > screen_width:
    target_width = screen_width
    target_height = int(target_width / ratio)

# --- Crear ventana WebView ---
webview.create_window(
    title='Game',
    url='http://127.0.0.1:8000/',
    width=target_width,
    height=target_height,
    resizable=True
)

webview.start()
