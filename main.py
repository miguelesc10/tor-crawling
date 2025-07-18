from ventana_inicio import VentanaInicio
from ventana_crawler import VentanaCrawler
from ventana_monederos_encontrados import VentanaMonederosEncontrados
from ventana_transacciones import VentanaTransacciones
import customtkinter as ctk

'''
* CLASE: App
* DESCRIPCIÓN: Clase principal de la aplicación que incorpora sus principales parámetros gráficos.
'''
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("TOR crawling")
        self.geometry("1920x1080")

        self.container = ctk.CTkFrame(self)
        self.container.pack(side="top", fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        
        self.ventanas = {}
        self.crear_ventanas()
        self.mostrar_ventana("VentanaInicio")
    
    '''
    * FUNCIÓN: crear_ventanas
    * DESCRIPCIÓN: Instancia objetos de las distintas clases de ventanas de la aplicación.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def crear_ventanas(self):
        for F in (VentanaInicio, VentanaCrawler, VentanaMonederosEncontrados,VentanaTransacciones):
            nombre_ventana = F.__name__
            ventana = F(parent=self.container, controller=self)
            self.ventanas[nombre_ventana] = ventana
            ventana.grid(row=0, column=0, sticky="nsew")
            
    '''
    * FUNCIÓN: mostrar_ventana
    * DESCRIPCIÓN: Muestra la ventana indicada como parámetro.
    * ARGS_IN:
        - nombre_ventana: String del nombre de la ventana a mostrar.
        - resultados: Diccionario de resultados del rastreo (Opcional).
        - direccion_monedero: Dirección del monedero Bitcoin (Opcional).
    * ARGS_OUT:
        - N/A
    '''
    def mostrar_ventana(self, nombre_ventana, resultados=None, direccion_monedero=None):
        ventana = self.ventanas[nombre_ventana]
        
        if nombre_ventana == "VentanaMonederosEncontrados" and isinstance(ventana, VentanaMonederosEncontrados) and resultados is not None:
            ventana.set_resultados_busqueda(resultados)
        elif nombre_ventana == "VentanaTransacciones" and isinstance(ventana, VentanaTransacciones) and direccion_monedero is not None:
            ventana.set_monedero(direccion_monedero)
        
        ventana.tkraise()

if __name__ == "__main__":
    app = App()
    app.mainloop()