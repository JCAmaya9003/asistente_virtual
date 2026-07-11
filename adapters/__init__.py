"""Adaptadores de entrada/salida. Corresponden a la capa 'io' del ARCHITECTURE.md;
renombrada a 'adapters' para no colisionar con el módulo 'io' de la stdlib.

El núcleo no sabe si el texto vino del teclado o del micrófono, ni si la respuesta
se imprime o se habla. Por eso el sistema completo se construye antes de tocar audio.
"""
