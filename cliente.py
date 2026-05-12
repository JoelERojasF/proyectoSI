import socket
import threading
import sys

# Configuración
HOST = "127.0.0.1"  # Cambiar por IP del servidor
TCP_PORT = 50000
BUFFER_SIZE = 1024

class ClienteChat:
    def __init__(self):
        self.usuario_actual = ""
        self.tcp_active = False

    def recibir_tcp(self, conn):
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
                    threading.Thread(target=self.recibir_tcp, args=(s,), daemon=True).start()

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

    def iniciar(self):
        print("=== CLIENTE DE CHAT (TCP) ===")
        print(f"Conectando a {HOST}")
        self.cliente_tcp()

if __name__ == "__main__":
    cliente = ClienteChat()
    try:
        cliente.iniciar()
    except KeyboardInterrupt:
        print("\nCliente terminado")
        sys.exit(0)