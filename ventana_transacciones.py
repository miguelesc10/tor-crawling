import customtkinter as ctk
from tkinter import ttk
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
from blockcypher import get_address_full

'''
* CLASE: VentanaTransacciones
* DESCRIPCIÓN: Clase que modela las características de la ventana de transacciones de un monedero Bitcoin.
'''
class VentanaTransacciones(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.monedero = None
        self.label_titulo = None
        self.tabla = None

        # Encabezado de la ventana
        frame_encabezado = ctk.CTkFrame(self)
        frame_encabezado.pack(fill="x", padx=20, pady=(20, 0))
        
        # Cuando es pulsado, el botón de retroceso muestra la ventana de resultados del rastreo
        boton_atras = ctk.CTkButton(frame_encabezado, text="Atrás", width=80, font=("Arial", 20, "bold"),command=lambda: self.controller.mostrar_ventana("VentanaMonederosEncontrados"))
        boton_atras.pack(side="left", padx=(10, 20), pady=10)

        self.label_titulo = ctk.CTkLabel(frame_encabezado, text="Transacciones de la dirección: ",
                                          font=ctk.CTkFont(size=30, weight="bold"))
        self.label_titulo.pack(side="left", pady=10)

        # Cuando es pulsado, el botón de exportación desencadena la función que exporta los resultados a un archivo local
        boton_exportar = ctk.CTkButton(frame_encabezado, text="Exportar a Excel", font=("Arial", 20, "bold"), command=self.exportar_excel)
        boton_exportar.pack(side="right", padx=10)

        # Marco para la tabla de transacciones
        frame_tabla = ctk.CTkFrame(self)
        frame_tabla.pack(expand=True, fill="both", padx=20, pady=20)

        # Columnas a mostrar en la tabla de transacciones
        columnas = ("hash", "valor_neto", "comision", "num_bloque", "fecha", "confirmaciones","tipo" ,"emisores", "receptores")
        self.tabla = ttk.Treeview(frame_tabla, columns=columnas, show="headings")

        columnas_ancho_corto = ["valor_neto", "comision", "num_bloque","fecha","confirmaciones", "tipo"]

        # Configuración de ancho de las columnas
        for col in columnas:
            self.tabla.heading(col, text=col.replace('_', ' ').title())
            if col in columnas_ancho_corto:
                self.tabla.column(col, width=7)
            else:
                self.tabla.column(col, width=290)

        # Barra de desplazamiento
        barra_desplazamiento = tk.Scrollbar(frame_tabla, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra_desplazamiento.set)

        self.tabla.pack(side="left", fill="both", expand=True)
        barra_desplazamiento.pack(side="right", fill="y")

    '''
    * FUNCIÓN: set_monedero
    * DESCRIPCIÓN: Establece el objeto instanciado de la clase MonederoBitcoin correspondiente al monedero a visualizar en 
                   la ventana, modifica el título de la ventana con su información y llama a la función que inserta la 
                   información de las transacciones en la ventana.
    * ARGS_IN:
        - monedero: Objeto de la clase MonederoBitcoin correspondiente al monedero a visualizar en la ventana.
    * ARGS_OUT:
        - N/A
    '''    
    def set_monedero(self, monedero):
        self.monedero = MonederoBitcoin(monedero)
        self.label_titulo.configure(text=f"Transacciones de la dirección: {self.monedero.direccion} (Balance: {self.monedero.balance} BTC)")
        self.set_tabla()

    '''
    * FUNCIÓN: set_tabla
    * DESCRIPCIÓN: Inserta la información de las transacciones del monedero Bitcoin en la tabla de visualización de la ventana.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''    
    def set_tabla(self):
        # Limpiar la tabla antes de insertar nuevos datos
        for i in self.tabla.get_children():
            self.tabla.delete(i)

        if not self.monedero or not self.monedero.transacciones_confirmadas:
            self.tabla.insert('', tk.END, values=("No hay transacciones disponibles para esta dirección.", "", "", "", "", "", "", "", ""))
            return

        # Formato de la información a mostrar de los emisores y receptores de cada transacción
        for tx in self.monedero.transacciones_confirmadas:
            emisores_str = ', '.join(f"{direccion}: {valor} BTC" for e in tx.emisores for direccion, valor in zip(e['direcciones'], [e['valor']]))
            receptores_str = ', '.join(f"{direccion}: {valor} BTC" for r in tx.receptores for direccion, valor in zip(r['direcciones'], [r['valor']]))
            
            self.tabla.insert('', tk.END, values=(tx.hash, tx.valor_neto, tx.comision, tx.num_bloque,tx.fecha_confirmacion.strftime("%Y-%m-%d %H:%M"),
                tx.num_confirmaciones,tx.tipo,emisores_str,receptores_str))
    
    '''
    * FUNCIÓN: exportar_excel
    * DESCRIPCIÓN: Almacena la información de las transacciones del monedero Bitcoin en un archivo Excel local.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def exportar_excel(self):
        datos_excel = []
        # Formato de la información a mostrar de los emisores y receptores de cada transacción
        for tx in self.monedero.transacciones_confirmadas:
            emisores_str = ', '.join(f"{direccion}: {valor} BTC" for e in tx.emisores for direccion, valor in zip(e['direcciones'], [e['valor']]))
            receptores_str = ', '.join(f"{direccion}: {valor} BTC" for r in tx.receptores for direccion, valor in zip(r['direcciones'], [r['valor']]))
            
            datos_excel.append({"Hash": tx.hash, "Valor Neto (BTC)": tx.valor_neto, "Comisión": tx.comision,
                "Bloque": tx.num_bloque, "Fecha": tx.fecha_confirmacion.strftime("%Y-%m-%d %H:%M"), "Confirmaciones": tx.num_confirmaciones,
                "Emisores": emisores_str, "Receptores": receptores_str})

        # Creación del DataFrame que almcacena la información de la tabla a exportar
        df = pd.DataFrame(datos_excel)
        
        # Ventana de diálogo de configuración del archivo a crear
        # Por defecto se establece la dirección del monedero como nombre del fichero
        archivo = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")],
            title="Guardar como", initialfile=f"{self.monedero.direccion}.xlsx")

        if archivo:
            df.to_excel(archivo, index=False)
            messagebox.showinfo("Finalizado", "Se han exportado las transacciones correctamente")

