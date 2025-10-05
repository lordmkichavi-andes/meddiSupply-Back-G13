name: CI/CD Microservices

on:
  push:
    branches: [ main, develop, 'feature/*' ]
  pull_request:
    branches: [ main, develop ]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  AWS_REGION: us-east-1
  ECS_CLUSTER: microservices-cluster
  MIN_COVERAGE: 5

jobs:
  # 1) Detecta microservicios modificados y expone salida JSON (una sola línea)
  detect-changes:
    runs-on: ubuntu-latest
    outputs:
      changed-services: ${{ steps.changes.outputs.changed-services }}
      pr-number: ${{ steps.pr-info.outputs.number }}
      pr-title: ${{ steps.pr-info.outputs.title }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with: { fetch-depth: 0 }

      - name: Ensure jq
        run: |
          if ! command -v jq >/dev/null 2>&1; then
            sudo apt-get update
            sudo apt-get install -y jq
          fi

      - name: PR Information
        id: pr-info
        if: github.event_name == 'pull_request'
        run: |
          echo "number=${{ github.event.number }}" >> $GITHUB_OUTPUT
          echo "title=${{ github.event.pull_request.title }}" >> $GITHUB_OUTPUT
          echo "🔍 PR #${{ github.event.number }}: ${{ github.event.pull_request.title }}"

      - name: Detect Changed Services
        id: changes
        shell: bash
        run: |
          echo "🔍 Detectando microservicios modificados..."
          if [[ "${{ github.event_name }}" == "pull_request" ]]; then
            BASE="${{ github.base_ref }}"
            echo "📋 Comparando con base branch: $BASE"
            git fetch origin "$BASE:$BASE" --depth=1
          else
            BASE="HEAD~1"
            echo "📋 Comparando contra commit anterior"
          fi

          CHANGED_FILES=$(git diff --name-only "$BASE"...HEAD || true)

          SERVICES_JSON='[]'
          for dir in services/*/; do
            [[ -d "$dir" ]] || continue
            s=$(basename "$dir")
            if echo "$CHANGED_FILES" | grep -q "^services/$s/"; then
              echo "✅ $s: CAMBIOS DETECTADOS"
              SERVICES_JSON=$(jq -c --arg svc "$s" '. + [$svc]' <<<"$SERVICES_JSON")
            else
              echo "⏭️  $s: Sin cambios"
            fi
          done

          echo "📊 Servicios a procesar (JSON): $SERVICES_JSON"
          echo "changed-services=$SERVICES_JSON" >> "$GITHUB_OUTPUT"

  # 2) Test + Build + (Skip if exists) Push ECR para cada servicio cambiado (matriz)
  test_build_push:
    needs: detect-changes
    if: needs.detect-changes.outputs.changed-services != '[]'
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        service: ${{ fromJSON(needs.detect-changes.outputs.changed-services) }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"
          cache: pip

      - name: Install deps
        working-directory: ./services/${{ matrix.service }}
        run: |
          pip install --upgrade pip
          pip install pytest pytest-cov flake8
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Lint
        working-directory: ./services/${{ matrix.service }}
        run: |
          echo "🔍 flake8..."
          flake8 app.py --count --select=E9,F63,F7,F82 --show-source --statistics || true
          flake8 app.py --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics || true

      - name: Unit tests
        working-directory: ./services/${{ matrix.service }}
        run: |
          echo "🧪 pytest..."
          pytest --cov=app --cov-report=xml --cov-report=html --cov-fail-under=${{ env.MIN_COVERAGE }} -v

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Ensure ECR repository (immutable + lifecycle)
        env:
          REPO: ${{ matrix.service }}
          AWS_REGION: ${{ env.AWS_REGION }}
        run: |
          set -euo pipefail
          echo "🔐 Asegurando ECR repo '$REPO' (IMMUTABLE + lifecycle)"

          if aws ecr describe-repositories --repository-names "$REPO" --region "$AWS_REGION" >/dev/null 2>&1; then
            echo "📦 Repo existe"
            aws ecr put-image-tag-mutability --repository-name "$REPO" --image-tag-mutability IMMUTABLE --region "$AWS_REGION" || true
          else
            echo "📦 Creando repo '$REPO' (IMMUTABLE, scanOnPush, AES256)"
            aws ecr create-repository \
              --repository-name "$REPO" \
              --image-tag-mutability IMMUTABLE \
              --image-scanning-configuration scanOnPush=true \
              --encryption-configuration encryptionType=AES256 \
              --region "$AWS_REGION" >/dev/null
          fi

          cat > lifecycle.json <<JSON
          {
            "rules": [
              {
                "rulePriority": 1,
                "description": "Keep last 30 commit images",
                "selection": {
                  "tagStatus": "tagged",
                  "countType": "imageCountMoreThan",
                  "countNumber": 30,
                  "tagPatternList": ["*-$REPO"]
                },
                "action": { "type": "expire" }
              },
              {
                "rulePriority": 2,
                "description": "Keep last 10 versioned images v*",
                "selection": {
                  "tagStatus": "tagged",
                  "countType": "imageCountMoreThan",
                  "countNumber": 10,
                  "tagPrefixList": ["v"]
                },
                "action": { "type": "expire" }
              }
            ]
          }
          JSON
          aws ecr put-lifecycle-policy \
            --repository-name "$REPO" \
            --lifecycle-policy-text file://lifecycle.json \
            --region "$AWS_REGION" >/dev/null
          echo "✅ Repo y lifecycle ok"

      - name: Build & Push image (immutable tag, skip if exists)
        id: build-image
        working-directory: ./services/${{ matrix.service }}
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          REPO: ${{ matrix.service }}
          IMAGE_TAG: ${{ github.sha }}-${{ matrix.service }}
          AWS_REGION: ${{ env.AWS_REGION }}
        run: |
          set -euo pipefail
          IMAGE="$ECR_REGISTRY/$REPO:$IMAGE_TAG"

          echo "🔎 Verificando si ya existe la imagen en ECR: $IMAGE"
          # Si el tag ya existe (inmutable), reutilizamos y NO pusheamos
          if aws ecr describe-images \
              --repository-name "$REPO" \
              --image-ids imageTag="$IMAGE_TAG" \
              --region "$AWS_REGION" >/dev/null 2>&1; then
            echo "♻️  Tag ya existe (inmutable). Reutilizando imagen: $IMAGE"
            echo "image=$IMAGE" >> $GITHUB_OUTPUT
            exit 0
          fi

          echo "🐳 Build $IMAGE"
          docker build -t "$IMAGE" .
          docker push "$IMAGE"
          echo "image=$IMAGE" >> $GITHUB_OUTPUT

      - name: Upload test artifacts
        uses: actions/upload-artifact@v4
        with:
          name: ${{ matrix.service }}-coverage
          path: services/${{ matrix.service }}/coverage.xml

  # 3) Deploy a Desarrollo (matrix)
  deploy_develop:
    needs: [detect-changes, test_build_push]
    if: github.ref == 'refs/heads/develop' && needs.detect-changes.outputs.changed-services != '[]'
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        service: ${{ fromJSON(needs.detect-changes.outputs.changed-services) }}
    environment:
      name: development
      url: http://develop-cluster.example.com
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Install jq
        run: sudo apt-get update && sudo apt-get install -y jq

      - name: Deploy to ECS (Fargate) - Desarrollo
        env:
          CLUSTER: ${{ env.ECS_CLUSTER }}-dev
          SERVICE: ${{ matrix.service }}
          AWS_REGION: ${{ env.AWS_REGION }}
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          COMMIT_SHA: ${{ github.sha }}
        run: |
          set -euo pipefail
          IMAGE="$ECR_REGISTRY/$SERVICE:$COMMIT_SHA-$SERVICE"
          echo "🚀 Deploy $SERVICE → $CLUSTER con imagen $IMAGE"

          TD_ARN=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query 'services[0].taskDefinition' --output text --region "$AWS_REGION")
          aws ecs describe-task-definition --task-definition "$TD_ARN" --query 'taskDefinition' --region "$AWS_REGION" > base.json

          jq 'del(.status,.taskDefinitionArn,.requiresAttributes,.revision,.compatibilities,.registeredAt,.registeredBy)' base.json > stripped.json

          if jq -e --arg S "$SERVICE" 'any(.containerDefinitions[].name; . == $S)' stripped.json >/dev/null; then
            jq --arg S "$SERVICE" --arg IMG "$IMAGE" '
              .containerDefinitions |= map(if .name == $S then .image = $IMG else . end)
            ' stripped.json > rendered.json
          else
            jq --arg S "$SERVICE" --arg IMG "$IMAGE" '
              .containerDefinitions |=
              (.[0].image = $IMG) as $x | map(if (.image|test("/"+$S+"(:|@|$)")) then (.image = $IMG) else . end)
            ' stripped.json > rendered.json
          fi

          NEW_TD_ARN=$(aws ecs register-task-definition --cli-input-json file://rendered.json --query 'taskDefinition.taskDefinitionArn' --output text --region "$AWS_REGION")
          aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$NEW_TD_ARN" --region "$AWS_REGION" >/dev/null
          echo "⏳ Esperando estabilidad..."
          aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$AWS_REGION"
          echo "✅ $SERVICE desplegado en desarrollo con $NEW_TD_ARN"

  # 4) Deploy a Producción (matrix)
  deploy_prod:
    needs: [detect-changes, test_build_push]
    if: github.ref == 'refs/heads/main' && needs.detect-changes.outputs.changed-services != '[]'
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        service: ${{ fromJSON(needs.detect-changes.outputs.changed-services) }}
    environment:
      name: production
      url: http://prod-cluster.example.com
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Install jq
        run: sudo apt-get update && sudo apt-get install -y jq

      - name: Deploy to ECS (Fargate) - Producción
        env:
          CLUSTER: ${{ env.ECS_CLUSTER }}-prod
          SERVICE: ${{ matrix.service }}
          AWS_REGION: ${{ env.AWS_REGION }}
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          COMMIT_SHA: ${{ github.sha }}
        run: |
          set -euo pipefail
          IMAGE="$ECR_REGISTRY/$SERVICE:$COMMIT_SHA-$SERVICE"
          echo "🚀 Deploy $SERVICE → $CLUSTER con imagen $IMAGE"

          TD_ARN=$(aws ecs describe-services --cluster "$CLUSTER" --services "$SERVICE" --query 'services[0].taskDefinition' --output text --region "$AWS_REGION")
          aws ecs describe-task-definition --task-definition "$TD_ARN" --query 'taskDefinition' --region "$AWS_REGION" > base.json

          jq 'del(.status,.taskDefinitionArn,.requiresAttributes,.revision,.compatibilities,.registeredAt,.registeredBy)' base.json > stripped.json

          if jq -e --arg S "$SERVICE" 'any(.containerDefinitions[].name; . == $S)' stripped.json >/dev/null; then
            jq --arg S "$SERVICE" --arg IMG "$IMAGE" '
              .containerDefinitions |= map(if .name == $S then .image = $IMG else . end)
            ' stripped.json > rendered.json
          else
            jq --arg S "$SERVICE" --arg IMG "$IMAGE" '
              .containerDefinitions |=
              (.[0].image = $IMG) as $x | map(if (.image|test("/"+$S+"(:|@|$)")) then (.image = $IMG) else . end)
            ' stripped.json > rendered.json
          fi

          NEW_TD_ARN=$(aws ecs register-task-definition --cli-input-json file://rendered.json --query 'taskDefinition.taskDefinitionArn' --output text --region "$AWS_REGION")
          aws ecs update-service --cluster "$CLUSTER" --service "$SERVICE" --task-definition "$NEW_TD_ARN" --region "$AWS_REGION" >/dev/null
          echo "⏳ Esperando estabilidad..."
          aws ecs wait services-stable --cluster "$CLUSTER" --services "$SERVICE" --region "$AWS_REGION"
          echo "✅ $SERVICE desplegado en producción con $NEW_TD_ARN"

  # 5) Notificación de PR (si aplica)
  pr_notification:
    needs: [detect-changes, test_build_push]
    runs-on: ubuntu-latest
    if: github.event_name == 'pull_request' && needs.detect-changes.outputs.changed-services != '[]'
    steps:
      - name: PR Summary
        run: |
          echo "📋 RESUMEN DEL PULL REQUEST"
          echo "================================="
          echo "🔍 PR #${{ needs.detect-changes.outputs.pr-number }}: ${{ needs.detect-changes.outputs.pr-title }}"
          echo "🌿 Branch: ${{ github.head_ref }} → ${{ github.base_ref }}"
          echo "📊 Microservicios afectados:"
          for s in $(jq -r '.[]' <<< '${{ needs.detect-changes.outputs.changed-services }}'); do
            echo "   ✅ $s - Tests OK, imagen construida"
          done
          echo "================================="

  # 6) Cleanup local del runner
  cleanup:
    needs: [deploy_develop, deploy_prod]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: Cleanup docker
        run: |
          echo "🧹 Limpiando capas locales de Docker..."
          docker system prune -af || true
          echo "✅ Cleanup completado"
Cambio pequeño para probar workflow
