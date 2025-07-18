import sys
import customtkinter as ctk
from tkinter import messagebox
from threading import Thread, Event
import queue
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from bitcoinlib.keys import Address
from bitcoinlib.encoding import EncodingError
import time


'''
* CLASE: VentanaEmergenteProgreso
* DESCRIPCIÓN: Clase que modela las características de la ventana emergente mostrada durante el proceso de rastreo.
'''
class VentanaEmergenteProgreso(ctk.CTkToplevel):
    def __init__(self, master, num_min_monederos):
        super().__init__(master)
        
        # Referencia a la ventana principal para llamar a sus métodos
        self.controller = master 

        self.title("Rastreando...")
        self.geometry("650x250")
        # Llamar a la función que cancela el rastreo si se cierra desde la "X" superior la ventana
        self.protocol("WM_DELETE_WINDOW", self.cancelar_rastreo)

        self.label_estado = ctk.CTkLabel(self, text="Iniciando conexión con la red TOR", wraplength=450, font=("Arial", 15))
        self.label_estado.pack(pady=10, padx=10)

        # Barra de progreso de la ventana
        self.barra_progreso = ctk.CTkProgressBar(self, width=400)
        self.barra_progreso.set(0)
        self.barra_progreso.pack(pady=10, padx=10)
        
        # Etiqueta para mostrar el número de monederos encontrados durante el rastreo
        self.label_monederos_encontrados = ctk.CTkLabel(self, text=f"Monederos encontrados: 0 / {num_min_monederos}", font=("Arial", 14))
        self.label_monederos_encontrados.pack(pady=5, padx=10)

        # Cuando es pulsado, el botón de cancelar llama a la función que finaliza la ejecución del rastreo
        self.boton_cancelar = ctk.CTkButton(self, text="Cancelar", command=self.cancelar_rastreo, fg_color="red", hover_color="#C00000")
        self.boton_cancelar.pack(pady=10)

    '''
    * FUNCIÓN: actualizar_progreso
    * DESCRIPCIÓN: Actualiza la información para mostrar en la ventana emergente durante el proceso de rastreo.
    * ARGS_IN:
        - estado: texto del estado para mostrar en la ventana de progreso.
        - num_monederos_encontrados: número de monederos Bitcoin que se han encontrado hasta el momento.
        - num_min_monederos: número mínimo de monederos Bitcoin a encontrar solicitados por el usuario.
    * ARGS_OUT:
        - N/A
    '''
    def actualizar_progreso(self, estado, num_monederos_encontrados, num_min_monederos):
        self.label_estado.configure(text=estado)
        self.label_monederos_encontrados.configure(text=f"Monederos encontrados: {num_monederos_encontrados} / {num_min_monederos}")
        
        # Actualización de la barra de progreso
        if num_min_monederos > 0:
            progress_float = num_monederos_encontrados / num_min_monederos
            self.barra_progreso.set(progress_float)
        else:
            self.barra_progreso.set(0)
    
    '''
    * FUNCIÓN: cancelar_rastreo
    * DESCRIPCIÓN: Finaliza la ejecución del rastreo del crawler llamando a la correspondiente función de parada en el hilo.
                   Restablece los botones de la ventana emergente para posteriores ejecuciones.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def cancelar_rastreo(self):
        self.label_estado.configure(text="Cancelando rastreo. Esperando a que el hilo termine.")
        self.boton_cancelar.configure(state="disabled")
        self.controller.detener_crawler()
        
        
'''
* CLASE: HiloCrawler
* DESCRIPCIÓN: Clase que implementa el hilo de ejecución del proceso de rastreo de monederos Bitcoin en la red TOR.
'''
class HiloCrawler(Thread):
    def __init__(self, urls, num_min_monederos, cola_comunicacion, evento_parada):
        super().__init__(daemon=True)
        # Parámetros del crawler
        self.lista_urls_a_visitar = list(urls)
        self.num_min_monederos = num_min_monederos
        self.set_urls_visitadas = set()
        self.set_direcciones_bitcoin_encontradas = set()
        self.diccionario_url_direcciones_bitcoin = {}
        # Canales de comunicación con la rutina principal
        self.cola_comunicacion = cola_comunicacion
        self.evento_parada = evento_parada
        
        # Proxies para redirigir el tráfico a través del servicio TOR
        self.PROXIES = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}
        
        self.USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/115.0"
        
        # Expresiones regulares para localización de monederos Bitcoin en las páginas visitadas
        self.REGEX_BITCOIN = [re.compile(r"\b[1][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),  # P2PKH (empiezan por 1)
                              re.compile(r"\b[3][a-km-zA-HJ-NP-Z1-9]{25,34}\b"),  # P2SH (empiezan por 3)
                              re.compile(r"\bbc1q[ac-hj-np-z02-9]{39,59}\b"),     # Bech32 (empiezan por bc1q)
                              re.compile(r"\bbc1p[ac-hj-np-z02-9]{39,59}\b")]     # Bech32m (empiezan por bc1p)] 
    '''
    * FUNCIÓN: run
    * DESCRIPCIÓN: Rutina ejecutada por el hilo que implementa el rastreo en la red TOR.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def run(self):
        try:
            # Verificación de la conexión a la red TOR
            self.verificar_conexion_tor()

            # Bucle principal de rastreo
            while len(self.lista_urls_a_visitar) > 0 and len(self.set_direcciones_bitcoin_encontradas) < self.num_min_monederos:
                #  Comprobar si se ha solicitado detener el hilo
                if self.evento_parada.is_set():
                    # Se comunica a la rutina principal que se ha cancelado la ejecución
                    self.cola_comunicacion.put(("cancelado", "Cerrando hilo de rastreo"))
                    return

                url_actual = self.lista_urls_a_visitar.pop(0)
                if url_actual in self.set_urls_visitadas:
                    continue
                # Se comunica a la rutina principal la URL que se está procesando
                self.cola_comunicacion.put(("estado", f"Procesando: {url_actual}"))
                self.set_urls_visitadas.add(url_actual)

                # Se obtiene el HTML de la página visitada
                html = self.obtener_html(url_actual)
                if html:
                    # Se procesa el HTML para buscar monederos en el código y nuevos enlaces para visitar
                    set_direcciones_bitcoin_pagina_actual, set_nuevos_enlaces = self.procesar_y_extraer_enlaces(html, url_actual)
                    
                    if set_direcciones_bitcoin_pagina_actual:                     
                        # Se añaden el total de direcciones Bitcoin encontradas en la página al diccionario de resultados
                        self.diccionario_url_direcciones_bitcoin[url_actual] = list(set_direcciones_bitcoin_pagina_actual)
                        
                        # Si al menos una de los monederos no había sido rastreado previamente, se actualiza el
                        # el conjunto total de monederos encontrados en el rastreo y 
                        # la barra de progreso de la ventana de progreso de la rutina principal
                        if len(set_direcciones_bitcoin_pagina_actual-self.set_direcciones_bitcoin_encontradas) > 0:
                            self.set_direcciones_bitcoin_encontradas.update(set_direcciones_bitcoin_pagina_actual)
                            self.cola_comunicacion.put(("monedero_encontrado", len(self.set_direcciones_bitcoin_encontradas)))
                    
                    # Añadir los enlaces encontrados a la lista de URLs si no ha sido visitada
                    for enlace in set_nuevos_enlaces:
                        if enlace not in self.set_urls_visitadas and enlace not in self.lista_urls_a_visitar:
                            self.lista_urls_a_visitar.append(enlace)
                
                time.sleep(0.2)

            # Envío de resultados a la rutina principal de la aplicación
            self.cola_comunicacion.put(("terminado", self.diccionario_url_direcciones_bitcoin))

        except ConnectionError as e:
            self.cola_comunicacion.put(("error_conexion", str(e)))
        
        # Error genérico
        except Exception as e:
            self.cola_comunicacion.put(("error", str(e)))

    '''
    * FUNCIÓN: verificar_conexion_tor
    * DESCRIPCIÓN: Comprueba que el tráfico es cursado a través de la red TOR utilizando la API de comprobación
                   de TOR Project, que devuelve True si la petición es recibida desde un nodo de salida de dicha red.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''   
    def verificar_conexion_tor(self):
        try:      
            respuesta_ip = requests.get("https://check.torproject.org/api/ip", proxies=self.PROXIES, timeout=20)
            if not respuesta_ip.json().get("IsTor"):
                raise ConnectionError("La IP utilizada no pertenece a TOR.")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"No se pudo conectar con la API de verificación de TOR ({e})")
    
    '''
    * FUNCIÓN: obtener_html
    * DESCRIPCIÓN: Obtiene el código HTML de una dirección URL.
    * ARGS_IN:
        - url: dirección de la página.
    * ARGS_OUT:
        - HTML de la página. None, si el Content-Type no es text/html o si se produce algún tipo de error en la conexión.
    ''' 
    def obtener_html(self, url):
        try:
            head_response = requests.head(url, proxies=self.PROXIES, headers={'User-Agent': self.USER_AGENT}, timeout=20, allow_redirects=True)
            head_response.raise_for_status()

            content_type = head_response.headers.get('Content-Type', '').lower()
            # Si la cabecera HEAD no contiene html, se omiten los pasos adicionales para esa URL
            if 'text/html' not in content_type:
                return None

            response = requests.get(url, proxies=self.PROXIES, headers={'User-Agent': self.USER_AGENT}, timeout=30)
            response.raise_for_status()
            return response.content.decode('utf-8', errors='replace')
    
        except requests.exceptions.RequestException as e:
            return None
    '''
    * FUNCIÓN: encontrar_direcciones_bitcoin
    * DESCRIPCIÓN: Busca direcciones Bitcoin en un texto.
    * ARGS_IN:
        - texto: Texto en el que buscar monederos.
    * ARGS_OUT:
        - set con las direcciones de monederos Bitcoin encontrados en el texto.
    '''
    def encontrar_direcciones_bitcoin(self, texto):
        set_direcciones_bitcoin_texto = set()
        for regex in self.REGEX_BITCOIN:
            # Comprobación de las expresiones regulares
            set_direcciones_bitcoin_texto.update(regex.findall(texto.strip()))
        if len(set_direcciones_bitcoin_texto) > 0:
            for direccion_monedero in list(set_direcciones_bitcoin_texto):
                try:
                    # Comprobación de la sintaxis del candidato a monedero
                    Address.parse(direccion_monedero)
                except EncodingError:
                    # Es eliminado si la validación es errónea
                    set_direcciones_bitcoin_texto.remove(direccion_monedero)
        
        return set_direcciones_bitcoin_texto

    '''
    * FUNCIÓN: procesar_y_extraer_enlaces
    * DESCRIPCIÓN: Procesa código HTML y busca direcciones Bitcoin y nuevos enlaces para visitar.
    * ARGS_IN:
        - html: código HTML de la página.
        - url_base: URL del dominio del cuál se está procesando la página.
    * ARGS_OUT:
        - set con las direcciones de monederos Bitcoin encontrados en el texto.
        - set con los enlaces a otras páginas encontrados en el código.
    '''
    def procesar_y_extraer_enlaces(self, html, url_base):
        if not html: 
            return set(), set()
        set_direcciones_bitcoin = set()
        soup = BeautifulSoup(html, 'lxml')
        set_direcciones_bitcoin.update(self.encontrar_direcciones_bitcoin(soup.get_text(separator=' ')))
        set_enlaces = set()
        for link in soup.find_all('a', href=True):
            if link['href']:
                url = urljoin(url_base, link['href'])
                if ".onion" in url:
                    set_enlaces.add(url)
        return set_direcciones_bitcoin, set_enlaces


'''
* CLASE: VentanaCrawler
* DESCRIPCIÓN: Clase que implementa la ventana de configuración del crawler.
'''
class VentanaCrawler(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Gestión del hilo y la comunicación
        self.hilo_crawler = None
        self.ventana_progreso = None
        self.evento_parada = Event()
        self.cola_comunicacion = queue.Queue()

        # Encabezado de la página
        frame_encabezado = ctk.CTkFrame(self)
        frame_encabezado.pack(fill="x", padx=20, pady=(20, 0))
        
        # Cuando es pulsado, el botón de retroceso muestra la ventana inicial
        boton_atras = ctk.CTkButton(frame_encabezado, text="Atrás", width=80, font=("Arial", 20, "bold"), command=lambda:self.controller.mostrar_ventana("VentanaInicio"))
        boton_atras.pack(side="left", padx=(10, 20), pady=10)
        
        self.label_titulo = ctk.CTkLabel(frame_encabezado, text="Introducir parámetros de búsqueda", font=ctk.CTkFont(size=30, weight="bold"))
        self.label_titulo.pack(side="left", pady=10)
        
        self.label_minimo_monederos = ctk.CTkLabel(self, text="Número mínimo de monederos:", font=("Arial", 20)).pack(pady=40)
        
        # Entrada para el número mínimo de monederos a encontrar
        self.entrada_num_min_monederos = ctk.CTkEntry(self, placeholder_text="Ej: 5", font=("Arial", 18))
        self.entrada_num_min_monederos.pack(pady=1)

        self.label_urls = ctk.CTkLabel(self, text="URLs de páginas web (una por línea):", font=("Arial", 20)).pack(pady=40)
        
        # Entrada para las URL iniciales de búsqueda
        self.entrada_urls = ctk.CTkTextbox(self, height=250, width=1200, font=("Arial", 18))
        self.entrada_urls.pack(pady=5)
        
        # Cuando es pulsado, el botón inicia el rastreo en la red TOR
        self.boton_busqueda = ctk.CTkButton(self, text="Iniciar búsqueda en TOR", font=("Arial", 20, "bold"), command=self.iniciar_crawler)
        self.boton_busqueda.pack(pady=45)

    '''
    * FUNCIÓN: iniciar_crawler
    * DESCRIPCIÓN: Procesamiento de la entrada del usuario y creación del hilo de ejecución de la búsqueda de monederos en TOR.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def iniciar_crawler(self):
        # Expresión regular que modeliza la sintaxis de una URL de servicio oculto de la red TOR
        REGEX_URL_TOR = r"^(https?://)?[a-z2-7]{56}\.onion([/?#].*)?$"
        
        # Obtención del texto de entrada
        texto_entrada_urls = self.entrada_urls.get("1.0", "end-1c").strip().splitlines()
        
        # Se mantienen las URLs que cumplan la expresión regular
        urls = [url for url in texto_entrada_urls if url.strip() and re.match(REGEX_URL_TOR, url)]
    
        try:
            num_min_monederos = int(self.entrada_num_min_monederos.get())
            if num_min_monederos < 1: raise ValueError
        except ValueError:
            messagebox.showwarning("Entrada inválida", "El número mínimo de monederos debe ser un entero positivo.")
            return

        if not urls:
            messagebox.showwarning("Entrada inválida", 
                                   "Se debe proporcionar al menos una URL .onion inicial válida sintácticamente que incluya el protocolo (http:// o https://)")
            return
        
        # Se inhabilita el botón de búsqueda y se reinicia el evento de parada
        self.boton_busqueda.configure(state="disabled")
        self.evento_parada.clear()
        
        # Se muestra la ventana de progreso
        self.ventana_progreso = VentanaEmergenteProgreso(self, num_min_monederos)
        self.after(200, self.ventana_progreso.grab_set)

        # Instanciación y arranque del hilo de rastreo
        self.hilo_crawler = HiloCrawler(urls, num_min_monederos, self.cola_comunicacion, self.evento_parada)
        self.hilo_crawler.start()

        # Inicio del bucle de chequeo de la cola en la interfaz gráfica
        self.after(250, self.procesar_cola)

    '''
    * FUNCIÓN: procesar_cola
    * DESCRIPCIÓN: Procesamiento de los mensajes introducidos en la cola por parte del hilo de rastreo.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def procesar_cola(self):
        try:
            # Obtención de mensaje de la cola
            mensaje = self.cola_comunicacion.get_nowait()
            comando, datos = mensaje

            num_min_monederos = int(self.entrada_num_min_monederos.get())

            # Si es de tipo "estado", se actualiza el texto de la ventana emergente
            if comando == "estado":
                texto_monederos_ventana = self.ventana_progreso.label_monederos_encontrados.cget("text").split(" ")[2]
                self.ventana_progreso.actualizar_progreso(datos, int(texto_monederos_ventana), num_min_monederos)
            
            # Si se ha encontrado un monedero, se actualiza el número en la ventana emergente
            elif comando == "monedero_encontrado":
                texto_estado = self.ventana_progreso.label_estado.cget("text")
                self.ventana_progreso.actualizar_progreso(texto_estado, datos, num_min_monederos)

            # Si la ejecución ha terminado, se restaura la ventana de configuración del crawler, se informa al usuario
            # y se muestra la ventana de monederos encontrados con los resultados
            elif comando == "terminado":
                self.restaurar_ventana_crawler()
                messagebox.showinfo("Proceso Finalizado", "Se ha completado el rastreo")
                self.controller.mostrar_ventana("VentanaMonederosEncontrados", resultados=datos)
            
            # Si la ejecución ha sido cancelada y ha finalizado la ejecución, se restaura la ventana de configuración del crawler
            elif comando == "cancelado":
                self.restaurar_ventana_crawler()
            
            # Si se ha producido un error, se informa al usuario
            elif comando == "error":
                messagebox.showerror("Error en el Crawler", f"Ha ocurrido un error:\n\n{datos}")
                self.restaurar_ventana_crawler()
            
            # Si se ha producido un error en la verificación de la conexión de la red TOR, se informa al usuario
            elif comando == "error_conexion":
                messagebox.showerror("Error en el Crawler", "Error al establecer conexión con la red TOR.")
                self.restaurar_ventana_crawler()
        
        except queue.Empty:
            # Si la cola está vacía, no se realiza ninguna acción
            pass
        finally:
            # Si el hilo sigue en funcionamiento, se vuelve a ejecutar esta función en 100 milisegundos
            if self.hilo_crawler and self.hilo_crawler.is_alive():
                self.after(100, self.procesar_cola)
    
    '''
    * FUNCIÓN: detener_crawler
    * DESCRIPCIÓN: Función llamada por la ventana de progreso para detener el hilo del crawler.
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def detener_crawler(self):
        # Si el hilo de ejecución se encuentra en ejecución, se establece el evento de parada
        if self.hilo_crawler and self.hilo_crawler.is_alive():
            self.evento_parada.set()

    '''
    * FUNCIÓN: restaurar_ventana_crawler
    * DESCRIPCIÓN: Función que cierra la ventana emergente de progreso y restaura la ventana de configuración del crawler
    * ARGS_IN:
        - N/A
    * ARGS_OUT:
        - N/A
    '''
    def restaurar_ventana_crawler(self):l
        if self.ventana_progreso:
            # Cierre de la ventana de progreso
            self.ventana_progreso.destroy()
            self.ventana_progreso = None
        
        # Habilitación del botón de búsqueda
        self.boton_busqueda.configure(state="normal")
        self.hilo_crawler = None