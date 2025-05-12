# Guía de Despliegue del Sistema de Análisis de Entrevistas de Audio

Esta guía proporciona instrucciones detalladas para desplegar el Sistema de Análisis de Entrevistas de Audio en AWS utilizando la plantilla CloudFormation incluida.

## Requisitos Previos

Antes de comenzar, asegúrese de tener:

1. Una cuenta de AWS con permisos para crear recursos como:
   - VPC y subredes
   - S3 Buckets
   - ECR Repositories
   - AWS Batch
   - Lambda Functions
   - IAM Roles

2. AWS CLI instalado y configurado con credenciales válidas.

3. Un token de API de HuggingFace para acceder a los modelos de diarización de hablantes.

4. Docker instalado en su máquina local (para construir y subir la imagen).

## Paso 1: Desplegar la Plantilla CloudFormation

La plantilla CloudFormation (`cloudformation-template.yaml`) crea toda la infraestructura necesaria para ejecutar el sistema en AWS.

### Opción 1: Despliegue mediante AWS CLI

```bash
aws cloudformation create-stack \
  --stack-name audio-analysis-system \
  --template-body file://cloudformation-template.yaml \
  --parameters \
    ParameterKey=EnvironmentName,ParameterValue=prod \
    ParameterKey=S3BucketName,ParameterValue=mi-bucket-de-audio-analisis \
    ParameterKey=ECRRepositoryName,ParameterValue=audio-interview-analysis \
    ParameterKey=HuggingFaceToken,ParameterValue=hf_xxxxxxxxxxxxxxxxxxxxxxxx \
  --capabilities CAPABILITY_IAM
```

### Opción 2: Despliegue mediante la Consola AWS

1. Inicie sesión en la [Consola de AWS](https://console.aws.amazon.com/).
2. Navegue a CloudFormation.
3. Haga clic en "Create stack" > "With new resources (standard)".
4. Seleccione "Upload a template file" y cargue el archivo `cloudformation-template.yaml`.
5. Haga clic en "Next".
6. Proporcione un nombre para la pila (por ejemplo, "audio-analysis-system").
7. Complete los parámetros requeridos:
   - **EnvironmentName**: El entorno (dev, test, prod)
   - **S3BucketName**: Nombre del bucket S3 para almacenar archivos de audio y resultados
   - **ECRRepositoryName**: Nombre del repositorio ECR para la imagen Docker
   - **HuggingFaceToken**: Su token de API de HuggingFace
8. Haga clic en "Next", revise las opciones y haga clic en "Create stack".

## Paso 2: Monitorear el Progreso del Despliegue

El despliegue puede tardar entre 10-15 minutos en completarse. Puede monitorear el progreso en la consola de CloudFormation o mediante AWS CLI:

```bash
aws cloudformation describe-stacks --stack-name audio-analysis-system
```

## Paso 3: Obtener Información de Salida

Una vez que el despliegue se haya completado, obtenga la información de salida que necesitará para los siguientes pasos:

```bash
aws cloudformation describe-stacks --stack-name audio-analysis-system --query "Stacks[0].Outputs"
```

Tome nota de los siguientes valores:
- **ECRRepositoryUrl**: La URL del repositorio ECR donde subirá la imagen Docker
- **S3BucketName**: El nombre del bucket S3 donde subirá los archivos de audio

## Paso 4: Construir y Subir la Imagen Docker

1. Construya la imagen Docker:

```bash
# Obtenga la URL del repositorio ECR
ECR_REPO=$(aws cloudformation describe-stacks --stack-name audio-analysis-system --query "Stacks[0].Outputs[?OutputKey=='ECRRepositoryUrl'].OutputValue" --output text)

# Inicie sesión en ECR
aws ecr get-login-password --region $(aws configure get region) | docker login --username AWS --password-stdin $ECR_REPO

# Construya la imagen Docker
docker build -t $ECR_REPO:latest .

# Suba la imagen a ECR
docker push $ECR_REPO:latest
```

## Paso 5: Probar el Sistema

1. Suba un archivo de audio al bucket S3 en la carpeta `input/`:

```bash
# Obtenga el nombre del bucket S3
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name audio-analysis-system --query "Stacks[0].Outputs[?OutputKey=='S3BucketName'].OutputValue" --output text)

# Suba un archivo de audio
aws s3 cp ruta/a/mi-entrevista.mp3 s3://$S3_BUCKET/input/
```

2. El sistema procesará automáticamente el archivo y guardará los resultados en la carpeta `output/` del mismo bucket.

3. Monitoree el progreso del trabajo:

```bash
# Obtenga el nombre de la cola de trabajos
JOB_QUEUE=$(aws cloudformation describe-stacks --stack-name audio-analysis-system --query "Stacks[0].Outputs[?OutputKey=='BatchJobQueueArn'].OutputValue" --output text | awk -F/ '{print $2}')

# Liste los trabajos
aws batch list-jobs --job-queue $JOB_QUEUE
```

4. Una vez que el trabajo se haya completado, puede descargar los resultados:

```bash
aws s3 cp s3://$S3_BUCKET/output/ ./resultados/ --recursive
```

## Paso 6: Verificar los Resultados

Los resultados incluirán:

1. **Transcripciones** en formato de guión con marcas de tiempo y hablantes identificados.
2. **Resúmenes** con las ideas principales de cada entrevista.
3. **Análisis de sentimiento** para detectar posibles indicadores de engaño.
4. **Análisis de inconsistencias** entre diferentes entrevistas (si se procesaron múltiples archivos).

## Solución de Problemas

### Problemas con el Despliegue de CloudFormation

Si el despliegue falla, revise los eventos de la pila para identificar el problema:

```bash
aws cloudformation describe-stack-events --stack-name audio-analysis-system
```

### Problemas con los Trabajos de AWS Batch

Si un trabajo falla, puede ver los registros en CloudWatch Logs:

```bash
# Obtenga el ID del trabajo
JOB_ID=$(aws batch list-jobs --job-queue $JOB_QUEUE --query "jobSummaryList[0].jobId" --output text)

# Obtenga el nombre del grupo de logs
LOG_GROUP=$(aws batch describe-jobs --jobs $JOB_ID --query "jobs[0].container.logStreamName" --output text)

# Vea los logs
aws logs get-log-events --log-group-name /aws/batch/job --log-stream-name $LOG_GROUP
```

## Limpieza de Recursos

Cuando ya no necesite el sistema, puede eliminar todos los recursos creados:

```bash
# Primero, vacíe el bucket S3
aws s3 rm s3://$S3_BUCKET --recursive

# Luego, elimine la pila de CloudFormation
aws cloudformation delete-stack --stack-name audio-analysis-system
```

## Recursos Adicionales

- [Documentación de AWS CloudFormation](https://docs.aws.amazon.com/cloudformation/)
- [Documentación de AWS Batch](https://docs.aws.amazon.com/batch/)
- [Documentación de Amazon ECR](https://docs.aws.amazon.com/ecr/)
- [Documentación de Amazon S3](https://docs.aws.amazon.com/s3/)