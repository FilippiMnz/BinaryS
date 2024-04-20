import mysql.connector
import requests
import re
import time

# Função para arredondar um número para o múltiplo mais próximo de 100
def round_to_nearest_100(num):
    return ((num + 50) // 100) * 100

# Função para conectar ao banco de dados 
def conectar_bd():
    try:
        conexao = mysql.connector.connect(
            host="localhost",
            user="user",
            password="password",
            database="NomeDoBancoDeDados"
        )
        print("Conexão bem-sucedida ao banco de dados.")
        return conexao
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao banco de dados: {err}")
        return None

# Função para verificar se um resultado já foi processado
def resultado_ja_processado(resultado, cursor):
    try:
        # Consulta para verificar se o resultado já existe no banco de dados
        query = "SELECT COUNT(*) FROM dados_fechamento WHERE nome_duopla = %s AND valor_fechamento = %s AND HOUR(hora_fechamento) = %s AND MINUTE(hora_fechamento) = %s"
        partes = resultado.split(" - ")
        nome_duopla = partes[0]
        hora = partes[1].split(":")[0].zfill(2)  # Adiciona zero à esquerda se necessário para garantir dois dígitos
        minuto = partes[1].split(":")[1].zfill(2)  # Adiciona zero à esquerda se necessário para garantir dois dígitos
        valor_fechamento = float(partes[2].split(" ")[1])
        cursor.execute(query, (nome_duopla, valor_fechamento, hora, minuto))
        count = cursor.fetchone()[0]
        return count > 0
    except mysql.connector.Error as err:
        print(f"Erro ao verificar resultado no banco de dados: {err}")
        return False

# Função para extrair elementos de chart.show para uma URL específica
def extrair_elementos_chart_show(url, par_moeda):
    resultados = []

    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text

        matches = re.findall(r'chart\.show\((.*?)\)', html)
        if matches:
            for match in matches:
                elements = re.findall(r"'(.*?)'", match.strip())
                if elements:
                    for element in elements:
                        digitos_e_sinais = re.findall(r'(\d{1})(\d{5})(-|\+)', element)
                        if digitos_e_sinais:
                            for d1, d2, s in digitos_e_sinais:
                                d1_com_ponto = d1 + '.'
                                resultado = f"{par_moeda} - {time.strftime('%H:%M', time.localtime())} - {'UP' if s == '+' else 'Down'} {d1_com_ponto}{d2}"
                                resultados.append(resultado)

        return resultados

    except Exception as e:
        print("Erro ao fazer a requisição:", e)
        return []

# Função para extrair elementos de chart.show para cada URL
def extrair_elementos_chart_show_para_lista_e_salvar_bd(urls, pares_moedas, rounded_time, conexao):
    try:
        cursor = conexao.cursor()
        for i in range(len(urls)):
            url_formatada = urls[i].format(rounded_time)
            resultados_para_url = extrair_elementos_chart_show(url_formatada, pares_moedas[i])
            if resultados_para_url:
                for resultado in resultados_para_url:
                    if not resultado_ja_processado(resultado, cursor):
                        # Extrair informações do resultado
                        partes = resultado.split(" - ")
                        nome_duopla = partes[0]
                        hora = partes[1].split(":")[0].zfill(2)  # Adiciona zero à esquerda se necessário para garantir dois dígitos
                        minuto = partes[1].split(":")[1].zfill(2)  # Adiciona zero à esquerda se necessário para garantir dois dígitos
                        situacao_fechamento = partes[2].split(" ")[0]
                        valor_fechamento = float(partes[2].split(" ")[1])

                        # Inserir o resultado no banco de dados
                        query = "INSERT INTO dados_fechamento (nome_duopla, hora_fechamento, situacao_fechamento, valor_fechamento) VALUES (%s, %s, %s, %s)"
                        cursor.execute(query, (nome_duopla, f"{hora}:{minuto}", situacao_fechamento, valor_fechamento))
                        conexao.commit()
                        print(f"Resultado inserido no banco de dados: {resultado}")
    except mysql.connector.Error as err:
        print(f"Erro ao salvar resultados no banco de dados: {err}")
    finally:
        cursor.close()

# Função principal para extrair e processar os dados dos sinais
def extrair_dados_e_salvar_bd():
    conexao = conectar_bd()
    if conexao:
        while True:
            try:
                rounded_time = round_to_nearest_100(int(time.time()))
                urls = [
                    "https://binary-signal.com/pt/chart/eurusd/?ts={}",
                    "https://binary-signal.com/pt/chart/usdjpy/?ts={}",
                    "https://binary-signal.com/pt/chart/gbpusd/?ts={}",
                    "https://binary-signal.com/pt/chart/usdchf/?ts={}",
                    "https://binary-signal.com/pt/chart/eurjpy/?ts={}",
                    "https://binary-signal.com/pt/chart/usdcad/?ts={}",
                    "https://binary-signal.com/pt/chart/audusd/?ts={}"
                ]
                pares_moedas = ['EUR/USD', 'USD/JPY', 'GBP/USD', 'USD/CHF', 'EUR/JPY', 'USD/CAD', 'AUD/USD']

                url = f"https://binary-signal.com/alerts/?t={rounded_time}"

                response = requests.get(url)
                response.raise_for_status()
                data = response.text.strip()

                extrair_elementos_chart_show_para_lista_e_salvar_bd(urls, pares_moedas, rounded_time, conexao)

            except requests.exceptions.RequestException as e:
                print("Erro ao fazer a requisição:", e)

            time.sleep(0.1)

extrair_dados_e_salvar_bd()
