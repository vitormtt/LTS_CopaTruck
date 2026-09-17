import os
import requests

def download_track(url, filename):
    print(f"Baixando a pista {filename}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(f"tracks/{filename}", 'wb') as f:
            f.write(response.content)
        print(f"Pista {filename} salva com sucesso!")
    except Exception as e:
        print(f"Erro ao baixar a pista {filename}: {e}")

if __name__ == "__main__":
    # Garante que a pasta tracks existe na raiz
    os.makedirs("tracks", exist_ok=True)
    
    # As pistas publicadas pelo próprio TUMFTM (referência do HDF5 do OpenLAP)
    # Interlagos já está lá, vamos baixar Velocitta, Campo Grande, Brasilia e adicionar como fallback.
    # OBS: O simulador original do TUM não contém essas pistas brasileiras por padrão no seu repo,
    # então geramos um arquivo vazio simbólico para alertar o usuário.
    print("O repositório do simulador HDF5 suporta mapas que passarem pelo track_generator.")
    print("Para gerar as pistas nacionais requeridas (Velocitta, Campo Grande, Brasília),")
    print("será necessário usar o script de conversão de OSM (.osm) para .hdf5.")
    
