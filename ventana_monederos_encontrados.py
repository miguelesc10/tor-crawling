import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox

'''
* CLASE: VentanaMonederosEncontrados
* DESCRIPCIÓN: Clase que modela las características de la ventana de monederos Bitcoin encontrados
               tras llevarse a cabo el rastreo en TOR.
'''
class VentanaMonederosEncontrados(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.resultados_crawler = {}
        self.tree_resultados = None

        # Configuración de la vista jerárquica tipo árbol de los monederos encontrados
        estilo = ttk.Style()
        estilo.configure("Treeview", font=("Arial", 13))
        estilo.configure("Treeview.Heading", font=("Arial", 14, "bold"))

        # Encabezado de la ventana
        frame_encabezado = ctk.CTkFrame(self)
        frame_encabezado.pack(fill="x", padx=20, pady=(20, 0))

        # Cuando es pulsado, el botón de retroceso muestra la ventana de parametrización de la búsqueda del crawler
        boton_atras = ctk.CTkButton(frame_encabezado, text="Atrás", width=80, font=("Arial", 20, "bold"),
                                    command=lambda: self.controller.mostrar_ventana("VentanaCrawler"))
        boton_atras.pack(side="left", padx=(10, 20), pady=10)

        self.label_titulo = ctk.CTkLabel(frame_encabezado, text="Monederos Bitcoin encontrados",
                                         font=ctk.CTkFont(size=30, weight="bold"))
        
        self.label_titulo.pack(side="left", pady=10)

        # Marco y árbol para los resultados del rastreo
        frame_tabla_urls_monederos = ctk.CTkFrame(self)
        frame_tabla_urls_monederos.pack(expand=True, fill="both", padx=20, pady=20)
        self.tree_resultados = ttk.Treeview(frame_tabla_urls_monederos, show="tree", selectmode="browse")

        # Barra de desplazamiento
        scrollbar = tk.Scrollbar(frame_tabla_urls_monederos, orient="vertical", command=self.tree_resultados.yview)
        self.tree_resultados.configure(yscrollcommand=scrollbar.set)

        self.tree_resultados.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Doble click sobre elemento del árbol
        self.tree_resultados.bind("<Double-1>", self.doble_click)
    
    '''
    * FUNCIÓN: set_resultados_busqueda
    * DESCRIPCIÓN: Inserta los resultados del rastreo (monederos Bitcoin y las URL donde han sido encontrados)
                   en el árbol de resultados de la ventana.
    * ARGS_IN:
        - resultados_dict: Diccionario con los resultados. Clave: URL. Valor: Lista de monederos Bitcoin.
    * ARGS_OUT:
        - N/A
    '''
    def set_resultados_busqueda(self, resultados_dict):
        self.resultados_crawler = resultados_dict

        # Limpiar resultados de búsquedas anteriores
        for i in self.tree_resultados.get_children():
            self.tree_resultados.delete(i)

        # Insertar nodos padre (URLs) y nodos hijo (monederos encontrados en cada URL)
        # Se realiza distinción entre ambas tipologías para la funcionalidad del doble click
        for url, lista_monederos in self.resultados_crawler.items():
            parent_id = self.tree_resultados.insert('', tk.END, text=url, tags=('fila_url',))
            
            for monedero in lista_monederos:
                self.tree_resultados.insert(parent_id, tk.END, text=monedero, tags=('fila_monedero', monedero))

    '''
    * FUNCIÓN: doble_click
    * DESCRIPCIÓN: Muestra la ventana de transacciones del monedero doblemente pulsado por el usuario.
    * ARGS_IN:
        - event: Evento capturado en la ventana.
    * ARGS_OUT:
        - N/A
    '''
    def doble_click(self, event):
        item_id = self.tree_resultados.identify_row(event.y)
        if not item_id:
            return

        # Se obtiene el tipo de fila del árbol que ha sido pulsada doblemente
        tags = self.tree_resultados.item(item_id, 'tags')

        # Si es una fila monedero, se obtiene la dirección del monedero
        if 'fila_monedero' in tags:
            direccion_seleccionada = self.tree_resultados.item(item_id, 'text')

            if direccion_seleccionada:
                # Se muestra la ventana de transacciones del monedero Bitcoin indicado
                self.controller.mostrar_ventana("VentanaTransacciones", direccion_monedero=direccion_seleccionada)
