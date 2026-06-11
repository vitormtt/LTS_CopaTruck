# src/tracks/tumftm.py
"""
TUMFTMDownloader: Faz download de circuitos do projeto TUMFTM (Technical University of Munich).
Referência: https://github.com/TUMFTM/racetrack-database
"""
import requests
import pandas as pd
from io import StringIO

class TUMFTMDownloader:
    BASE_URL = "https://raw.githubusercontent.com/TUMFTM/racetrack-database/master/tracks/"
    AVAILABLE_CIRCUITS = {
        'austin': 'Austin',
        'interlagos': 'SaoPaulo',
        'silverstone': 'Silverstone',
        # ...adicione mais conforme desejar
    }
    @classmethod
    def download(cls, circuit_key):
        circuit_key = circuit_key.lower().replace(' ', '_')
        if circuit_key not in cls.AVAILABLE_CIRCUITS:
            raise ValueError(f"Circuito não disponível em TUMFTM: {circuit_key}")
        file_name = cls.AVAILABLE_CIRCUITS[circuit_key]
        url = f"{cls.BASE_URL}{file_name}.csv"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        df = pd.read_csv(StringIO(resp.text), names=['x_m', 'y_m', 'w_tr_right_m', 'w_tr_left_m'], comment='#')
        return df
    @classmethod
    def is_available(cls, circuit_key):
        return circuit_key.lower().replace(' ', '_') in cls.AVAILABLE_CIRCUITS
