import traceback

class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}. O ip_outra_ponta é o IP do
        host ou roteador que se encontra na outra ponta do enlace, escrito como
        uma string no formato 'x.y.z.w'. A linha_serial é um objeto da classe
        PTY (vide camadafisica.py) ou de outra classe que implemente os métodos
        registrar_recebedor e enviar.
        """
        self.enlaces = {}
        self.callback = None
        # Constrói um Enlace para cada linha serial
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop, onde next_hop é um endereço IPv4
        fornecido como string (no formato x.y.z.w). A camada de enlace se
        responsabilizará por encontrar em qual enlace se encontra o next_hop.
        """
        # Encontra o Enlace capaz de alcançar next_hop e envia por ele
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.callback = None
        self.buffer = b''
        # Constantes do protocolo SLIP
        self.END = b'\xc0'
        self.ESC = b'\xdb'
        self.ESC_END = b'\xdc'
        self.ESC_ESC = b'\xdd'

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        # TODO: Preencha aqui com o código para enviar o datagrama pela linha
        # serial, fazendo corretamente a delimitação de quadros e o escape de
        # sequências especiais, de acordo com o protocolo CamadaEnlace (RFC 1055).
        
        # Passo 2: Faz o "byte stuffing" para escapar os caracteres especiais.
        # A ordem é importante para não escapar os bytes de escape recém-adicionados.
        datagrama_escapado = datagrama.replace(self.ESC, self.ESC + self.ESC_ESC)
        datagrama_escapado = datagrama_escapado.replace(self.END, self.ESC + self.ESC_END)

        # Passo 1: Delimita o quadro com o byte END no início e no fim.
        quadro_a_enviar = self.END + datagrama_escapado + self.END

        self.linha_serial.enviar(quadro_a_enviar)

    def __raw_recv(self, dados):
        # TODO: Preencha aqui com o código para receber dados da linha serial.
        # Trate corretamente as sequências de escape. Quando ler um quadro
        # completo, repasse o datagrama contido nesse quadro para a camada
        # superior chamando self.callback. Cuidado pois o argumento dados pode
        # vir quebrado de várias formas diferentes - por exemplo, podem vir
        # apenas pedaços de um quadro, ou um pedaço de quadro seguido de um
        # pedaço de outro, ou vários quadros de uma vez só.
        
        self.buffer += dados
        
        # Passo 3: Usa o byte END para encontrar os quadros completos no buffer.
        quadros = self.buffer.split(self.END)
        
        # O último elemento de 'quadros' é o que veio depois do último END,
        # ou seja, um quadro incompleto. Ele se torna o novo buffer.
        self.buffer = quadros[-1]
        
        # Processa cada quadro completo que foi recebido.
        for quadro in quadros[:-1]:
            # Ignora quadros vazios (gerados por sequências ...END-END...)
            if not quadro:
                continue

            # Passo 5: Usa um bloco try-except para lidar com erros na camada superior.
            try:
                # Passo 4: Reverte o "byte stuffing" (unstuffing).
                datagrama = quadro.replace(self.ESC + self.ESC_END, self.END)
                datagrama = datagrama.replace(self.ESC + self.ESC_ESC, self.ESC)
                
                # Se o callback estiver registrado, envia o datagrama "limpo".
                if self.callback:
                    self.callback(datagrama)
            except:
                # Se ocorrer um erro, imprime o traceback mas não trava o programa,
                # apenas descarta o quadro problemático.
                traceback.print_exc()