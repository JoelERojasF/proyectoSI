import socket
import threading
import sys

# Configuración
HOST = '192.168.100.13'  # Cambiar por IP del servidor
TCP_PORT = 50000
UDP_PORT = 50001
BUFFER_SIZE = 1024

class ClienteChat:
    def __init__(self):
        self.usuario_actual = ""
        self.tcp_active = False
        self.udp_active = False

    def recibir_tcp(self, conn):
        """Hilo para recibir mensajes TCP"""
        while self.tcp_active:
            try:
                data = conn.recv(BUFFER_SIZE)
                if not data:
                    print("\n[Servidor] Conexión cerrada")
                    break
                print(f"\n{data.decode()}", end='')
                print(f"{self.usuario_actual}> ", end='', flush=True)
            except:
                print("\n[Error] Conexión TCP perdida")
                break

    def cliente_tcp(self):
        """Conexión TCP con autenticación"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, TCP_PORT))
                self.tcp_active = True
                print("Conexión TCP establecida")

                # Autenticación
                print(s.recv(BUFFER_SIZE).decode(), end='')
                self.usuario_actual = input().strip()
                s.sendall(self.usuario_actual.encode())

                print(s.recv(BUFFER_SIZE).decode(), end='')
                clave = input().strip()
                s.sendall(clave.encode())

                respuesta = s.recv(BUFFER_SIZE).decode()
                print(respuesta)

                if "Autenticado" in respuesta:
                    # Hilo para recibir mensajes
                    threading.Thread(target=self.recibir_tcp, args=(s,), daemon=True).start()

                    # Envío de mensajes
                    while self.tcp_active:
                        msg = input(f"{self.usuario_actual}> ")
                        if msg.lower() == 'salir':
                            s.sendall(b"salir")
                            self.tcp_active = False
                            break
                        s.sendall(msg.encode())

            except ConnectionRefusedError:
                print("[Error] Servidor no disponible")
            except Exception as e:
                print(f"[Error TCP] {e}")
            finally:
                self.tcp_active = False

    def recibir_udp(self, sock):
        """Hilo para recibir mensajes UDP"""
        while self.udp_active:
            try:
                data, _ = sock.recvfrom(BUFFER_SIZE)
                print(f"\n{data.decode()}", end='')
                print(f"{self.usuario_actual}> ", end='', flush=True)
            except:
                print("\n[Error] Conexión UDP perdida")
                break

    def cliente_udp(self):
        """Conexión UDP con autenticación"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.bind(('0.0.0.0', 0))  # Puerto local aleatorio
                self.udp_active = True
                print("Conexión UDP lista")

                # Autenticación
                self.usuario_actual = input("Usuario: ").strip()
                clave = input("Clave: ").strip()
                credenciales = f"{self.usuario_actual}:{clave}"
                s.sendto(credenciales.encode(), (HOST, UDP_PORT))

                respuesta, _ = s.recvfrom(BUFFER_SIZE)
                print(respuesta.decode())

                if "Autenticado" in respuesta.decode():
                    # Hilo para recibir mensajes
                    threading.Thread(target=self.recibir_udp, args=(s,), daemon=True).start()

                    # Envío de mensajes
                    while self.udp_active:
                        msg = input(f"{self.usuario_actual}> ")
                        if msg.lower() == 'salir':
                            s.sendto(b"salir", (HOST, UDP_PORT))
                            self.udp_active = False
                            break
                        s.sendto(msg.encode(), (HOST, UDP_PORT))

            except Exception as e:
                print(f"[Error UDP] {e}")
            finally:
                self.udp_active = False

    def iniciar(self):
        """Menú principal"""
        print("=== CLIENTE DE CHAT ===")
        print(f"Conectando a {HOST}")

        while True:
            protocolo = input("Selecciona protocolo (tcp/udp): ").lower().strip()
            if protocolo == 'tcp':
                self.cliente_tcp()
                break
            elif protocolo == 'udp':
                self.cliente_udp()
                break
            else:
                print("Opción inválida")

if __name__ == "__main__":
    cliente = ClienteChat()
    try:
        cliente.iniciar()
    except KeyboardInterrupt:
        print("\nCliente terminado")
        sys.exit(0)