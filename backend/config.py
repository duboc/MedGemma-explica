from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    project_id: str = "riojucu"
    location: str = "us-central1"
    gcs_bucket: str = "riojucu-medgemma-explica"
    firestore_collection: str = "analyses"
    # MedGemma endpoint (in external project)
    medgemma_endpoint_url: str = "https://mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de.us-central1-640132109143.prediction.vertexai.goog"
    medgemma_endpoint_project: str = "640132109143"
    medgemma_endpoint_id: str = "mg-endpoint-b2729fdc-fd5a-423a-97aa-1416142313de"

    # Gemini Flash (for educational companion)
    gemini_model: str = "gemini-3-flash-preview"
    gemini_location: str = "global"

    # Cloud Healthcare API - DICOM store for CT scans
    dicom_project: str = "riojucu"
    dicom_location: str = "us-central1"
    dicom_dataset: str = "medgemma-dicom"
    dicom_store: str = "ct-scans"

    # CORS
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_prefix = "MEDGEMMA_"
        env_file = ".env"


settings = Settings()
