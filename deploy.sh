#!/bin/bash

# --- Configuration Section ---
# Your Google Cloud Project ID (string format)
PROJECT_ID="refined-algebra-433218-f7"
REGION="us-central1"                   # Recommended Cloud Run region (check Gemini Pro Vision availability)
SERVICE_NAME="loan-extractor-combined" # Name for your Cloud Run service

# --- End Configuration Section ---

echo "Starting automated deployment script..."
echo "Target Project ID: ${PROJECT_ID}"
echo "Deployment Region: ${REGION}"
echo "Cloud Run Service Name: ${SERVICE_NAME}"
echo ""

# --- Step 1: Configure gcloud CLI ---
echo "--- 1. Configuring gcloud CLI to use project: ${PROJECT_ID} ---"
gcloud config set project "${PROJECT_ID}"
echo ""

# --- Step 2: Authenticate gcloud (if not already) ---
echo "--- 2. Authenticating gcloud CLI ---"
# This command will open a browser for you to log in if you're not already authenticated.
# Use --no-launch-browser if running in a headless environment and you want to copy the URL manually.
gcloud auth login
echo "Ensure you are logged in with an account that has owner/editor privileges for project ${PROJECT_ID}."
echo ""

# --- Step 3: Enable necessary Google Cloud APIs ---
echo "--- 3. Enabling necessary Google Cloud APIs ---"
gcloud services enable run.googleapis.com || { echo "Failed to enable Cloud Run API. Aborting."; exit 1; }
gcloud services enable aiplatform.googleapis.com || { echo "Failed to enable Vertex AI API. Aborting."; exit 1; }
gcloud services enable artifactregistry.googleapis.com || { echo "Failed to enable Artifact Registry API. Aborting."; exit 1; }
echo "APIs enabled successfully."
echo ""

# --- Step 4: Grant Service Account Permissions for Gemini access ---
echo "--- 4. Granting 'Vertex AI User' role to Cloud Run service account ---"
# Get the Project Number, which is part of the default Compute Engine service account name
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
SERVICE_ACCOUNT_EMAIL="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "Granting 'Vertex AI User' role to service account: ${SERVICE_ACCOUNT_EMAIL}"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/aiplatform.user" || { echo "Failed to grant IAM role. Aborting."; exit 1; }
echo "IAM role granted successfully."
echo ""

# --- Step 5: Build Docker image and push to Artifact Registry ---
echo "--- 5. Building Docker image and pushing to Artifact Registry ---"
# Ensure Docker is running locally if you encounter issues here.
# Configure Docker to use gcloud as a credential helper for Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev"

# Build and tag the image
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${SERVICE_NAME}-repo/${SERVICE_NAME}:latest"
echo "Building image: ${IMAGE_URI}"

# Create Artifact Registry repository if it doesn't exist
gcloud artifacts repositories describe "${SERVICE_NAME}-repo" \
  --location="${REGION}" --project="${PROJECT_ID}" &>/dev/null || \
  gcloud artifacts repositories create "${SERVICE_NAME}-repo" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="Docker repository for ${SERVICE_NAME} service" \
    --project="${PROJECT_ID}" || { echo "Failed to create Artifact Registry repository. Aborting."; exit 1; }

docker build -t "${IMAGE_URI}" . || { echo "Docker build failed. Aborting."; exit 1; }
docker push "${IMAGE_URI}" || { echo "Docker push failed. Aborting."; exit 1; }
echo "Docker image built and pushed successfully to Artifact Registry."
echo ""


# --- Step 6: Deploy the service to Cloud Run ---
echo "--- 6. Deploying the service to Cloud Run ---"
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_URI}" \
  --platform managed \
  --region "${REGION}" \
  --allow-unauthenticated \
  --min-instances 0 \
  --max-instances 1 \
  --port 8080 \
  --cpu 1 \
  --memory 512Mi \
  --timeout 300 \
  --set-env-vars PYTHONUNBUFFERED=1 || { echo "Cloud Run deployment failed. Aborting."; exit 1; }
echo "Cloud Run deployment initiated. Waiting for service URL..."
echo ""

# --- Step 7: Get the deployed service URL ---
echo "--- 7. Getting deployed service URL ---"
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --format="value(status.url)")

if [ -z "$SERVICE_URL" ]; then
  echo "Error: Could not retrieve service URL after deployment. Check Cloud Run console for details."
  exit 1
fi

echo "--------------------------------------------------------"
echo "Deployment Complete!"
echo "Your combined web app + API is deployed at:"
echo "Frontend:  ${SERVICE_URL}"
echo "API Endpoint: ${SERVICE_URL}/api/extract-loan-details/"
echo "--------------------------------------------------------"
echo "To test:"
echo "1. Copy the Frontend URL and open it in your web browser."
echo "   URL: ${SERVICE_URL}"
echo "2. Upload your loan contract image interactively."
echo "--------------------------------------------------------"
echo "Check Cloud Run logs for '${SERVICE_NAME}' service if you encounter issues."
