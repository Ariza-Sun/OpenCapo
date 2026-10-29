"""Compute device selection shared by the model adapters."""

AUTO = "auto"


def resolve_device(device: str = AUTO) -> str:
    """Map "auto" to "cuda" when a GPU is visible, else "cpu"; pass anything else through."""
    if device != AUTO:
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"
