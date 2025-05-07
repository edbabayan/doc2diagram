import ollama
from loguru import logger

def download_local_llm(model_name):
    """
    Check if an Ollama model is installed locally and download it if not.

    Args:
        model_name (str): Name of the Ollama model to check/download

    Returns:
        bool: True if model is available (already installed or successfully downloaded)
              False if model could not be downloaded
    """
    print(f"Checking if model '{model_name}' is installed locally...")

    try:
        # Get list of installed models
        models_list = ollama.list()

        # Check if our target model is in the list

        installed_models = [model.model for model in models_list.get("models", [])]

        if model_name in installed_models:
            logger.info(f"Model '{model_name}' is already installed locally")
            return True

        logger.warning(f"Model '{model_name}' is not installed, downloading...")

        # Download the model
        ollama.pull(model_name)
        logger.success(f"✓ Successfully downloaded model '{model_name}'")
        return True

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return False


# Example usage
if __name__ == "__main__":
    from src.config import CFG

    # Define the model you want to check/download
    download_local_llm(CFG.local_llm_model)