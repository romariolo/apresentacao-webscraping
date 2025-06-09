# verifica e instala as dependencias necessarias
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    import os
    import requests
    from urllib.parse import urlparse
    import zipfile
    import xml.etree.ElementTree as ET
    import json
    from datetime import datetime
    import io
except ImportError as e:
    print(f"Biblioteca não encontrada: {e}. Instalando dependências...")
    import subprocess
    import sys

    required_packages = [
        'selenium',
        'requests',
        'urllib3',
        'zipfile36',
        'lxml'
    ]

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", package])

    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    import os
    import requests
    from urllib.parse import urlparse
    import zipfile
    import xml.etree.ElementTree as ET
    import json
    from datetime import datetime
    import io

# ----------------------------------------------------------------------------#

# config do navegador
service = Service()
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--log-level=3')
driver = webdriver.Chrome(service=service, options=options)

# ----------------------------------------------------------------------------#


def download_and_extract_zip(url, folder='downloads_xml'):
    # extrai o nome base do arquivo
    zip_filename = os.path.basename(urlparse(url).path)
    base_name = zip_filename.replace('.zip', '')
    xml_filename = f"{base_name}.xml"
    xml_path = os.path.join(folder, xml_filename)

    # verifica se o XML final ja existe
    if os.path.exists(xml_path):
        print(f"Arquivo {xml_filename} já existe, pulando download.")
        return False  # retorna False pois n foi necessario baixar

    # se n existe, faz o download
    try:
        print(f"Baixando {zip_filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # cria a pasta se nn existir
        os.makedirs(folder, exist_ok=True)

        # caminho temporario para o ZIP
        zip_path = os.path.join(folder, zip_filename)

        # salva o arquivo ZIP
        with open(zip_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # extrai o conteúdo
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(folder)
            print(f"Arquivos extraídos de {zip_filename}")

        # remove o ZIP
        os.remove(zip_path)
        return True  # retorna true pois foi baixado novo arquivo

    except Exception as e:
        print(f"Erro ao processar {url}: {e}")
        if 'zip_path' in locals() and os.path.exists(zip_path):
            os.remove(zip_path)
        return False

# ----------------------------------------------------------------------------#


def parse_xml_to_json(xml_file, json_folder='json_output'):
    # cria a pasta para os JSONs se não existir
    os.makedirs(json_folder, exist_ok=True)

    try:
        # parseia o arquivo XML
        tree = ET.parse(xml_file)
        root = tree.getroot()

        processos_json = []

        for processo in root.findall('processo'):
            try:
                protocolo_id = int(processo.get('numero'))
                data_deposito = processo.get('data-deposito', '')

                # titular
                titular = ''
                if processo.find('titulares') is not None:
                    titular = processo.find(
                        'titulares/titular').get('nome-razao-social', '')

                # dados da marca
                marca = processo.find('marca')
                apresentacao = marca.get(
                    'apresentacao', '') if marca is not None else ''
                natureza = marca.get(
                    'natureza', '') if marca is not None else ''
                elemento_nominativo = marca.findtext(
                    'nome', '') if marca is not None else ''

                # classe Vienna (CFE)
                cfe = ''
                if processo.find('classes-vienna/classe-vienna') is not None:
                    cfe = processo.find(
                        'classes-vienna/classe-vienna').get('codigo', '')

                # classe Nice (NCL)
                ncl = 0
                especificacao = ''
                status = ''
                if processo.find('lista-classe-nice/classe-nice') is not None:
                    classe_nice = processo.find(
                        'lista-classe-nice/classe-nice')
                    ncl = int(classe_nice.get('codigo', '0'))
                    especificacao = classe_nice.findtext(
                        'especificacao', '').strip().rstrip(';').upper()
                    status = classe_nice.findtext('status', '')

                # logo (verifica classes Vienna)
                logo = 'Sim' if processo.find(
                    'classes-vienna') is not None else 'Não'

                # monta o dicionario
                processo_data = {
                    "protocolo_id": protocolo_id,
                    "status": status,
                    "titular": titular,
                    "data_deposito": data_deposito,
                    "apresentação": apresentacao,
                    "natureza": natureza,
                    "elemento_nominativo": elemento_nominativo,
                    "cfe": cfe,
                    "ncl": ncl,
                    "especificação": especificacao,
                    "logo": logo,
                    "classe": ncl
                }

                # remove campos vazios
                processo_data = {
                    k: v for k, v in processo_data.items() if v not in ('', None, 0)}

                processos_json.append(processo_data)

            except Exception as e:
                print(
                    f"Erro ao processar processo {processo.get('numero', 'desconhecido')}: {e}")

        # gera o JSON
        json_filename = os.path.basename(xml_file).replace('.xml', '.json')
        json_path = os.path.join(json_folder, json_filename)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(processos_json, f, ensure_ascii=False, indent=4)

        print(f"Arquivo JSON gerado: {json_path}")
        return json_path

    except Exception as e:
        print(f"Erro ao processar {xml_file}: {e}")
        return None

# ----------------------------------------------------------------------------#


def main():
    url = "https://revistas.inpi.gov.br/rpi/"
    driver.get(url)

    # encontra todas as linhas da tabela (ignorando cabeçalho)
    rows = driver.find_elements(
        By.XPATH, "/html/body/div[4]/div/table[1]/tbody/tr[position()>1]")

    for row in rows:
        try:
            # pega o link do ZIP
            zip_link = row.find_element(
                By.XPATH, "./td[7]/div/a[2]").get_attribute('href')

            if zip_link and zip_link.endswith('.zip'):
                # baixa apenas se necessario
                if download_and_extract_zip(zip_link):
                    # processa apenas o XML correspondente
                    base_name = os.path.basename(zip_link).replace('.zip', '')
                    xml_file = os.path.join(
                        'downloads_xml', f"{base_name}.xml")
                    if os.path.exists(xml_file):
                        parse_xml_to_json(xml_file)
        except Exception as e:
            print(f"Erro ao processar linha: {e}")

    driver.quit()

# ----------------------------------------------------------------------------#


if __name__ == "__main__":
    main()