'''
* CLASE: TransaccionBitcoin
* DESCRIPCIÓN: Clase que modela las transacciones de Bitcoin.
'''
class TransaccionBitcoin():
    def __init__(self, hash, valor_neto, comision, num_bloque, fecha_confirmacion, num_confirmaciones,
                 tipo, emisores, receptores):
        self.hash = hash
        self.valor_neto = valor_neto
        self.comision = comision
        self.num_bloque = num_bloque
        self.fecha_confirmacion = fecha_confirmacion
        self.num_confirmaciones = num_confirmaciones
        self.tipo = tipo
        self.emisores = emisores
        self.receptores = receptores

'''
* CLASE: TransaccionBitcoin
* DESCRIPCIÓN: Clase que modela los monederos Bitcoin.
'''
class MonederoBitcoin():
    
    def __init__(self, direccion):
        self.direccion = direccion
        
        # Obtención de la información del monedero a través de la API Blockcypher
        self.datosapi = get_address_full(direccion)

        # Conversión de la información financiera de satoshis a BTC
        self.balance = self.datosapi["balance"]/100000000
        self.total_recibido = self.datosapi["total_received"]/100000000
        self.total_enviado = self.datosapi["total_sent"]/100000000
        self.num_transacciones_confirmadas = self.datosapi["n_tx"]

        self.balance_no_confirmado = self.datosapi["unconfirmed_balance"]/100000000
        self.num_transacciones_no_confirmadas = self.datosapi["unconfirmed_n_tx"]

        # Lista que contiene objetos de tipo TransaccionBitcoin asociados a los movimientos confirmados en los que se identifica al monedero
        self.transacciones_confirmadas = []

        if self.num_transacciones_confirmadas > 0:
            for transaccion in self.datosapi["txs"]:
                # Para cada transacción, estudiamos si el monedero ha participado como emisor, receptor o ambos
                emisores = [{'direcciones': e['addresses'] or [], 'valor': e['output_value']/100000000} for e in transaccion["inputs"]]
                receptores = [{'direcciones': r['addresses'] or [], 'valor': r['value']/100000000} for r in transaccion["outputs"]]
                
                en_emisores = any(self.direccion in e['direcciones'] for e in emisores)
                en_receptores = any(self.direccion in r['direcciones'] for r in receptores)
    
                if en_emisores and en_receptores:
                    tipo = "Emisor/Receptor"
                elif en_emisores:
                    tipo = "Emisor"
                elif en_receptores:
                    tipo = "Receptor"
                else:
                    tipo = "Revisar en la cadena"

                self.transacciones_confirmadas.append(TransaccionBitcoin(hash = transaccion["hash"], valor_neto = transaccion["total"], 
                                                                  comision = transaccion["fees"], 
                                                                  num_bloque = transaccion["block_height"],
                                                                  fecha_confirmacion = transaccion["confirmed"],
                                                                  num_confirmaciones= transaccion["confirmations"], 
                                                                  tipo = tipo, emisores = emisores, receptores = receptores))

