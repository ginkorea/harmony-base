import os
import argparse
import logging
from tqdm import tqdm
from huggingface_hub import hf_hub_download, list_repo_files

# === Logging Setup ===
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/download_gpt_oss.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def download_model(model_repo: str, local_dir: str):
    print(f"📥 Downloading {model_repo} to {local_dir}")
    try:
        files = list_repo_files(model_repo)
        os.makedirs(local_dir, exist_ok=True)

        for file in tqdm(files, desc="📦 Downloading files", unit="file"):
            hf_hub_download(
                repo_id=model_repo,
                filename=file,
                local_dir=local_dir,
                force_download=False
            )

        print("✅ Download complete.")
        logging.info(f"Model {model_repo} successfully downloaded to {local_dir}")
    except Exception as e:
        print("❌ Download failed:", str(e))
        logging.error("Download failed", exc_info=True)

def main():
    parser = argparse.ArgumentParser(description="Download GPT-OSS model from Hugging Face.")
    parser.add_argument(
        "--model",
        type=str,
        default="gpt-oss-20b",
        choices=["gpt-oss-20b", "gpt-oss-120b"],
        help="Which model to download: gpt-oss-20b or gpt-oss-120b"
    )
    args = parser.parse_args()

    model_repo = f"openai/{args.model}"
    local_dir = f"./models/{args.model}"

    download_model(model_repo, local_dir)

if __name__ == "__main__":
    main()
