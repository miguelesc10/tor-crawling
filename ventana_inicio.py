import customtkinter as ctk
import tkinter as tk

'''
* CLASE: VentanaInicio
* DESCRIPCIÓN: Clase que modela las características de la ventana inicial de la aplicación.
'''
class VentanaInicio(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        label_titulo = ctk.CTkLabel(self, text="Búsqueda de monederos Bitcoin en TOR", font=("Arial", 40, "bold"))
        label_titulo.place(relx=0.5, rely=0.45, anchor=tk.CENTER)

        # Cuando es pulsado, el botón de inicio muestra la ventana de parametrización de la búsqueda del crawler
        boton_inicio = ctk.CTkButton(self, text="Inicio",font=("Arial", 20, "bold"), command=lambda: self.controller.mostrar_ventana("VentanaCrawler"))
        boton_inicio.place(relx=0.5, rely=0.55, anchor=tk.CENTER)
