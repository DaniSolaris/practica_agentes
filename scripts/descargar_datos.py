"""Descarga los datos de taxis amarillos de Nueva York (NYC TLC).

Uso:
    python scripts/descargar_datos.py                      # enero-marzo 2024
    python scripts/descargar_datos.py --anio 2023 --meses 1 2 3 4

Los ficheros se guardan en data/raw/ (carpeta ignorada por git).
Fuente: https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page
"""

import argparse
import urllib.request
from pathlib import Path

BASE_URL = "https://d37ci6vzurychx.cloudfront.net"
RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "data" / "raw"


def descargar(url: str, destino: Path) -> None:
    if destino.exists():
        print(f"Ya existe, se omite: {destino.name}")
        return
    print(f"Descargando {url} ...")
    tmp = destino.with_suffix(destino.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(destino)
    print(f"  -> {destino.name} ({destino.stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anio", type=int, default=2024)
    parser.add_argument("--meses", type=int, nargs="+", default=[1, 2, 3])
    args = parser.parse_args()

    DESTINO.mkdir(parents=True, exist_ok=True)

    # Tabla de zonas: traduce los IDs de zona a barrio / nombre
    descargar(f"{BASE_URL}/misc/taxi_zone_lookup.csv", DESTINO / "taxi_zone_lookup.csv")

    for mes in args.meses:
        nombre = f"yellow_tripdata_{args.anio}-{mes:02d}.parquet"
        descargar(f"{BASE_URL}/trip-data/{nombre}", DESTINO / nombre)


if __name__ == "__main__":
    main()
