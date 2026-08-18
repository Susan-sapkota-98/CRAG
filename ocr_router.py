import pytesseract
from PIL import Image
import torch
import pytesseract

#for windows
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

#for linux
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
# ---- Nepali printed (Tesseract) ----
def ocr_nepali_printed(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="nep")

# ---- English printed (Tesseract) ----
def ocr_english_printed(image: Image.Image) -> str:
    return pytesseract.image_to_string(image, lang="eng")

# ---- English handwritten — transformers + peft (no unsloth, avoids ROCm crash) ----
_model_cache = {"model": None, "processor": None}
INSTRUCTION = "Extract all text from this handwritten page exactly as written, preserving line breaks."

def _load_handwriting_model():
    if _model_cache["model"] is None:
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor
        from peft import PeftModel

        base_model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2.5-VL-7B-Instruct",
            torch_dtype=torch.float32,   # CPU ma float16 le pani issue dina sakcha, float32 safer
            low_cpu_mem_usage=True,
        )
        model = PeftModel.from_pretrained(base_model, "models/english_ocr_fullpage_lora")
        processor = AutoProcessor.from_pretrained("Qwen/Qwen2.5-VL-7B-Instruct")

        _model_cache["model"] = model
        _model_cache["processor"] = processor
    return _model_cache["model"], _model_cache["processor"]

def ocr_english_handwritten(image: Image.Image) -> str:
    model, processor = _load_handwriting_model()
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image},
        {"type": "text", "text": INSTRUCTION}
    ]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = processor(text=[text], images=[image], return_tensors="pt").to(model.device)
    output = model.generate(**inputs, max_new_tokens=768)
    decoded = processor.batch_decode(output, skip_special_tokens=True)[0]
    return decoded.split(INSTRUCTION)[-1].strip()

# ---- Dispatch ----
ENGINES = {
    "nepali_printed": ocr_nepali_printed,
    "english_printed": ocr_english_printed,
    "english_handwritten": ocr_english_handwritten,
}

def run_ocr(image: Image.Image, engine: str) -> str:
    if engine not in ENGINES:
        raise ValueError(f"Unknown OCR engine: {engine}. Choose from {list(ENGINES.keys())}")
    return ENGINES[engine](image)