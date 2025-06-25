import json
import os
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import Document, init_beanie

# Estas variáveis definem onde o banco de dados MongoDB está rodando.
MONGO_HOST = 'localhost' # Endereço do servidor MongoDB (geralmente 'localhost' para ambiente local)
MONGO_PORT = 27017       # Porta padrão do MongoDB
MONGO_DB_NAME = 'protocolos_db' # Nome do banco de dados que será usado ou criado
MONGO_DB_USERNAME = 'admin' # Credencial de username para autentificação no banco
MONGO_DB_PASSWORD = 'admin123' # Credencial de password para autentificação no banco
DIR_JSON = ".\\json_output"

class Protocolo(Document):
    protocolo_id: int
    status: Optional[str] = None
    titular: Optional[str] = None
    data_deposito: Optional[str] = None
    apresentação: Optional[str] = None
    natureza: Optional[str] = None
    elemento_nominativo: Optional[str] = None
    cfe: Optional[str] = None
    ncl: Optional[int] = 0
    especificação: Optional[str] = None 
    logo: Optional[str] = None
    classe: Optional[int] = 0
    
def get_database_uri():
    return f"mongodb://{MONGO_DB_USERNAME}:{MONGO_DB_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"


async def save_or_update_by_batch():
    client = AsyncIOMotorClient(get_database_uri())
    await init_beanie(database=client.protocolos, document_models=[Protocolo])

    for arquivo in os.listdir(DIR_JSON):
        if arquivo.endswith(".json"):
            arquivo_path = os.path.join(DIR_JSON, arquivo)
            print(f'Processando: {arquivo_path}')

            with open(arquivo_path, "r", encoding="utf-8") as a:
                try:
                    protocolos = json.load(a)
                except json.JSONDecodeError as e:
                    print(f'Erro ao carregar {a}: {e}')
                    continue
            for dados in protocolos:
                protocolo_existente = await Protocolo.find_one(Protocolo.protocolo_id == dados["protocolo_id"])

                if protocolo_existente:
                    for k, v in dados.items():
                        setattr(protocolo_existente, k, v)
                    await protocolo_existente.save()
                    print(f"Atualizado: {protocolo_existente.protocolo_id}")
                else:
                    novo_protocolo = Protocolo(**dados)
                    await novo_protocolo.insert()
                    print(f"Inserido: {novo_protocolo.protocolo_id}")
        os.remove(arquivo_path)