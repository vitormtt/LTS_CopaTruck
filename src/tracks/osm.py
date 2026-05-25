# src/tracks/osm.py
"""
OpenStreetMapDownloader: Baixa circuitos brasileiros via Overpass API/OSM ou cria aproximação.
"""
import requests
import numpy as np
from typing import Optional, Dict

class OpenStreetMapDownloader:
    OVERPASS_URL = "https://overpass-api.de/api/interpreter"
    BRAZILIAN_CIRCUITS = {
        'cascavel': {
            'name': 'Cascavel',
            'lat': -24.9586,
            'lon': -53.4878,
            'radius': 800,
            'length': 3045,
            'width': 12.0
        },
        # ...adicione mais circuitos aqui se quiser
    }
    @classmethod
    def download(cls, circuit_key: str) -> Optional[Dict]:
        circuit_key = circuit_key.lower().replace(' ', '_')
        if circuit_key not in cls.BRAZILIAN_CIRCUITS:
            return None
        info = cls.BRAZILIAN_CIRCUITS[circuit_key]
        query = f"""
        [out:json][timeout:25];
        (
          way["sport"="motor"]["motor_vehicle"="yes"](around:{info['radius']},{info['lat']},{info['lon']});
          way["highway"="raceway"](around:{info['radius']},{info['lat']},{info['lon']});
        );
        out geom;
        """
        try:
            r = requests.post(cls.OVERPASS_URL, data={'data': query}, timeout=30)
            r.raise_for_status()
            data = r.json()
            if data.get('elements'):
                return {'osm_data': data['elements'], 'info': info}
            else:
                return None
        except Exception:
            return None
    @classmethod
    def is_available(cls, circuit_key: str) -> bool:
        return circuit_key.lower().replace(' ', '_') in cls.BRAZILIAN_CIRCUITS
