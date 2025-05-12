# Arquitectura del Sistema de Análisis de Entrevistas de Audio

## Diagrama de Arquitectura

```
+----------------------------------------------------------------------------------------------------------+
|                                            AWS Cloud                                                      |
|                                                                                                          |
|  +----------------+     +-----------------+     +------------------+     +----------------------+         |
|  |                |     |                 |     |                  |     |                      |         |
|  |  S3 Bucket     |     |  Lambda         |     |  AWS Batch       |     |  ECR Repository      |         |
|  |                |     |  Function       |     |  Job Queue       |     |                      |         |
|  |  +----------+  |     |                 |     |                  |     |  +----------------+  |         |
|  |  | Audio    |  |     |  +-----------+  |     |  +------------+  |     |  | Docker Image  |  |         |
|  |  | Files    |--+-----+->| Trigger   |--+-----+->| Process    |  |     |  | audio-analysis|  |         |
|  |  +----------+  |     |  | Processing|  |     |  | Audio Files|<-+-----+--+                |  |         |
|  |                |     |  +-----------+  |     |  +------------+  |     |  +----------------+  |         |
|  |  +----------+  |     |                 |     |                  |     |                      |         |
|  |  | Results  |<-+-----+------------------+-----+------------------+     |                      |         |
|  |  +----------+  |     |                 |     |                  |     |                      |         |
|  +----------------+     +-----------------+     +------------------+     +----------------------+         |
|                                                                                                          |
|                                                                                                          |
|  +----------------+     +-----------------+     +------------------+                                     |
|  |                |     |                 |     |                  |                                     |
|  |  VPC           |     |  Subnets        |     |  Security Groups |                                     |
|  |                |     |                 |     |                  |                                     |
|  |  +-----------+ |     |  +-----------+  |     |  +------------+  |                                     |
|  |  | Network   | |     |  | Public &  |  |     |  | Firewall   |  |                                     |
|  |  | Resources | |     |  | Private   |  |     |  | Rules      |  |                                     |
|  |  +-----------+ |     |  +-----------+  |     |  +------------+  |                                     |
|  |                |     |                 |     |                  |                                     |
|  +----------------+     +-----------------+     +------------------+                                     |
|                                                                                                          |
+----------------------------------------------------------------------------------------------------------+
```

## Flujo de Procesamiento

1. **Carga de Archivos**: Los archivos de audio se suben al bucket S3 en la carpeta `input/`.

2. **Activación del Procesamiento**: La carga de archivos activa una función Lambda a través de eventos S3.

3. **Envío de Trabajo**: La función Lambda envía un trabajo a la cola de AWS Batch.

4. **Procesamiento de Audio**: AWS Batch ejecuta un contenedor Docker con la imagen del sistema de análisis de audio.

5. **Análisis de Audio**:
   - Transcripción del audio con marcas de tiempo
   - Identificación de hablantes (diarización)
   - Generación de resúmenes y extracción de ideas principales
   - Análisis de sentimiento y detección de posible engaño
   - Detección de inconsistencias entre entrevistas

6. **Almacenamiento de Resultados**: Los resultados se guardan en el bucket S3 en la carpeta `output/`.

## Componentes Principales

### S3 Bucket
- Almacena los archivos de audio de entrada
- Almacena los resultados del análisis
- Activa eventos cuando se suben nuevos archivos

### Lambda Function
- Se activa cuando se suben nuevos archivos de audio
- Envía trabajos a AWS Batch para procesamiento

### AWS Batch
- Gestiona la cola de trabajos de procesamiento
- Ejecuta contenedores Docker en instancias EC2 (con GPU cuando es posible)
- Escala automáticamente según la demanda

### ECR Repository
- Almacena la imagen Docker del sistema de análisis
- Proporciona la imagen a AWS Batch para ejecución

### VPC y Recursos de Red
- Proporciona aislamiento de red para los recursos
- Permite el acceso a Internet para descargar modelos y recursos

## Ventajas de esta Arquitectura

1. **Escalabilidad**: Procesa múltiples archivos en paralelo según la demanda.
2. **Costo-eficiencia**: Solo paga por los recursos utilizados durante el procesamiento.
3. **Serverless**: No requiere administrar servidores para la mayoría de los componentes.
4. **GPU Aceleración**: Utiliza instancias con GPU para acelerar el procesamiento de ML.
5. **Seguridad**: Los recursos están aislados en una VPC con acceso controlado.
6. **Automatización**: El procesamiento se inicia automáticamente cuando se suben nuevos archivos.

## Consideraciones de Seguridad

- Los archivos se almacenan cifrados en S3
- El acceso a los recursos está controlado mediante IAM
- Las comunicaciones entre servicios están protegidas dentro de la VPC
- Los secretos (como el token de HuggingFace) se pasan como variables de entorno seguras