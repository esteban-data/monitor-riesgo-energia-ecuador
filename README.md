# Monitor de Riesgo Energético — Ecuador 
![Captura diaria](https://github.com/esteban-data/monitor-riesgo-energia-ecuador/actions/workflows/captura_diaria.yml/badge.svg)
![Cota Mazar](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Festeban-data%2Fmonitor-riesgo-energia-ecuador%2Fmain%2Fstatus.json)
![Demanda pico](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2Festeban-data%2Fmonitor-riesgo-energia-ecuador%2Fmain%2Fstatus_demanda.json)

Sistema automatizado que rastrea diariamente el nivel del embalse Mazar y el pico de demanda eléctrica nacional, como primer paso hacia un modelo de predicción de riesgo de apagones para el sector industrial ecuatoriano.

## 📌 Contexto

Ecuador atraviesa un período de estiaje (bajo nivel de agua en las represas) que amenaza con generar cortes de energía programados. Las industrias no cuentan con una herramienta que les permita anticipar estos cortes con varios días de antelación para planificar turnos, mantenimiento e inventario de combustibles de respaldo.

Este proyecto captura y almacena, de forma 100% automática, los datos necesarios para eventualmente construir ese sistema de alerta temprana.

## Funcionamiento

(GitHub Actions) ejecuta el script `captura_diaria.py`, que:

1. Consulta la cota (nivel) del embalse Mazar, extraída de la API interna de CELEC Sur.
2. Consulta el pico de demanda eléctrica nacional del día anterior, publicado por CENACE.
3. Guarda ambos valores en `historico_diario.csv`, sin duplicar ni sobrescribir datos anteriores.
4. Sube el cambio automáticamente al repositorio.

Todo el proceso corre sin intervención humana, una vez al día.

## 📊 Datos recolectados

|      Columna     |             Descripción                  |
|------------------|------------------------------------------|
|  `fecha`         | Día al que corresponde el dato           |
| `cota_mazar`     | Nivel del embalse Mazar (msnm)           |
| `pico_demanda_mw`| Demanda máxima nacional de ese día (MW)  |

##  Tecnologías

- Python (`requests`, `pandas`)
- GitHub Actions (automatización)
- Datos abiertos de CELEC Sur y CENACE

## 👤 Autor

Esteban — Estudiante de Ingeniería en Ciencias de Datos, Ecuador.

## ⚠️ Nota

Los datos provienen de fuentes públicas del sector eléctrico ecuatoriano. Este proyecto es de carácter académico y no está afiliado a CELEC EP ni a CENACE.
