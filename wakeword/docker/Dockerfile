# Entorno de entrenamiento de openWakeWord.
#
# Por qué Docker: el pipeline exige Python 3.10, PyTorch 1.13.1 y TensorFlow 2.8.1 —
# versiones de 2022 que ya no conviven con Python moderno. Meterlo en el .venv del
# proyecto lo rompería. Se construye UNA vez y no se toca más.
#
# Base con CUDA 11.8 + cuDNN 8: es lo que esperan esas versiones de PyTorch/TF.
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv python3.10-dev python3-pip \
        git wget curl ffmpeg libsndfile1 build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

WORKDIR /work

# --- PyTorch 1.13.1 con CUDA 11.8 (versión clavada por el pipeline) ---
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        torch==1.13.1+cu117 torchvision==0.14.1+cu117 torchaudio==0.13.1 \
        --extra-index-url https://download.pytorch.org/whl/cu117

# --- TensorFlow 2.8.1 (para exportar el modelo) ---
RUN pip install --no-cache-dir \
        tensorflow-cpu==2.8.1 \
        protobuf==3.20.3 \
        numpy==1.23.5

# --- openWakeWord + dependencias de entrenamiento ---
RUN pip install --no-cache-dir \
        openwakeword \
        onnx onnxruntime tf2onnx==1.13.0 \
        datasets==2.14.6 huggingface_hub \
        speechbrain==0.5.16 \
        acoustics audiomentations \
        scipy scikit-learn pyyaml tqdm \
        webrtcvad mutagen torchinfo

# --- generador de muestras sintéticas con Piper ---
RUN git clone --depth 1 https://github.com/rhasspy/piper-sample-generator.git /work/piper-sample-generator \
    && pip install --no-cache-dir -r /work/piper-sample-generator/requirements.txt || true

# --- código de entrenamiento de openWakeWord ---
RUN git clone --depth 1 https://github.com/dscripka/openWakeWord.git /work/openWakeWord

CMD ["/bin/bash"]
