# Análisis Forense de Audio con AWS AI Services

Este proyecto implementa una arquitectura serverless utilizando servicios de AWS para procesar y analizar entrevistas de audio relacionadas con casos criminalísticos.

## Funcionalidades

- Transcripción de audio con identificación de hablantes (formato guión)
- Marcas de tiempo para cada fragmento de diálogo
- Extracción de ideas principales y resumen de cada audio
- Análisis de sentimiento para detectar posibles mentiras
- Identificación de inconsistencias entre diferentes entrevistas

## Arquitectura

La solución utiliza los siguientes servicios de AWS:
- Amazon S3: Almacenamiento de archivos de audio y resultados
- AWS Lambda: Procesamiento serverless
- Amazon Transcribe: Transcripción de audio con identificación de hablantes
- Amazon Comprehend: Análisis de sentimiento y extracción de frases clave
- Amazon Bedrock: Análisis avanzado de texto para resúmenes e inconsistencias
- AWS Step Functions: Orquestación del flujo de trabajo
- Amazon EventBridge: Activación de procesos basados en eventos
- Amazon DynamoDB: Almacenamiento de metadatos y resultados intermedios

## Requisitos

- AWS CLI configurado
- Python 3.9+
- Make

## Instalación

```bash
make deploy
```

## Uso

1. Sube los archivos de audio al bucket S3 creado
2. El proceso se iniciará automáticamente
3. Los resultados estarán disponibles en el bucket de salida

## Desarrollo

```bash
# Instalar dependencias de desarrollo
make dev

# Ejecutar pruebas
make test

# Validar formato de código
make lint
```
