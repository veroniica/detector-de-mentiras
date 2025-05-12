# Audio Interview Analysis System

Este sistema procesa entrevistas de audio relacionadas con casos criminales y proporciona:

1. Transcripciones limpias en formato de guión con marcas de tiempo
2. Identificación y diarización de hablantes
3. Ideas principales y resúmenes de cada entrevista
4. Análisis de sentimiento para detectar posible engaño
5. Detección de inconsistencias entre diferentes entrevistas

## Descripción General

El sistema está diseñado para analizar entrevistas de audio relacionadas con casos criminales. Procesa múltiples archivos de audio, identifica diferentes hablantes, transcribe el contenido, y realiza análisis avanzados para ayudar en la investigación.

### Características Principales

- **Transcripción de Audio**: Convierte el habla en texto con marcas de tiempo precisas.
- **Identificación de Hablantes**: Distingue entre diferentes voces en la grabación.
- **Formato de Guión**: Presenta la transcripción como un guión con nombres de hablantes.
- **Resumen Automático**: Genera resúmenes y extrae las ideas principales de cada entrevista.
- **Análisis de Sentimiento**: Detecta emociones y posibles indicadores de engaño en el tono de voz.
- **Detección de Inconsistencias**: Identifica contradicciones entre diferentes entrevistas.

## Arquitectura del Sistema

```
audio_analysis/
├── __init__.py
├── config.py                  # Configuración del sistema
├── main.py                    # Punto de entrada principal
├── transcription/             # Módulo de transcripción
│   ├── __init__.py
│   ├── transcriber.py         # Funcionalidad de voz a texto
│   └── diarization.py         # Identificación de hablantes
├── analysis/                  # Módulos de análisis
│   ├── __init__.py
│   ├── summarizer.py          # Extracción de ideas principales y resúmenes
│   ├── sentiment.py           # Análisis de sentimiento y detección de engaño
│   └── inconsistency.py       # Detección de inconsistencias entre entrevistas
├── utils/                     # Funciones de utilidad
│   ├── __init__.py
│   ├── audio_processing.py    # Preprocesamiento de audio
│   ├── output_formatter.py    # Formateo de salidas
│   └── s3_handler.py          # Manejo de operaciones con S3
└── tests/                     # Pruebas unitarias
    ├── __init__.py
    ├── test_transcription.py
    ├── test_analysis.py
    └── test_utils.py
```

## Flujo de Trabajo del Sistema

1. **Preprocesamiento de Audio**:
   - Normalización de volumen
   - Reducción de ruido
   - Conversión de formato

2. **Transcripción**:
   - Conversión de voz a texto
   - Generación de marcas de tiempo

3. **Diarización de Hablantes**:
   - Identificación de diferentes voces
   - Asignación de etiquetas de hablantes

4. **Análisis de Contenido**:
   - Generación de resúmenes
   - Extracción de ideas principales
   - Análisis de sentimiento y emociones

5. **Detección de Engaño**:
   - Análisis de características acústicas
   - Identificación de indicadores de estrés o engaño

6. **Análisis de Inconsistencias**:
   - Comparación de declaraciones entre entrevistas
   - Detección de contradicciones

7. **Generación de Informes**:
   - Transcripciones en formato de guión
   - Resúmenes y análisis
   - Informe de inconsistencias

## Requisitos

- Python 3.8+
- Paquetes requeridos: ver requirements.txt
- AWS CLI (para despliegue en AWS)

## Instalación Local

```bash
# Clonar el repositorio
git clone https://github.com/usuario/audio-interview-analysis.git
cd audio-interview-analysis

# Crear un entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Para el reconocimiento de voz y diarización, puede ser necesario instalar ffmpeg
# En Ubuntu: sudo apt-get install ffmpeg
# En macOS: brew install ffmpeg
# En Windows: descargar de https://ffmpeg.org/download.html
```

## Uso Local

### Línea de Comandos

```bash
# Uso básico
python -m audio_analysis.main --input_dir /ruta/a/archivos/audio --output_dir /ruta/a/salida

# Con opciones adicionales
python -m audio_analysis.main --input_dir /ruta/a/archivos/audio --output_dir /ruta/a/salida --debug
```

### Ejemplo de Uso

También puede utilizar el script de ejemplo incluido:

```bash
python example.py
```

Este script creará directorios de ejemplo y proporcionará instrucciones para usar el sistema.

## Despliegue en AWS

El sistema puede desplegarse en AWS utilizando la plantilla CloudFormation incluida. Esta plantilla crea una arquitectura serverless que procesa automáticamente los archivos de audio subidos a un bucket S3.

### Requisitos para el Despliegue en AWS

- Cuenta de AWS
- AWS CLI configurado
- Token de HuggingFace para acceder a los modelos de diarización

### Pasos para el Despliegue

1. **Crear la pila de CloudFormation**:

```bash
aws cloudformation create-stack \
  --stack-name audio-analysis-system \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=S3BucketName,ParameterValue=mi-bucket-de-audio-analisis \
    ParameterKey=HuggingFaceToken,ParameterValue=tu-token-de-huggingface \
  --capabilities CAPABILITY_IAM
```

2. **Construir y subir la imagen Docker a ECR**:

Una vez que la pila se haya creado correctamente, obtendrá la URL del repositorio ECR. Utilice los siguientes comandos para construir y subir la imagen Docker:

```bash
# Iniciar sesión en ECR
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com

# Construir la imagen Docker
docker build -t <account-id>.dkr.ecr.<region>.amazonaws.com/<repository-name>:latest .

# Subir la imagen a ECR
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/<repository-name>:latest
```

3. **Usar el sistema**:

Suba archivos de audio al bucket S3 en la carpeta `input/`:

```bash
aws s3 cp mi-entrevista.mp3 s3://mi-bucket-de-audio-analisis/input/
```

El sistema procesará automáticamente los archivos y guardará los resultados en la carpeta `output/` del mismo bucket.

## Estructura de Salida

El sistema genera los siguientes archivos de salida:

```
output/
├── transcripts/                # Transcripciones
│   ├── entrevista1_script.txt  # Transcripción en formato de guión
│   └── entrevista1_transcript.json  # Datos de transcripción en JSON
├── summaries/                  # Resúmenes
│   ├── entrevista1_summary.txt # Resumen en formato de texto
│   └── entrevista1_summary.json  # Datos de resumen en JSON
├── sentiment/                  # Análisis de sentimiento
│   ├── entrevista1_sentiment.txt  # Análisis de sentimiento en texto
│   └── entrevista1_sentiment.json  # Datos de sentimiento en JSON
└── inconsistency_analysis.txt  # Análisis de inconsistencias entre entrevistas
```

## Configuración

El sistema puede configurarse editando el archivo `audio_analysis/config.py`. Algunas opciones configurables incluyen:

- Idioma de transcripción
- Configuración de procesamiento de audio
- Umbrales para detección de inconsistencias
- Directorios predeterminados

## Limitaciones y Consideraciones

- El rendimiento de la transcripción depende de la calidad del audio
- La diarización de hablantes funciona mejor cuando hay diferencias claras entre las voces
- La detección de engaño debe considerarse como una herramienta de apoyo, no como evidencia definitiva
- El sistema está optimizado para español, pero puede funcionar con otros idiomas configurando el parámetro `LANGUAGE`

## Desarrollo y Pruebas

Para ejecutar las pruebas unitarias:

```bash
python -m unittest discover tests
```

## Licencia

Este proyecto está licenciado bajo los términos de la licencia MIT.